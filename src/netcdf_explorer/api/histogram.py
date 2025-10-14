import math
import numpy as np

import matplotlib.pyplot as plt
from xarray.tests.test_formatting_html import test_short_data_repr_html


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