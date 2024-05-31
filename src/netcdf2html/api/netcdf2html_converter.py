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
import random
import numpy as np

from .layers import LayerFactory

from netcdf2html.htmlfive.html5_builder import Html5Builder, RawFragment

from netcdf2html.fragments.utils import anti_aliasing_style
from netcdf2html.fragments.image import ImageFragment
from netcdf2html.fragments.table import TableFragment
from netcdf2html.fragments.legend import LegendFragment

js_path = os.path.join(os.path.split(__file__)[0],"index.js")
css_path = os.path.join(os.path.split(__file__)[0],"index.css")

def get_image_dimensions(ds):
    if len(ds.lat.shape) == 2:
        image_height = ds.lat.shape[0]
        image_width = ds.lon.shape[1]
    elif len(ds.lat.shape) == 1:
        image_height = ds.lat.shape[0]
        image_width = ds.lon.shape[1]
    else:
        raise Exception("Unable to determin image dimensions from dataset")
    return (image_width, image_height)

class Netcdf2HtmlConverter:

    def __init__(self, config, input_ds, output_folder, title, sample_count=None, netcdf_download_filename=""):
        dimensions = config.get("dimensions", {})
        case_dimension = dimensions.get("case", "time")
        coordinates = config.get("coordinates", {})
        x_coordinate = coordinates.get("x", "x")
        y_coordinate = coordinates.get("y", "y")
        time_coordinate = coordinates.get("time", "time")
        image = config.get("image", {})
        max_zoom = image.get("max-zoom", None)
        grid_image_width = image.get("grid-width", None)

        self.case_dimension = case_dimension
        self.x_coordinate = x_coordinate
        self.y_coordinate = y_coordinate
        self.time_coordinate = time_coordinate
        self.input_ds = input_ds
        self.output_folder = output_folder
        self.title = title
        self.sample_count = sample_count
        self.max_zoom = max_zoom
        self.grid_image_width = grid_image_width
        self.netcdf_download_filename = netcdf_download_filename
        self.output_html_path = os.path.join(output_folder,"index.html")
        image_folder = os.path.join(self.output_folder,"images")
        os.makedirs(image_folder,exist_ok=True)
        shutil.copyfile(js_path,os.path.join(self.output_folder,"index.js"))
        shutil.copyfile(css_path, os.path.join(self.output_folder, "index.css"))
        self.layer_definitions = []

        self.layer_images = []
        self.layer_legends = {}

        for (layer_name, layer_spec) in config["layers"].items():
            layer = LayerFactory.create(layer_name, layer_spec, self.case_dimension, self.x_coordinate, self.y_coordinate, self.time_coordinate)
            self.layer_definitions.append(layer)

    def get_image_path(self, key, timestamp=""):
        filename = key+timestamp+".png"
        src = os.path.join("images", filename)
        path = os.path.join(self.output_folder, src)
        return (src,path)

    def run(self):
        cases = []

        image_width, image_height = get_image_dimensions(self.input_ds)
        n = len(self.input_ds[self.case_dimension])

        selected_indexes = list(range(n))
        if self.sample_count:
            selected_indexes = np.random.choice(np.array(selected_indexes),self.sample_count,replace=False).tolist()

        for i in selected_indexes:
            timestamp = str(self.input_ds[self.time_coordinate].data[i])[:10] if self.time_coordinate else None
            cases.append((i, timestamp, self.input_ds.isel(**{self.case_dimension:i})))
            cases = sorted(cases,key=lambda t:t[0])

        # check the layers
        for layer_definition in self.layer_definitions:
            err = layer_definition.check(self.input_ds)
            if err:
                raise Exception(err)

        # build the legends
        for layer_definition in self.layer_definitions:
            if layer_definition.has_legend():
                legend_src, legend_path = self.get_image_path(layer_definition.layer_name + "_legend")
                layer_definition.build_legend(legend_path)
                self.layer_legends[layer_definition.layer_name] = legend_src

        # build the images
        for (index, timestamp, ds) in cases:
            image_srcs = {}
            for layer_definition in self.layer_definitions:
                (src, path) = self.get_image_path(layer_definition.layer_name, timestamp=timestamp)
                layer_definition.build(ds, path)
                image_srcs[layer_definition.layer_name] = src
            self.layer_images.append((index, timestamp, image_srcs))

        builder = Html5Builder(language="en")

        builder.head().add_element("title").add_text(self.title)
        builder.head().add_element("style").add_text(anti_aliasing_style)
        builder.head().add_element("script",{"src":"index.js"})
        builder.head().add_element("link", {"rel": "stylesheet", "href":"index.css"})

        root = builder.body().add_element("div")

        container_div = root.add_element("div")
        overlay_container_div = container_div.add_element("div",{"id":"overlay_container"})
        grid_container_div = container_div.add_element("div", {"id": "grid_container","style":"display:none;"})

        self.build_overlay_view(overlay_container_div,builder,image_width,image_height)
        self.build_grid_view(grid_container_div, builder, image_width, image_height)

        with open(self.output_html_path, "w") as f:
            f.write(builder.get_html())

        if self.netcdf_download_filename:
            self.input_ds.to_netcdf(os.path.join(self.output_folder,self.netcdf_download_filename))


    def build_grid_view(self, grid_container_div, builder, image_width, image_height):
        grid_container_div.add_element("input", {"type": "button", "id": "overlay_view_btn", "value": "Show Overlay View"})
        grid_container_div.add_element("span").add_text(self.title)

        if self.netcdf_download_filename:
            grid_container_div.add_element("span", {"class": "spacer"}).add_text("|")
            grid_container_div.add_element("a", {"href": self.netcdf_download_filename, "download": self.netcdf_download_filename}).add_text(
                "download netcdf4")
        
        tf = TableFragment()

        header_cells = ["Index","Time"]
        for layer_definition in self.layer_definitions[::-1]:
            if layer_definition.layer_name in self.layer_legends:
                img = ImageFragment(self.layer_legends[layer_definition.layer_name], layer_definition.layer_name + "_grid_legend", alt_text="legend",
                                    w=self.grid_image_width if self.grid_image_width else image_width)
                vmin = getattr(layer_definition,"vmin",None)
                vmax = getattr(layer_definition,"vmax", None)
                header_cells.append(LegendFragment(layer_definition.layer_label,img,vmin,vmax))
            else:
                header_cells.append(layer_definition.layer_label)
        tf.add_header_row(header_cells)

        for (index, timestamp, layer_sources) in self.layer_images:
            cells = [str(index), timestamp]
            for layer_definition in self.layer_definitions[::-1]:
                src = layer_sources[layer_definition.layer_name]
                img = ImageFragment(src, layer_definition.layer_name+"_grid_"+str(index), alt_text=timestamp, w=self.grid_image_width if self.grid_image_width else image_width)
                cells.append(img)
            tf.add_row(cells)

        grid_container_div.add_fragment(tf)

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
            overlay_container_div.add_element("a", {"href": self.netcdf_download_filename, "download": self.netcdf_download_filename}).add_text(
                "download netcdf4")

        overlay_container_div.add_element("span", {"class": "spacer"}).add_text("|")
        overlay_container_div.add_element("label", {"for": "zoom_control"}).add_text("Zoom")
        overlay_container_div.add_element("input", {"type": "range", "id": "zoom_control", "min": 1, "max": int(max_zoom),
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

        overlay_container_div.add_element("input",
                                       {"type": "checkbox", "id": "show_filters", "checked": "checked"}).add_text(
            "Show Filters")

        controls_div = overlay_container_div.add_element("div", {"id": "layer_container", "class": "control_container"})
        controls_div.add_element("div", {"id": "layer_container_header", "class": "control_container_header"}).add_text(
            "Layers")

        slider_fieldset = controls_div.add_element("fieldset", style={"display": "inline"})
        slider_fieldset.add_element("legend").add_text("Layers")
        slider_container = slider_fieldset.add_element("div")
        slider_table = slider_container.add_element("table", {"id": "slider_controls"})
        slider_container.add_element("input", {"type": "button", "id": "close_all_sliders", "value": "Hide All Layers"})
        layer_list = []

        for layer_definition in self.layer_definitions:
            row = slider_table.add_element("tr")
            col1 = row.add_element("td")
            col2 = row.add_element("td")
            col3 = row.add_element("td")
            col1.add_text(layer_definition.layer_label)
            opacity_control_id = layer_definition.layer_name + "_opacity"
            col2.add_element("input", {"type": "range", "id": opacity_control_id})
            layer_list.insert(0, {"name": layer_definition.layer_name, "opacity_control_id": opacity_control_id})
            if layer_definition.has_legend():
                legend_src = self.layer_legends[layer_definition.layer_name]
                col3.add_element("span").add_text(str(layer_definition.vmin))
                col3.add_element("img", {"src": legend_src, "class": "legend"})
                col3.add_element("span").add_text(str(layer_definition.vmax))

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

        self.layer_definitions.reverse()

        image_container = overlay_container_div.add_element("div")

        time_index = []

        counter = 0

        image_div = image_container.add_element("div", {"id": "image_div", "class": "image_holder"})

        first_slice = True
        layers = []

        for (index, timestamp, layer_sources) in self.layer_images:
            counter += 1
            for layer_definition in self.layer_definitions:
                src = layer_sources[layer_definition.layer_name]

                if first_slice:
                    image_div.add_fragment(ImageFragment(src, layer_definition.layer_name, alt_text=timestamp))
                    layers.insert(0, {"name": layer_definition.layer_name, "label": layer_definition.layer_label})

            time_index.append({"timestamp": timestamp, "image_srcs": layer_sources, "layers": layers})
            first_slice = False

        builder.head().add_element("script").add_text("let all_time_index=" + json.dumps(time_index) + ";")
        builder.head().add_element("script").add_text("let layer_list=" + json.dumps(layer_list) + ";")
        builder.head().add_element("script").add_text("let image_width=" + json.dumps(image_width) + ";")

