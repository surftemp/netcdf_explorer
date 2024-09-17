import unittest
import os
import xarray as xr
import json
from netcdf_explorer.api.html_generator import HTMLGenerator, strip_json5_comments


class Test(unittest.TestCase):

    def test_293_api(self):
        path = os.path.join(os.path.split(__file__)[0],"area_293_min.nc")
        ds = xr.open_dataset(path)
        layers_path = os.path.join(os.path.split(__file__)[0],"example_layers.json5")
        output_folder = os.path.join(os.path.split(__file__)[0], "area_293_output_api")
        with open(layers_path) as f:
            config = json.loads(strip_json5_comments(f.read()))
        gen = HTMLGenerator(config=config, input_ds=ds, output_folder=output_folder, title="area 293", sample_count=None, sample_cases=None,
            netcdf_download_filename="area_293_min.nc", filter_controls=False)
        gen.run()

    def test_293_commandline(self):
        cli_test = 'python -m netcdf_explorer.cli.generate_html --input-path area_293_min.nc --title "area_293" --output-folder area_293_output_cli --config-path example_layers.json5'
        os.system(f'(cd {os.path.split(__file__)[0]}; {cli_test})')
