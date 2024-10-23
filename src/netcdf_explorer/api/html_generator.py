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

import csv
import datetime
import os
import sys

import xarray as xr
import shutil
import json
import numpy as np
from mako.template import Template
import pyproj
import logging
import copy


from .layers import LayerFactory, LayerSingleBand, LayerWMS
from .expr_parser import ExpressionParser

from netcdf_explorer.htmlfive.html5_builder import Html5Builder, ElementFragment

from netcdf_explorer.fragments.utils import anti_aliasing_style
from netcdf_explorer.fragments.image import ImageFragment
from netcdf_explorer.fragments.table import TableFragment
from netcdf_explorer.fragments.legend import LegendFragment
from netcdf_explorer.fragments.select import SelectFragment

src_folder = os.path.split(__file__)[0]

js_paths = [os.path.join(src_folder, "cmap.js"),
            os.path.join(src_folder, "data_image.js"),
            os.path.join(src_folder, "leaflet_map.js"),
            os.path.join(src_folder, "timeseries_chart.js"),
            os.path.join(src_folder, "terrain_view.js"),
            os.path.join(src_folder, "html_view.js")]

css_path = os.path.join(src_folder, "index.css")

dygraph_dependency_paths = [os.path.join(src_folder,"..","dependencies","dygraph.css"),
                    os.path.join(src_folder,"..","dependencies","dygraph.js")]

babylonjs_dependency_paths = [os.path.join(src_folder,"..","dependencies","babylon.js"),
                    os.path.join(src_folder,"..","dependencies","babylonTerrain.js")]

class Progress(object):

    def __init__(self,label):
        self.label = label
        self.last_progress_frac = None

    def report(self,msg,progress_frac):
        if self.last_progress_frac == None or (progress_frac - self.last_progress_frac) >= 0.01:
            self.last_progress_frac = progress_frac
            i = int(100*progress_frac)
            if i > 100:
                i = 100
            si = i // 2
            sys.stdout.write("\r%s %s %-05s %s" % (self.label,msg,str(i)+"%","#"*si))
            sys.stdout.flush()

    def complete(self,msg):
        self.report(msg, 1)
        sys.stdout.write("\n")
        sys.stdout.flush()


class HTMLGenerator:

    def __init__(self, config, input_ds, output_folder, title, sample_count=None, sample_cases=None,
                 download_from=None, filter_controls=False):

        dimensions = config.get("dimensions", {})
        coordinates = config.get("coordinates", {})
        image = config.get("image", {})

        self.case_dimension = dimensions.get("case", "")
        self.x_dimension = dimensions.get("x", "")
        self.y_dimension = dimensions.get("y", "")
        self.x_coordinate = coordinates.get("x", "")
        self.y_coordinate = coordinates.get("y", "")
        self.time_coordinate = coordinates.get("time", "")
        self.input_ds = input_ds

        self.data_width = None
        self.data_height = None

        if self.x_dimension:
            self.data_width = self.input_ds.sizes[self.x_dimension]
        if self.y_dimension:
            self.data_height = self.input_ds.sizes[self.y_dimension]

        self.output_folder = output_folder
        self.title = title
        self.sample_count = sample_count
        self.sample_cases = sample_cases
        self.max_zoom = image.get("max-zoom", None)
        self.grid_image_width = image.get("grid-width", None)
        self.netcdf_download_filename = os.path.split(download_from)[-1] if download_from else ""
        self.output_html_path = os.path.join(output_folder, "index.html")
        self.filter_controls = filter_controls
        self.info = config.get("info",{})
        self.crs = config.get("crs",None)
        self.labels = config.get("labels",None)
        self.logger = logging.getLogger("generate_html")
        self.timeseries = config.get("timeseries",{})
        self.derive_bands = config.get("derive_bands",{})
        self.terrain_view = config.get("terrain_view",{})

        self.parser = ExpressionParser()
        self.parser.add_unary_operator("not")
        self.parser.add_binary_operator("*", 5)
        self.parser.add_binary_operator("/", 5)
        self.parser.add_binary_operator("+", 4)
        self.parser.add_binary_operator("-", 4)
        self.parser.add_binary_operator("|", 3)
        self.parser.add_binary_operator("&", 3)
        self.parser.add_binary_operator("==",2)
        self.parser.add_binary_operator("and",1)
        self.parser.add_binary_operator("or",1)

        self.build_derived_bands()

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
        if download_from:
            shutil.copyfile(download_from, os.path.join(self.output_folder, self.netcdf_download_filename))

        # copy in dependencies
        dependency_folder = os.path.join(self.output_folder, "dependencies")
        os.makedirs(dependency_folder, exist_ok=True)

        if self.timeseries:
            for dependency_path in dygraph_dependency_paths:
                filename = os.path.split(dependency_path)[-1]
                shutil.copyfile(dependency_path,os.path.join(dependency_folder, filename))

        if self.terrain_view:
            for dependency_path in babylonjs_dependency_paths:
                filename = os.path.split(dependency_path)[-1]
                shutil.copyfile(dependency_path,os.path.join(dependency_folder, filename))

        self.layer_definitions = []

        self.layer_images = []
        self.layer_data = []
        self.layer_legends = {}

        self.timeseries_definitions = []

        if self.x_coordinate:
            self.input_ds = self.reduce_coordinate_dimension(self.input_ds, self.x_coordinate, self.case_dimension)
        if self.y_coordinate:
            self.input_ds = self.reduce_coordinate_dimension(self.input_ds, self.y_coordinate, self.case_dimension)

        if "layers" in config:
            for (layer_name, layer_spec) in config["layers"].items():
                layer = LayerFactory.create(self, layer_name, layer_spec)
                self.layer_definitions.append(layer)

        if "timeseries" in config:
            for (timeseries_name, timeseries_spec) in config["timeseries"]["plots"].items():
                valid_variables = []
                for variable in timeseries_spec["variables"]:
                    variable_components = variable.split(":")
                    variable_name = variable_components[0]
                    if variable_name in self.input_ds:
                        valid_variables.append(variable)
                if valid_variables:
                    timeseries_spec["variables"] = valid_variables
                    self.timeseries_definitions.append((timeseries_name, timeseries_spec, {}))

        self.all_cmaps = sorted(["Purples", "gist_rainbow", "gist_ncar", "Blues", "Greys", "autumn", "gist_gray", "magma", "Set3",
                     "cool", "tab20c", "GnBu", "brg", "cividis", "Pastel1", "YlOrRd", "Spectral", "gist_earth", "PuBu",
                     "OrRd", "PuRd", "plasma", "winter", "PuBuGn", "inferno", "bwr", "RdGy", "Wistia", "gist_stern",
                     "gist_heat", "BuGn", "twilight", "RdBu", "twilight_shifted", "Paired", "PiYG", "RdYlBu", "Dark2",
                     "CMRmap", "BuPu", "gnuplot", "PRGn", "nipy_spectral", "ocean", "viridis", "bone", "BrBG",
                     "gnuplot2", "Oranges", "turbo", "YlGn", "PuOr", "hot", "Set2", "afmhot", "hsv", "YlOrBr",
                     "terrain", "Accent", "copper", "cubehelix", "RdPu", "tab10", "Reds", "Greens", "gray", "rainbow",
                     "spring", "tab20", "pink", "coolwarm", "RdYlGn", "Set1", "tab20b", "flag", "gist_yarg", "binary",
                     "YlGnBu", "seismic", "prism", "Pastel2", "jet", "summer"], key=lambda v:v.lower())

        for cmap in self.all_cmaps:
            source_path = os.path.join(os.path.abspath(os.path.split(__file__)[0]),"..","misc","cmaps", cmap+".json")
            dest_path = os.path.join(cmap_folder, cmap + ".json")
            shutil.copyfile(source_path, dest_path)

    def flatten_layers(self, layer_definitions, only_grid_view=False, only_overlay_view=False):
        flattened_layers = []
        for layer in layer_definitions:
            if only_grid_view and not layer.get_grid_view():
                continue
            if only_overlay_view and not layer.get_overlay_view():
                continue
            if layer.get_sublayers() is not None:
                flattened_layers += layer.get_sublayers()
            else:
                flattened_layers.append(layer)
        return flattened_layers

    def build_derived_bands(self):
        for (mask_name, mask_expression) in self.derive_bands.items():
            from_bands = []
            parsed_expression = self.parser.parse(mask_expression)
            arr = self.evaluate_expression(parsed_expression, from_bands)
            dims = []
            # the dimensions of the derived band should match the longest dimensions of the input bands
            for band in from_bands:
                if len(self.input_ds[band].dims) > len(dims):
                    dims = self.input_ds[band].dims
            self.input_ds[mask_name] = xr.DataArray(arr,dims=dims)

    def evaluate_expression(self, parsed_expression, from_bands_accumulator):
        if "name" in parsed_expression:
            from_bands_accumulator.append(parsed_expression["name"])
            return self.input_ds[parsed_expression["name"]].data
        elif "operator" in parsed_expression:
            operator = parsed_expression["operator"]
            args = parsed_expression["args"]
            arrays = []
            for arg in args:
                arrays.append(self.evaluate_expression(arg,from_bands_accumulator))
            if operator == "==":
                assert len(args) == 2
                return np.equal(arrays[0],arrays[1])
            elif operator == "&":
                assert len(args) == 2
                return np.bitwise_and(np.astype(arrays[0],int),np.astype(arrays[1],int))
            elif operator == "|":
                assert len(args) == 2
                return np.bitwise_or(np.astype(arrays[0],int), np.astype(arrays[1],int))
            elif operator == "and":
                assert len(args) == 2
                return np.logical_and(np.astype(arrays[0],int),np.astype(arrays[1],int))
            elif operator == "or":
                assert len(args) == 2
                return np.logical_or(np.astype(arrays[0],int), np.astype(arrays[1],int))
            elif operator == "not":
                assert(len(args) == 1)
                return np.logical_not(arrays[0])
            elif operator == "*":
                assert len(args) == 2
                return np.multiply(arrays[0],arrays[1])
            elif operator == "/":
                assert len(args) == 2
                return np.divide(arrays[0],arrays[1])
            elif operator == "+":
                assert len(args) == 2
                return np.add(arrays[0],arrays[1])
            elif operator == "-":
                assert len(args) == 2
                return np.subtract(arrays[0], arrays[1])
            else:
                raise Exception(f"Unknown operator: {operator}")
        elif "literal" in parsed_expression:
            return np.array([parsed_expression["literal"]])

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
            filename = f"{key}_{index}.png"
        else:
            filename = f"{key}.png"
        src = os.path.join("images", filename)
        path = os.path.join(self.output_folder, src)
        return (src, path)

    def get_data_path(self, key, index=None):
        if index is not None:
            filename = f"{key}_{index}.gz"
        else:
            filename = f"{key}.gz"
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
        image_width = None
        image_height = None
        label_values = None

        if self.layer_definitions:
            image_width, image_height = self.get_image_dimensions(self.input_ds)

            n = len(self.input_ds[self.case_dimension])

            p = Progress("Reading data")
            for i in range(n):
                p.report("", i/n)
                timestamp = str(self.input_ds[self.time_coordinate].data[i])[:10] if self.time_coordinate else None
                cases.append((i, timestamp, self.input_ds.isel(**{self.case_dimension: i})))
                if self.time_coordinate:
                    cases = sorted(cases, key=lambda t: t[1])
            p.complete("Done")

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
            for layer_definition in self.flatten_layers(self.layer_definitions):
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

            p = Progress("Building images")

            static_image_srcs = {}
            static_data_srcs = {}

            for layer_definition in self.flatten_layers(self.layer_definitions):
                if not layer_definition.get_case_wise():
                    (src, path) = self.get_image_path(layer_definition.layer_name)
                    layer_definition.build(self.input_ds, path)
                    static_image_srcs[layer_definition.layer_name] = src
                    if layer_definition.save_data():
                        (data_src, data_path) = self.get_data_path(layer_definition.layer_name)
                        data_options = layer_definition.build_data(self.input_ds, data_path)
                        static_data_srcs[layer_definition.layer_name] = {"url": data_src, "options": data_options}

            for (index, timestamp, ds) in cases:
                p.report("",index/n)
                image_srcs = {}
                data_srcs = {}

                for layer_definition in self.flatten_layers(self.layer_definitions):
                    if layer_definition.get_case_wise():
                        (src, path) = self.get_image_path(layer_definition.layer_name, index=index)
                        layer_definition.build(ds, path)
                        image_srcs[layer_definition.layer_name] = src
                        if layer_definition.save_data():
                            (data_src, data_path) = self.get_data_path(layer_definition.layer_name, index)
                            data_options = layer_definition.build_data(ds, data_path)
                            data_srcs[layer_definition.layer_name] = {"url":data_src, "options":data_options}
                    else:
                        image_srcs[layer_definition.layer_name] = static_image_srcs[layer_definition.layer_name]
                        if layer_definition.save_data():
                            data_srcs[layer_definition.layer_name] = static_data_srcs[layer_definition.layer_name]

                if self.labels:
                    for label_group in self.labels:
                        if label_group not in label_values["values"]:
                            label_values["values"][label_group] = []
                        if label_group in ds:
                            label_values["values"][label_group].append(ds[label_group].item())
                        else:
                            label_values["values"][label_group].append(None)


                self.layer_images.append((index, timestamp, image_srcs, data_srcs, ds))

            p.complete("Done")

        # build timeseries if any are defined
        if self.timeseries_definitions:

            folder = os.path.join(self.output_folder, "timeseries")
            os.makedirs(folder, exist_ok=True)
            for (timeseries_name, timeseries_spec, timeseries_detail) in self.timeseries_definitions:
                csv_path = os.path.join(folder, timeseries_name + ".csv")
                source_masks = timeseries_spec.get("masks", [])
                variables = timeseries_spec["variables"]
                with open(csv_path,"w") as f:
                    writer = csv.writer(f)
                    headers = ["datetime"]
                    if source_masks:
                        for source_mask in source_masks:
                            for variable in variables:
                                headers.append(f"{source_mask}_{variable.replace(':','_')}")
                    else:
                        headers += variables

                    writer.writerow(headers)
                    n = len(self.input_ds[self.time_coordinate])

                    for i in range(n):
                        timestamp = str(self.input_ds[self.time_coordinate].data[i])[
                                    :10] if self.time_coordinate else None

                        data_slice = self.input_ds.isel(**{self.case_dimension:i})

                        dt = datetime.datetime.strptime(timestamp, "%Y-%m-%d")
                        row = [dt.strftime("%Y-%m-%d")]

                        if source_masks:
                            # build a timseries for each combination of mask and variable
                            for source_mask in source_masks:
                                mask_slice = self.input_ds[source_mask].squeeze()
                                if self.case_dimension in mask_slice.dims:
                                    mask_slice = mask_slice.isel(**{self.case_dimension:i})

                                for variable in variables:
                                    variable_components = variable.split(":")
                                    variable_name = variable_components[0]
                                    if len(variable_components)==2:
                                        aggregation_fn = variable_components[1]
                                    else:
                                        aggregation_fn = "mean"
                                    values = xr.where(mask_slice, data_slice[variable_name], np.nan)
                                    if aggregation_fn == "mean":
                                        value = values.mean(skipna=True).item()
                                    elif aggregation_fn == "min":
                                        value = values.min(skipna=True).item()
                                    elif aggregation_fn == "max":
                                        value = values.max(skipna=True).item()
                                    else:
                                        raise Exception(f"Cannot apply unrecognised aggregation function {aggregation_fn}")
                                    row.append(str(value))
                        else:
                            for variable in timeseries_spec["variables"]:
                                value = data_slice[variable].item()
                                row.append(str(value))

                        writer.writerow(row)

                timeseries_detail["csv_url"] = os.path.join("timeseries", timeseries_name + ".csv")

        builder = Html5Builder(language="en")

        builder.head().add_element("title").add_text(self.title)
        builder.head().add_element("style").add_text(anti_aliasing_style)
        builder.head().add_element("script", {"src": "index.js"})
        builder.head().add_element("link", {"rel": "stylesheet", "href": "index.css"})
        builder.head().add_element("link", {"rel": "stylesheet", "href":"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
                                            "integrity":"sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=", "crossorigin":""})
        builder.head().add_element("script", {"src":"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
                                              "integrity":"sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=",
                                              "crossorigin":""})

        # dygraphs
        if self.timeseries:
            builder.head().add_element("script", {"type": "text/javascript", "src":"dependencies/dygraph.js"})
            builder.head().add_element("link", {"type": "text/css", "rel":"stylesheet", "href": "dependencies/dygraph.css"})

        # babylonJS
        if self.terrain_view:
            builder.head().add_element("script", {"type": "text/javascript", "src": "dependencies/babylon.js"})
            builder.head().add_element("script", {"type": "text/javascript", "src": "dependencies/babylonTerrain.js"})

        root = builder.body().add_element("div")

        container_div = root.add_element("div")

        display_timeseries = len(self.timeseries_definitions) > 0
        if self.layer_definitions:
            overlay_container_div = container_div.add_element("div",
                                                              {"id": "overlay_container", "style": "display:none;"})
            grid_container_div = container_div.add_element("div", {"id": "grid_container", "style": "display:none;"})
            self.build_overlay_view(overlay_container_div, builder, image_width, image_height)
            self.build_grid_view(grid_container_div, builder, image_width, image_height, display_timeseries=display_timeseries)

        if display_timeseries:
            timeseries_container_div = container_div.add_element("div", {"id": "timeseries_container",
                                                                         "style": "display:none;"})

            self.build_timeseries_view(timeseries_container_div, builder)

        if self.terrain_view:
            terrain_container_div = container_div.add_element("div", {"id": "terrain_container", "style":"display:none;"})
            self.build_terrain_view(terrain_container_div, builder)

        scenes = { "layers":[], "index": [], "layer_groups":{} }

        if self.terrain_view:
            scenes["terrain_view"] = self.terrain_view

        for layer_definition in self.flatten_layers(self.layer_definitions):
            layer_dict = {"name": layer_definition.layer_name, "label": layer_definition.layer_label, "has_data": layer_definition.save_data()}
            if isinstance(layer_definition,LayerWMS):
                layer_dict["wms_url"] = layer_definition.wms_url
            scenes["layers"].insert(0, layer_dict)

        for layer_definition in self.flatten_layers(self.layer_definitions):
            group = layer_definition.get_group()
            if group:
                group_layer_name = group.layer_name
                if group_layer_name not in scenes["layer_groups"]:
                    scenes["layer_groups"][group_layer_name] = []
                scenes["layer_groups"][group_layer_name].append(layer_definition.layer_name)

        for (index, timestamp, layer_sources, data_sources, ds) in self.layer_images:

            info = {}
            if self.info:
                info = self.generate_info_dict(index, ds)

            scene_dict = {"timestamp": timestamp if timestamp is not None else "", "image_srcs": layer_sources,
                               "data_srcs": data_sources, "info": info, "pos":index}
            for layer_definition in self.flatten_layers(self.layer_definitions):
                if isinstance(layer_definition, LayerWMS):
                    ((x_min, y_min), (x_max, y_max)) = layer_definition.get_bounds(ds)
                    scene_dict["x_min"] = x_min
                    scene_dict["x_max"] = x_max
                    scene_dict["y_min"] = y_min
                    scene_dict["y_max"] = y_max

            scenes["index"].append(scene_dict)

        with open(os.path.join(self.output_folder, "scenes.json"), "w") as f:
            f.write(json.dumps(scenes,indent=4))

        if image_width:
            builder.head().add_element("script").add_text("let image_width=" + json.dumps(image_width) + ";")

        if self.timeseries_definitions:
            timeseries = []
            for (timeseries_name, timeseries_spec, timeseries_detail) in self.timeseries_definitions:
                timeseries.append({
                    "name": timeseries_name,
                    "spec": timeseries_spec,
                    "csv_url": timeseries_detail["csv_url"],
                    "div_id": timeseries_detail["div_id"]
                })
            with open(os.path.join(self.output_folder, "timeseries.json"), "w") as f:
                f.write(json.dumps(timeseries, indent=4))

        self.logger.info(f"writing {self.output_html_path}")
        with open(self.output_html_path, "w") as f:
            f.write(builder.get_html())

        if label_values:
            with open(os.path.join(self.output_folder, "labels.json"),"w") as f:
                f.write(json.dumps(label_values, indent=4))

        os.makedirs(os.path.join(self.output_folder, "service_info"), exist_ok=True)
        with open(os.path.join(self.output_folder, "service_info", "services.json"), "w") as f:
            f.write(json.dumps({}, indent=4))

    def build_grid_view(self, grid_container_div, builder, image_width, image_height, display_timeseries=False):
        grid_container_div.add_element("input",
                                       {"type": "button", "id": "overlay_view_btn", "value": "Show Overlay View"})
        if display_timeseries:
            grid_container_div.add_element("input",
                                       {"type": "button", "id": "timeseries_view_btn", "value": "Show Timeseries View"})

        grid_container_div.add_element("span").add_text(self.title)

        if self.netcdf_download_filename:
            grid_container_div.add_element("span", {"class": "spacer"}).add_text("|")
            grid_container_div.add_element("a", {"href": self.netcdf_download_filename,
                                                 "download": self.netcdf_download_filename}).add_text(
                "download netcdf4")

        tf = TableFragment()

        columns_hidden = [False]
        column_ids = ["index_col"]

        if self.info:
            column_ids += ["info"]
            columns_hidden += [False]

        if self.labels:
            column_ids += ["labels"]
            columns_hidden += [False]

        groups = set()

        for layer_definition in self.flatten_layers(self.layer_definitions, only_grid_view=True)[::-1]:
            group = layer_definition.get_group()
            columm_id = layer_definition.layer_name + "_col"
            column_ids.append(columm_id)
            if group and group in groups:
                columns_hidden.append(True) # this column is one of a group and not the first, hide it initially
            else:
                columns_hidden.append(False)
            if group:
                groups.add(group)

        tf.set_column_ids(column_ids, columns_hidden)

        header_cells = ["Index"]
        if self.info:
            header_cells.append("Info")
        if self.labels:
            header_cells.append("Labels")
        for layer_definition in self.flatten_layers(self.layer_definitions,only_grid_view=True)[::-1]:
            label = layer_definition.layer_label
            group = layer_definition.get_group()
            if group:
                label = group.layer_label
            header_div = ElementFragment("div")
            if layer_definition.layer_name in self.layer_legends:
                img = ImageFragment(self.layer_legends[layer_definition.layer_name],
                                    layer_definition.layer_name + "_grid_legend", alt_text="legend",
                                    w=self.grid_image_width if self.grid_image_width else image_width)
                vmin = getattr(layer_definition, "vmin", None)
                vmax = getattr(layer_definition, "vmax", None)
                header_div.add_fragment(LegendFragment(label, img, vmin, vmax))
            else:
                label_fragment = ElementFragment("span").add_text(label)
                header_div.add_fragment(label_fragment)
            group = layer_definition.get_group()
            if group:
                sf = SelectFragment({"id": layer_definition.layer_name + "_group_select"})
                for layer in group.get_layers():
                    sf.add_option(layer.layer_name, layer.layer_label,
                                  is_selected=(layer.layer_name == layer_definition.layer_name))
                header_div.add_fragment(ElementFragment("br"))
                header_div.add_fragment(sf)
            header_cells.append(header_div)
        tf.add_header_row(header_cells)

        button_cells = [""]
        if self.info:
            button_cells.append("")
        if self.labels:
            button_cells.append(self.generate_label_buttons())

        for layer_definition in self.flatten_layers(self.layer_definitions, only_grid_view=True)[::-1]:
            button_cells.append(
                ElementFragment("button", {"id": layer_definition.layer_name + "_hide"}).add_text("Hide"))

        tf.add_header_row(button_cells)

        current_group_label = ""
        for (index, timestamp, layer_sources, _, ds) in self.layer_images:
            cells = [self.generate_index_cell(index)]
            if self.info:
                cells += [self.generate_info_table(index,ds)]
            if self.labels:
                cells += [self.generate_label_controls(index)]
            for layer_definition in self.flatten_layers(self.layer_definitions,only_grid_view=True)[::-1]:
                src = layer_sources[layer_definition.layer_name]
                img = ImageFragment(src, layer_definition.layer_name + "_grid_" + str(index), alt_text=timestamp,
                                    w=self.grid_image_width if self.grid_image_width else image_width)
                cells.append(img)
            tf.add_row(cells)

        grid_container_div.add_fragment(tf)

    def generate_index_cell(self, index):
        return ElementFragment("button",attrs={"id":f"open_{index}_btn"}).add_text("Open: "+str(index))

    def build_overlay_view(self, overlay_container_div, builder, image_width, image_height):

        overlay_container_div.add_element("input", {"type": "button", "id": "grid_view_btn", "value": "Show Grid View"})
        overlay_container_div.add_element("span").add_text(self.title)

        if self.netcdf_download_filename:
            overlay_container_div.add_element("span", {"class": "spacer"}).add_text("|")
            overlay_container_div.add_element("a", {"href": self.netcdf_download_filename,
                                                    "download": self.netcdf_download_filename}).add_text(
                "download netcdf4")

        has_data = False
        for layer_definition in self.flatten_layers(self.layer_definitions):
            if layer_definition.has_legend():
                if isinstance(layer_definition,LayerSingleBand) and layer_definition.save_data():
                    has_data = True
                    break

        overlay_container_div.add_element("span", {"class": "spacer"}).add_text("|")
        overlay_container_div.add_element("button", {"id": "prev_btn"}).add_text("Previous")
        overlay_container_div.add_element("input", {"type": "range", "id": "time_index"})
        overlay_container_div.add_element("button", {"id": "next_btn"}).add_text("Next")
        overlay_container_div.add_element("span", {"id": "scene_label"}).add_text("?")

        overlay_container_div.add_element("span", {"class": "spacer"}).add_text("|")

        if self.terrain_view:
            overlay_container_div.add_element("button", {"id": "terrain_view_btn"}).add_text("Terrain View")
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

        if has_data:
            overlay_container_div.add_element("input",
                                              {"type": "checkbox", "id": "show_data",
                                               "checked": "checked"}).add_text("Show Data")

        controls_div = overlay_container_div.add_element("div", {"id": "layer_container", "class": "control_container"})
        controls_div.add_element("div", {"id": "layer_container_header", "class": "control_container_header"}).add_text(
            "Layers")

        slider_fieldset = controls_div.add_element("fieldset", style={"display": "inline"})
        slider_fieldset.add_element("legend").add_text("Layers")
        slider_container = slider_fieldset.add_element("div", {"id": "legend_controls"})
        slider_table = slider_container.add_element("table", {"id": "slider_controls"})
        slider_container.add_element("input", {"type": "button", "id": "close_all_sliders", "value": "Hide All Layers"})

        groups = set()
        for layer_definition in self.flatten_layers(self.layer_definitions, only_overlay_view=True):

            group = layer_definition.get_group()
            style = {}
            if group and group in groups:
                style["display"] = "none"
            if group:
                groups.add(group)

            row = slider_table.add_element("tr", attrs={"id":layer_definition.layer_name+"_overlay_row"},style=style)
            col1 = row.add_element("td")
            col2 = row.add_element("td")
            col3 = row.add_element("td")
            col4 = row.add_element("td")
            col5 = row.add_element("td")
            col6 = row.add_element("td")

            if group:
                col1.add_text(group.layer_label)
                sf = SelectFragment({"id": layer_definition.layer_name + "_group_select_row"})
                for layer in group.get_layers():
                    sf.add_option(layer.layer_name, layer.layer_label,
                                  is_selected=(layer.layer_name == layer_definition.layer_name))
                col1.add_fragment(sf)
            else:
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

        if has_data:
            data_div = overlay_container_div.add_element("div",
                                                           {"id": "data_container", "class": "control_container"})
            data_div.add_element("div",
                                   {"id": "data_container_header", "class": "control_container_header"}).add_text(
                "Data")
            data_div.add_element("div", attrs={"id":"data_content"})

        self.layer_definitions.reverse()

        overlay_container_div.add_element("div",{"id":"map"})


    def build_timeseries_view(self, timeseries_container_div, builder):
        if self.layer_definitions:
            timeseries_container_div.add_element("input", {"type": "button", "id": "grid_view_btn2", "value": "Show Grid View"})

        timeseries_container_div.add_element("span").add_text(self.title)

        timeseries_container_div.add_element("h2").add_text("timeseries")

        for (timeseries_name,timeseries_spec, timeseries_detail) in self.timeseries_definitions:

            timeseries_title = timeseries_spec.get("title",timeseries_name)

            timeseries_container_div.add_element("h3").add_text(timeseries_title)
            timeseries_div_id = f"timeseries_{timeseries_name}"
            timeseries_container_div.add_element("div",{"id":timeseries_div_id, "class":"timeseries_chart"})
            timeseries_detail["div_id"] = timeseries_div_id

    def build_terrain_view(self, terrain_container_div, builder):
        terrain_container_div.add_element("input", {"id": "exit_terrain_view", "type":"button", "value":"Exit Terrain View"})
        terrain_container_div.add_element("span", {"class": "spacer"}).add_text("|")
        terrain_container_div.add_element("label", attrs={"for": "terrain_zoom"}).add_text("Exaggerate Terrain")
        terrain_container_div.add_element("input", {"id":"terrain_zoom", "step":"0.1", "type": "range", "min": "1", "max": "10", "value":"1"})
        terrain_container_div.add_element("span", {"id": "terrain_zoom_value"}).add_text("1")
        terrain_container_div.add_element("p")
        terrain_container_div.add_element("canvas",{"id": "render_canvas"})
