import unittest
import os
import xarray as xr
import json
from netcdf2html.api.netcdf2html_converter import Netcdf2HtmlConverter

class Test(unittest.TestCase):

    def test_293(self):
        # path = os.path.join(os.path.split(__file__)[0],"area_293_min.nc")
        path = "/home/dev/Downloads/area_293_min_labelled.nc"
        ds = xr.open_dataset(path)
        layers_path = os.path.join(os.path.split(__file__)[0],"area_293_min.json")
        output_folder = os.path.join(os.path.split(__file__)[0], "area_293_output")
        with open(layers_path) as f:
            config = json.loads(f.read())
        conv = Netcdf2HtmlConverter(config, ds, output_folder, "area 293", sample_count=None, sample_cases=None,
            netcdf_download_filename="area_293_min.nc", filter_controls=False)
        conv.run()