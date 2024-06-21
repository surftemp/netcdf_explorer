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
import shutil
import requests

from PIL import Image
from matplotlib import cm
import numpy as np

from .colours import colours_to_rgb

def save_image(arr,vmin,vmax,path,cmap_name="coolwarm"):
    if not hasattr(cm,cmap_name):
        raise ValueError("Unknown colour map: " + cmap_name)
    cmap_fn = getattr(cm,cmap_name)
    im = Image.fromarray(np.uint8((255*cmap_fn((arr-vmin)/(vmax-vmin)))))
    im.save(path)

def save_image_falsecolour(data_red, data_green, data_blue, path):
    alist = []
    for arr in [data_red, data_green, data_blue]:
        minv = np.nanmin(arr)
        maxv = np.nanmax(arr)
        v = (arr - minv) / (maxv - minv)
        v = np.sqrt(v) # this boosts the contrast
        alist.append((255*v).astype(np.uint8))
    arr = np.stack(alist,axis=-1)
    im = Image.fromarray(arr,mode="RGB")
    im.save(path)

def save_image_mask(arr, path, r, g, b, mask):
    if mask is not None:
        arr = np.bitwise_and(arr,mask)
    alist = []
    a = np.zeros(arr.shape)
    alist.append((a + r).astype(np.uint8))
    alist.append((a + g).astype(np.uint8))
    alist.append((a + b).astype(np.uint8))
    alist.append(np.where(arr>0,255,0).astype(np.uint8))
    rgba_arr = np.stack(alist, axis=-1)
    im = Image.fromarray(rgba_arr, mode="RGBA")
    im.save(path)


class LayerBase:

    def __init__(self, layer, converter, layer_name, layer_label, selectors={}):
        self.layer_name = layer_name
        self.layer_label = layer_label
        self.case_dimension = ""
        self.x_coordinate = ""
        self.y_coordinate = ""
        self.case_dimension = ""
        self.selectors = selectors
        self.flipud = False
        self.fliplr = False
        self.converter = converter
        self.case_dimension = layer.get("dimensions",{}).get("case",converter.case_dimension)
        self.x_dimension = layer.get("dimensions",{}).get("x",converter.x_dimension)
        self.y_dimension = layer.get("dimensions",{}).get("y",converter.y_dimension)
        self.time_coordinate = layer.get("coordinates",{}).get("time",converter.time_coordinate)
        self.x_coordinate = layer.get("coordinates",{}).get("x",converter.x_coordinate)
        self.y_coordinate = layer.get("coordinates",{}).get("y",converter.y_coordinate)

    def check(self, ds):
        for variable in [self.x_coordinate, self.y_coordinate, self.time_coordinate]:
            if variable and variable not in ds:
                return f"No variable {variable}"
        xc = self.converter.get_x_coords(ds)
        yc = self.converter.get_y_coords(ds)
        if len(xc.shape) != 1:
            return "x_coordinate {self.x_coordinate} must be 1-dimensional"
        if len(yc.shape) != 1:
            return "y_coordinate {self.y_coordinate} must be 1-dimensional"

        if float(xc.data[0]) > float(xc.data[-1]):
            self.fliplr = True
        if float(yc.data[0]) < float(yc.data[-1]):
            self.flipud = True

    def get_data(self, da):
        if self.selectors:
            da = da.isel(**self.selectors)
        da = da.squeeze()
        ndims = len(da.dims)
        if ndims != 2:
            raise Exception("Data is not 2D")

        x_index = da.dims.index(self.x_dimension)
        y_index = da.dims.index(self.y_dimension)
        arr = da.data
        if y_index > x_index:
            arr = np.transpose(arr)
        if self.flipud:
            arr = np.flipud(arr)
        if self.fliplr:
            arr = np.fliplr(arr)
        return arr


class LayerRGB(LayerBase):

    def __init__(self, layer, converter, layer_name, layer_label, selectors, red_variable, green_variable, blue_variable):
        super().__init__(layer, converter, layer_name, layer_label, selectors)
        self.red_variable = red_variable
        self.green_variable = green_variable
        self.blue_variable = blue_variable

    def has_legend(self):
        return False

    def check(self, ds):
        err = super().check(ds)
        if err:
            return err
        for variable in [self.red_variable, self.green_variable, self.blue_variable]:
            if variable not in ds:
                return f"No variable {variable}"

    def build(self,ds,path):
        red = self.get_data(ds[self.red_variable])
        green = self.get_data(ds[self.green_variable])
        blue = self.get_data(ds[self.blue_variable])

        save_image_falsecolour(red, green, blue, path)


class LayerSingleBand(LayerBase):

    def __init__(self, layer, converter, layer_name, layer_label, selectors, band_name, vmin, vmax, cmap_name):
        super().__init__(layer, converter, layer_name, layer_label, selectors)
        self.band_name = band_name
        self.vmin = vmin
        self.vmax = vmax
        self.cmap_name = cmap_name

    def check(self, ds):
        err = super().check(ds)
        if err:
            return err
        if self.band_name not in ds:
            return f"No variable {self.band_name}"

    def build(self,ds,path):
        save_image(self.get_data(ds[self.band_name]), self.vmin, self.vmax, path, self.cmap_name)

    def has_legend(self):
        return True

    def build_legend(self, path):
        legend_width, legend_height = 200, 20
        a = np.zeros(shape=(legend_height,legend_width))
        for i in range(0,legend_width):
            a[:,i] = self.vmin + (i/legend_width) * (self.vmax-self.vmin)
        save_image(a, self.vmin, self.vmax, path, self.cmap_name)


class LayerWMS(LayerBase):

    def __init__(self, layer, converter, layer_name, layer_label, wms_url, scale):
        super().__init__(layer, converter, layer_name, layer_label)
        self.wms_url = wms_url
        self.cache = {}
        self.failed = set()
        self.scale = scale

    def has_legend(self):
        return False

    def build(self,ds,path):
        if os.path.exists(path):
            os.remove(path)
        image_width, image_height = self.converter.get_image_dimensions(ds)
        image_width *= self.scale
        image_height *= self.scale

        xc = self.converter.get_x_coords(ds)
        yc = self.converter.get_y_coords(ds)

        spacing_x = abs(float(xc[0]) - float(xc[1]))
        spacing_y = abs(float(yc[0]) - float(yc[1]))

        x_min = float(xc.min()) - spacing_x/2
        x_max = float(xc.max()) + spacing_x/2
        y_min = float(yc.min()) - spacing_y/2
        y_max = float(yc.max()) + spacing_y/2
        url = self.wms_url.replace("{WIDTH}",str(image_width)).replace("{HEIGHT}",str(image_height)) \
            .replace("{YMIN}",str(y_min)).replace("{YMAX}",str(y_max)) \
            .replace("{XMIN}",str(x_min)).replace("{XMAX}", str(x_max))

        if url in self.cache:
            shutil.copyfile(self.cache[url],path)
        elif url in self.failed:
            pass
        else:
            print("Fetching:"+url)
            r = requests.get(url, stream=True)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, f)
                self.cache[url] = path
            else:
                print("Failed")
                self.failed.add(url)

class LayerMask(LayerBase):

    def __init__(self, layer, converter, layer_name, layer_label, selectors, band_name, r, g, b, mask):
        super().__init__(layer, converter, layer_name, layer_label, selectors)
        self.band_name = band_name
        self.r = r
        self.g = g
        self.b = b
        self.mask = mask

    def has_legend(self):
        return False

    def check(self, ds):
        err = super().check(ds)
        if err:
            return err
        if self.band_name not in ds:
            return f"No variable {self.band_name}"

    def build(self,ds,path):
        save_image_mask(self.get_data(ds[self.band_name].astype(int)), path, self.r, self.g, self.b, self.mask)

class LayerFactory:

    @staticmethod
    def create(converter, layer_name, layer):
        layer_type = layer["type"]
        layer_label = layer.get("label", layer_name)
        selectors = layer.get("selectors", {})
        if layer_type == "single":
            layer_band = layer.get("band", layer_name)
            vmin = layer["min_value"]
            vmax = layer["max_value"]
            cmap = layer.get("cmap", "coolwarm")
            created_layer = LayerSingleBand(layer, converter, layer_name, layer_label, selectors, layer_band, vmin, vmax, cmap)
        elif layer_type == "mask":
            layer_band = layer.get("band", layer_name)
            if "colour" in layer:
                colour = layer["colour"]
                if colour in colours_to_rgb:
                    rgb = colours_to_rgb[layer["colour"]]
                    r = rgb["r"]
                    g = rgb["g"]
                    b = rgb["b"]
                else:
                    raise Exception(f"Unknown colour {colour}")
            else:
                r = layer.get("r",0)
                g = layer.get("g",0)
                b = layer.get("b",0)

            mask = layer.get("mask", None)
            created_layer = LayerMask(layer, converter, layer_name, layer_label, selectors, layer_band, r, g, b, mask)
        elif layer_type == "rgb":
            red_band = layer["red_band"]
            green_band = layer["green_band"]
            blue_band = layer["blue_band"]
            created_layer = LayerRGB(layer, converter, layer_name, layer_label, selectors, red_band, green_band, blue_band)
        elif layer_type == "wms":
            url = layer["url"]
            scale = layer.get("scale", 1)
            created_layer = LayerWMS(layer, converter, layer_name, layer_label, url, scale)
        else:
            raise Exception(f"Unknown layer type {layer_type}")

        return created_layer


