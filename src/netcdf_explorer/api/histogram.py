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

import math
import numpy as np

import matplotlib.pyplot as plt

class Histogram:

    def __init__(self, layer_name, label, band, threshold=None, min_value=None, max_value=None, bin_width=1):
        self.layer_name = layer_name
        self.label = label
        self.band = band
        self.threshold = threshold
        self.min_value = min_value
        self.max_value = max_value
        self.bin_width = bin_width

    def build(self,ds,path):
        data = ds[self.band]
        min_v = data.min(skipna=True).item()
        max_v = data.max(skipna=True).item()
        if math.isnan(min_v) or math.isnan(max_v):
            return
        min_v = math.floor(min_v) if self.min_value is None else self.min_value
        max_v = math.ceil(max_v) if self.max_value is None else self.max_value
        bin_width = 1 if self.bin_width is None else self.bin_width
        bins = np.arange(min_v, max_v, bin_width)
        plt.cla()
        if self.threshold is not None:
            threshold = self.threshold
            # if the threshold is a string use it to look up a variable with this name to get the threshold value
            if isinstance(threshold, str):
                threshold = ds[threshold].item()
            data.where(data < threshold, np.nan).plot.hist(bins=bins)
            data.where(data >= threshold, np.nan).plot.hist(bins=bins)
        else:
            data.plot.hist(bins=bins)
        plt.savefig(path)