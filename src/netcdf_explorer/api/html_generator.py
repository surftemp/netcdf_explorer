# MIT License
#
# Copyright (c) 2023-2024 National Centre for Earth Observation
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import xarray as xr
import shutil
import json
import numpy as np
from mako.template import Template
import pyproj
import logging
import copy

from .layers import LayerFactory, LayerSingleBand, LayerWMS

from netcdf_explorer.htmlfive.html5_builder import Html5Builder, ElementFragment

from netcdf_explorer.fragments.utils import anti_aliasing_style
from netcdf_explorer.fragments.image import ImageFragment
from netcdf_explorer.fragments.table import TableFragment
from netcdf_explorer.fragments.legend import LegendFragment

js_paths = [os.path.join(os.path.split(__file__)[0], "cmap.js"),
            os.path.join(os.path.split(__file__)[0], "data_image.js"),
            os.path.join(os.path.split(__file__)[0], "html_view.js")]
css_path = os.path.join(os.path.split(__file__)[0], "index.css")


class HTMLGenerator:

    def __init__(self, config, input_ds, output_folder, title, sample_count=None, sample_cases=None,
                 netcdf_download_filename="", filter_controls=False):
        dimensions = config.get("dimensions", {})
        case_dimension = dimensions.get("case", "time")
        x_dimension = dimensions.get("x", "x")
        y_dimension = dimensions.get("y", "y")
        coordinates = config.get("coordinates", {})
        x_coordinate = coordinates.get("x", "x")
        y_coordinate = coordinates.get("y", "y")
        time_coordinate = coordinates.get("time", "")
        info = config.get("info",{})
        image = config.get("image", {})
        max_zoom = image.get("max-zoom", None)
        grid_image_width = image.get("grid-width", None)
        crs = config.get("crs",None)
        labels = config.get("labels",None)
        group = config.get("group",None)

        self.case_dimension = case_dimension
        self.x_dimension = x_dimension
        self.y_dimension = y_dimension
        self.x_coordinate = x_coordinate
        self.y_coordinate = y_coordinate
        self.time_coordinate = time_coordinate
        self.input_ds = input_ds
        self.output_folder = output_folder
        self.title = title
        self.sample_count = sample_count
        self.sample_cases = sample_cases
        self.max_zoom = max_zoom
        self.grid_image_width = grid_image_width
        self.netcdf_download_filename = netcdf_download_filename
        self.output_html_path = os.path.join(output_folder, "index.html")
        self.filter_controls = filter_controls
        self.info = info
        self.crs = crs
        self.labels = labels
        self.logger = logging.getLogger("generate_html")
        self.group = group

        image_folder = os.path.join(self.output_folder, "images")
        os.makedirs(image_folder, exist_ok=True)

        data_folder = os.path.join(self.output_folder, "data")
        os.makedirs(data_folder, exist_ok=True)

        cmap_folder = os.path.join(self.output_folder, "cmaps")
        os.makedirs(cmap_folder, exist_ok=True)

        js_code = ""
        for js_path in js_paths:
            with open(js_path) as f:
                js_code += f.read()

        with open(os.path.join(self.output_folder, "index.js"), "w") as f:
            f.write(js_code)

        shutil.copyfile(css_path, os.path.join(self.output_folder, "index.css"))
        self.layer_definitions = []

        self.layer_images = []
        self.layer_data = []
        self.layer_legends = {}

        self.input_ds = self.reduce_coordinate_dimension(self.input_ds, self.x_coordinate, self.case_dimension)
        self.input_ds = self.reduce_coordinate_dimension(self.input_ds, self.y_coordinate, self.case_dimension)

        for (layer_name, layer_spec) in config["layers"].items():
            layer = LayerFactory.create(self, layer_name, layer_spec)
            self.layer_definitions.append(layer)

        self.all_cmaps = ["Purples", "gist_rainbow", "gist_ncar", "Blues", "Greys", "autumn", "gist_gray", "magma", "Set3",
                     "cool", "tab20c", "GnBu", "brg", "cividis", "Pastel1", "YlOrRd", "Spectral", "gist_earth", "PuBu",
                     "OrRd", "PuRd", "plasma", "winter", "PuBuGn", "inferno", "bwr", "RdGy", "Wistia", "gist_stern",
                     "gist_heat", "BuGn", "twilight", "RdBu", "twilight_shifted", "Paired", "PiYG", "RdYlBu", "Dark2",
                     "CMRmap", "BuPu", "gnuplot", "PRGn", "nipy_spectral", "ocean", "viridis", "bone", "BrBG",
                     "gnuplot2", "Oranges", "turbo", "YlGn", "PuOr", "hot", "Set2", "afmhot", "hsv", "YlOrBr",
                     "terrain", "Accent", "copper", "cubehelix", "RdPu", "tab10", "Reds", "Greens", "gray", "rainbow",
                     "spring", "tab20", "pink", "coolwarm", "RdYlGn", "Set1", "tab20b", "flag", "gist_yarg", "binary",
                     "YlGnBu", "seismic", "prism", "Pastel2", "jet", "summer"]

        for cmap in self.all_cmaps:
            source_path = os.path.join(os.path.abspath(os.path.split(__file__)[0]),"..","misc","cmaps", cmap+".json")
            dest_path = os.path.join(cmap_folder, cmap + ".json")
            shutil.copyfile(source_path, dest_path)

    def reduce_coordinate_dimension(self, ds, coordinate_name, case_dimension):
        dims = ds[coordinate_name].dims
        ndims = len(dims)
        if case_dimension in dims:
            ndims -= 1
        if ndims == 1:
            return ds  # already 1-dimensional
        if ndims == 2:
            if case_dimension in dims:
                raise Exception(f"Unable to make spatial coordinate {coordinate_name} 1-dimensional")

            # coordinate is 2 dimensional, see if it can be reduced to 1 dimensional
            da = ds[coordinate_name]
            arr = da.data
            if np.alltrue(arr[0, :] == arr[-1, :]):
                # assume all rows are identical if first and last rows are
                ds[coordinate_name] = xr.DataArray(arr[0, :], dims=(da.dims[1],), attrs=da.attrs)
                return ds
            if np.alltrue(arr[:, 0] == arr[:, -1]):
                # assume all columns are identical if first and last columns are
                ds[coordinate_name] = xr.DataArray(arr[:, 0], dims=(da.dims[0],), attrs=da.attrs)
                return ds
        raise Exception(f"Unable to make spatial coordinate {coordinate_name} 1-dimensional")

    def get_image_path(self, key, index=None):
        if index is not None:
            filename = f"{key}{index}.png"
        else:
            filename = f"{key}.png"
        src = os.path.join("images", filename)
        path = os.path.join(self.output_folder, src)
        return (src, path)

    def get_data_path(self, key, index):
        filename = f"{key}{index}.gz"
        src = os.path.join("data", filename)
        path = os.path.join(self.output_folder, src)
        return (src, path)

    def get_x_coords(self, ds, for_case=0):
        x_dims = ds[self.x_coordinate].dims
        if self.case_dimension in x_dims:
            return ds[self.x_coordinate].isel(**{self.case_dimension: for_case}).squeeze()
        else:
            return ds[self.x_coordinate]

    def get_y_coords(self, ds, for_case=0):
        y_dims = ds[self.y_coordinate].dims
        if self.case_dimension in y_dims:
            return ds[self.y_coordinate].isel(**{self.case_dimension: for_case}).squeeze()
        else:
            return ds[self.y_coordinate]

    def get_image_dimensions(self, ds):
        x_coords = self.get_x_coords(ds)
        y_coords = self.get_y_coords(ds)
        if len(x_coords.shape) == 1 and len(y_coords.shape) == 1:
            image_height = y_coords.shape[0]
            image_width = x_coords.shape[0]
            return (image_width, image_height)
        else:
            raise Exception("Unable to determine image dimensions from dataset")

    def generate_label_buttons(self):
        d = ElementFragment("div")
        d.add_fragment(ElementFragment("a",attrs={"href":"", "download":"labels.json","id":"download_labels_btn"}).add_text("download"))
        return d

    def get_label_control_id(self, for_group, for_label, for_index=None):
        # obtain the expected id for a label control
        if for_index is not None:
            return f"radio_{for_group}_{for_label}_{for_index}"
        else:
            return f"radio_{for_group}_{for_label}"

    def generate_label_controls(self, index=None):
        d = ElementFragment("div")
        for label_group in self.labels:
            fieldset = ElementFragment("fieldset", style={"width":str(self.grid_image_width)+"px"})
            legend = ElementFragment("legend").add_text(label_group)
            fieldset.add_fragment(legend)
            group = "label_group_" + label_group
            if index is not None:
                group += "_" + str(index)

            for label in self.labels[label_group]:
                control_id = self.get_label_control_id(label_group,label,index)
                i = ElementFragment("input",attrs={"type":"radio","name":group,"value":label,"id":control_id})
                l = ElementFragment("label",attrs={"for":control_id}).add_text(label)
                i.add_fragment(l)
                fieldset.add_fragment(i)
            d.add_fragment(fieldset)
        return d

    def generate_info_table(self, index, ds):
        d = self.generate_info_dict(index, ds)
        tf = TableFragment(attrs={"class":"info_table"},style={"width":"%dpx"%self.grid_image_width})
        for (key,value) in d.items():
            tf.add_row([key,value])
        ef = ElementFragment("button", attrs={"class": "info_table"},style={"max-height":"%dpx"%self.grid_image_width}).add_fragment(tf)
        return ef

    def generate_info_dict(self, index, ds):
        d = {}
        variables = { "data": ds, "index":index }
        if self.crs:
            transformer = pyproj.Transformer.from_crs(self.crs, "EPSG:4326", always_xy=True)
            lon, lat = transformer.transform(ds[self.x_coordinate].mean().item(), ds[self.y_coordinate].mean().item())
            variables["lon"] = lon
            variables["lat"] = lat

        for (key,value) in self.info.items():
            template = Template(value)
            try:
                d[key] = template.render(**variables)
            except Exception as ex:
                self.logger.error(f"Unable to render info for key: {str(ex)}")
        return d

    def run(self):
        cases = []
        image_width, image_height = self.get_image_dimensions(self.input_ds)
        n = len(self.input_ds[self.case_dimension])

        selected_indexes = list(range(n))

        for i in selected_indexes:
            timestamp = str(self.input_ds[self.time_coordinate].data[i])[:10] if self.time_coordinate else None
            cases.append((i, timestamp, self.input_ds.isel(**{self.case_dimension: i})))
            cases = sorted(cases, key=lambda t: t[0])

        # check the layers, removing any that fail
        remove_layers = []
        for layer_definition in self.layer_definitions:
            err = layer_definition.check(self.input_ds)
            if err:
                self.logger.error(f"Unable to add layer {layer_definition.layer_name}: {err}")
                remove_layers.append(layer_definition)

        for layer_definition in remove_layers:
            self.layer_definitions.remove(layer_definition)

        # build the legends
        for layer_definition in self.layer_definitions:
            if layer_definition.has_legend():
                legend_src, legend_path = self.get_image_path(layer_definition.layer_name + "_legend")
                layer_definition.build_legend(legend_path)
                self.layer_legends[layer_definition.layer_name] = legend_src

        # build the images and data
        label_values = None
        if self.labels:
            label_values = { "case_dimension": self.case_dimension, "values": {}, "schema": copy.deepcopy(self.labels)}
            if self.netcdf_download_filename:
                label_values["netcdf_filename"] = self.netcdf_download_filename

        for (index, timestamp, ds) in cases:
            image_srcs = {}
            data_srcs = {}

            for layer_definition in self.layer_definitions:
                (src, path) = self.get_image_path(layer_definition.layer_name, index=index)
                layer_definition.build(ds, path)
                image_srcs[layer_definition.layer_name] = src
                if layer_definition.save_data():
                    (data_src, data_path) = self.get_data_path(layer_definition.layer_name, index)
                    data_options = layer_definition.build_data(ds, data_path)
                    data_srcs[layer_definition.layer_name] = {"url":data_src, "options":data_options}

            if self.labels:
                for label_group in self.labels:
                    if label_group in ds:
                        if label_group not in label_values["values"]:
                            label_values["values"][label_group] = []
                        label_values["values"][label_group].append(ds[label_group].item())


            self.layer_images.append((index, timestamp, image_srcs, data_srcs, ds))

        builder = Html5Builder(language="en")

        builder.head().add_element("title").add_text(self.title)
        builder.head().add_element("style").add_text(anti_aliasing_style)
        builder.head().add_element("script", {"src": "index.js"})
        builder.head().add_element("link", {"rel": "stylesheet", "href": "index.css"})

        root = builder.body().add_element("div")

        container_div = root.add_element("div")
        overlay_container_div = container_div.add_element("div", {"id": "overlay_container", "style": "display:none;"})
        grid_container_div = container_div.add_element("div", {"id": "grid_container", "style": "display:none;"})

        self.build_overlay_view(overlay_container_div, builder, image_width, image_height)
        self.build_grid_view(grid_container_div, builder, image_width, image_height)

        scenes = { "layers":[], "index": [] }

        for layer_definition in self.layer_definitions:
            layer_dict = {"name": layer_definition.layer_name, "label": layer_definition.layer_label, "has_data": layer_definition.save_data()}
            if isinstance(layer_definition,LayerWMS):
                layer_dict["wms_url"] = layer_definition.wms_url
            scenes["layers"].insert(0, layer_dict)

        for (index, timestamp, layer_sources, data_sources, ds) in self.layer_images:

            info = {}
            if self.info:
                info = self.generate_info_dict(index, ds)

            scene_dict = {"timestamp": timestamp if timestamp is not None else "", "image_srcs": layer_sources,
                               "data_srcs": data_sources, "info": info, "pos":index}
            for layer_definition in self.layer_definitions:
                if isinstance(layer_definition, LayerWMS):
                    ((x_min, y_min), (x_max, y_max)) = layer_definition.get_bounds(ds)
                    scene_dict["x_min"] = x_min
                    scene_dict["x_max"] = x_max
                    scene_dict["y_min"] = y_min
                    scene_dict["y_max"] = y_max

            scenes["index"].append(scene_dict)

        with open(os.path.join(self.output_folder, "scenes.json"), "w") as f:
            f.write(json.dumps(scenes,indent=4))

        builder.head().add_element("script").add_text("let image_width=" + json.dumps(image_width) + ";")

        self.logger.info(f"writing {self.output_html_path}")
        with open(self.output_html_path, "w") as f:
            f.write(builder.get_html())

        if self.netcdf_download_filename:
            self.input_ds.to_netcdf(os.path.join(self.output_folder, self.netcdf_download_filename))

        if label_values:
            with open(os.path.join(self.output_folder, "labels.json"),"w") as f:
                f.write(json.dumps(label_values, indent=4))

        os.makedirs(os.path.join(self.output_folder, "service_info"), exist_ok=True)
        with open(os.path.join(self.output_folder, "service_info", "services.json"), "w") as f:
            f.write(json.dumps({}, indent=4))

    def build_grid_view(self, grid_container_div, builder, image_width, image_height):
        grid_container_div.add_element("input",
                                       {"type": "button", "id": "overlay_view_btn", "value": "Show Overlay View"})

        grid_container_div.add_element("span").add_text(self.title)

        if self.netcdf_download_filename:
            grid_container_div.add_element("span", {"class": "spacer"}).add_text("|")
            grid_container_div.add_element("a", {"href": self.netcdf_download_filename,
                                                 "download": self.netcdf_download_filename}).add_text(
                "download netcdf4")

        tf = TableFragment()

        column_ids = ["index_col"]
        if self.info:
            column_ids += ["info"]
        if self.labels:
            column_ids += ["labels"]

        for layer_definition in self.layer_definitions[::-1]:
            columm_id = layer_definition.layer_name + "_col"
            column_ids.append(columm_id)
        tf.set_column_ids(column_ids)

        header_cells = ["Index"]
        if self.info:
            header_cells.append("Info")
        if self.labels:
            header_cells.append("Labels")
        for layer_definition in self.layer_definitions[::-1]:
            if layer_definition.layer_name in self.layer_legends:
                img = ImageFragment(self.layer_legends[layer_definition.layer_name],
                                    layer_definition.layer_name + "_grid_legend", alt_text="legend",
                                    w=self.grid_image_width if self.grid_image_width else image_width)
                vmin = getattr(layer_definition, "vmin", None)
                vmax = getattr(layer_definition, "vmax", None)
                header_cells.append(LegendFragment(layer_definition.layer_label, img, vmin, vmax))
            else:
                header_cells.append(layer_definition.layer_label)
        tf.add_header_row(header_cells)

        button_cells = [""]
        if self.info:
            button_cells.append("")
        if self.labels:
            button_cells.append(self.generate_label_buttons())

        for layer_definition in self.layer_definitions[::-1]:
            button_cells.append(
                ElementFragment("button", {"id": layer_definition.layer_name + "_hide"}).add_text("Hide"))
        tf.add_row(button_cells)

        current_group_label = ""
        for (index, timestamp, layer_sources, _, ds) in self.layer_images:
            if self.group:
                template = Template(self.group)
                group_label = template.render(**{"data":ds})
                if group_label != current_group_label:
                    tf.add_row(group_label)
                current_group_label = group_label
            cells = [self.generate_index_cell(index)]
            if self.info:
                cells += [self.generate_info_table(index,ds)]
            if self.labels:
                cells += [self.generate_label_controls(index)]
            for layer_definition in self.layer_definitions[::-1]:
                src = layer_sources[layer_definition.layer_name]
                img = ImageFragment(src, layer_definition.layer_name + "_grid_" + str(index), alt_text=timestamp,
                                    w=self.grid_image_width if self.grid_image_width else image_width)
                cells.append(img)
            tf.add_row(cells)

        grid_container_div.add_fragment(tf)

    def generate_index_cell(self, index):
        return ElementFragment("button",attrs={"id":f"open_{index}_btn"}).add_text("Open: "+str(index))

    def build_overlay_view(self, overlay_container_div, builder, image_width, image_height):

        initial_zoom = 768 / image_width
        if initial_zoom < 1:
            initial_zoom = 1
        if self.max_zoom and self.max_zoom > initial_zoom:
            max_zoom = self.max_zoom
        else:
            max_zoom = 2048 / image_width

        overlay_container_div.add_element("input", {"type": "button", "id": "grid_view_btn", "value": "Show Grid View"})
        overlay_container_div.add_element("span").add_text(self.title)

        if self.netcdf_download_filename:
            overlay_container_div.add_element("span", {"class": "spacer"}).add_text("|")
            overlay_container_div.add_element("a", {"href": self.netcdf_download_filename,
                                                    "download": self.netcdf_download_filename}).add_text(
                "download netcdf4")

        overlay_container_div.add_element("span", {"class": "spacer"}).add_text("|")
        overlay_container_div.add_element("label", {"for": "zoom_control"}).add_text("Zoom")
        overlay_container_div.add_element("input",
                                          {"type": "range", "id": "zoom_control", "min": 1, "max": int(max_zoom),
                                           "step": 1,
                                           "value": initial_zoom})

        overlay_container_div.add_element("span", {"class": "spacer"}).add_text("|")
        overlay_container_div.add_element("button", {"id": "prev_btn"}).add_text("Previous")
        overlay_container_div.add_element("input", {"type": "range", "id": "time_index"})
        overlay_container_div.add_element("button", {"id": "next_btn"}).add_text("Next")
        overlay_container_div.add_element("span", {"id": "scene_label"}).add_text("?")

        overlay_container_div.add_element("span", {"class": "spacer"}).add_text("|")

        overlay_container_div.add_element("input",
                                          {"type": "checkbox", "id": "show_layers", "checked": "checked"}).add_text(
            "Show Layers")

        overlay_container_div.add_element("span", {"class": "spacer"}).add_text("|")

        if self.filter_controls:
            overlay_container_div.add_element("input",
                {"type": "checkbox", "id": "show_filters", "checked": "checked"}).add_text("Show Filters")

        if self.info:
            overlay_container_div.add_element("input",
                                               {"type": "checkbox", "id": "show_info",
                                                "checked": "checked"}).add_text("Show Info")
        if self.labels:
            overlay_container_div.add_element("input",
                                              {"type": "checkbox", "id": "show_labels",
                                               "checked": "checked"}).add_text("Show Labels")

        controls_div = overlay_container_div.add_element("div", {"id": "layer_container", "class": "control_container"})
        controls_div.add_element("div", {"id": "layer_container_header", "class": "control_container_header"}).add_text(
            "Layers")

        slider_fieldset = controls_div.add_element("fieldset", style={"display": "inline"})
        slider_fieldset.add_element("legend").add_text("Layers")
        slider_container = slider_fieldset.add_element("div", {"id": "legend_controls"})
        slider_table = slider_container.add_element("table", {"id": "slider_controls"})
        slider_container.add_element("input", {"type": "button", "id": "close_all_sliders", "value": "Hide All Layers"})


        for layer_definition in self.layer_definitions:
            row = slider_table.add_element("tr")
            col1 = row.add_element("td")
            col2 = row.add_element("td")
            col3 = row.add_element("td")
            col4 = row.add_element("td")
            col5 = row.add_element("td")
            col6 = row.add_element("td")
            col1.add_text(layer_definition.layer_label)
            opacity_control_id = layer_definition.layer_name + "_opacity"
            col2.add_element("input", {"type": "range", "id": opacity_control_id})

            if layer_definition.has_legend():
                has_data = isinstance(layer_definition,LayerSingleBand) and layer_definition.save_data()
                legend_src = self.layer_legends[layer_definition.layer_name]
                if has_data:
                    col3.add_element("input",{"type":"number","value":str(layer_definition.vmin),"id":layer_definition.layer_name+"_min_input"})
                else:
                    col3.add_element("span").add_text(str(layer_definition.vmin))
                col4.add_element("img", {"src": legend_src, "class": "legend", "id":layer_definition.layer_name+"_legend_img"})
                if has_data:
                    col5.add_element("input", {"type": "number", "value": str(layer_definition.vmax),
                                               "id": layer_definition.layer_name + "_max_input"})
                else:
                    col5.add_element("span").add_text(str(layer_definition.vmax))
                if has_data:
                    selector_control_id = layer_definition.layer_name+"_camp_selector"
                    cmap_selector = col6.add_element("select",{"id":selector_control_id})
                    for cmap in self.all_cmaps:
                        option_attrs = {"value":cmap}
                        if cmap == layer_definition.get_cmap():
                            option_attrs["selected"] = "selected"
                        cmap_selector.add_element("option",option_attrs).add_text(cmap)


        if self.filter_controls:
            filter_div = overlay_container_div.add_element("div", {"id": "filter_container", "class": "control_container"})
            filter_div.add_element("div", {"id": "filter_container_header", "class": "control_container_header"}).add_text(
                "Scene Filters")

            filter_fieldset = filter_div.add_element("fieldset", style={"display": "inline"})
            filter_fieldset.add_element("legend").add_text("Filters")

            month_filter = filter_fieldset.add_element("div", {})

            for month in range(0, 12):
                month_name = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month]
                month_filter.add_element("span").add_text(month_name)
                month_filter.add_element("input", {"id": f"month{month + 1}", "type": "checkbox", "checked": "checked"})

        if self.info:
            info_div = overlay_container_div.add_element("div",
                                                           {"id": "info_container", "class": "control_container"})
            info_div.add_element("div",
                                   {"id": "info_container_header", "class": "control_container_header"}).add_text(
                "Scene Info")

            info_div.add_element("div", attrs={"id":"info_content"})

        if self.labels:
            labels_div = overlay_container_div.add_element("div",
                                                           {"id": "labels_container", "class": "control_container"})
            labels_div.add_element("div",
                                   {"id": "labels_container_header", "class": "control_container_header"}).add_text(
                "Labels")

            labels_div.add_fragment(self.generate_label_controls(None))

        self.layer_definitions.reverse()

        image_container = overlay_container_div.add_element("div")

        image_div = image_container.add_element("div", {"id": "image_div", "class": "image_holder"})
        for layer_definition in self.layer_definitions:
            image_div.add_fragment(ImageFragment("", layer_definition.layer_name))

        builder.body().add_element("span",{"id":"tooltip"})
