import unittest
import os
import xarray as xr
import numpy as np
import json

from netcdf_explorer.api.html_generator import HTMLGenerator

class Test(unittest.TestCase):

    def __make_mandlebrot(self, width, height, niter):
        # rustle up an old school mandlebrot, makes a nice test pattern...
        # based on https://tomroelandts.com/articles/how-to-compute-the-mandelbrot-set-using-numpy-array-operations
        m = width
        n = height

        x = np.linspace(-2, 1, num=m).reshape((1, m))
        y = np.linspace(-1, 1, num=n).reshape((n, 1))
        C = np.tile(x, (n, 1)) + 1j * np.tile(y, (1, m))

        Z = np.zeros((n, m), dtype=complex)
        M = np.full((n, m), True, dtype=bool)

        count = np.zeros((n, m), dtype=int)  # count the iterations to escape
        for i in range(niter):
            Z[M] = Z[M] * Z[M] + C[M]
            M[np.abs(Z) > 2] = False
            count = np.where(np.logical_and(count == 0, M == False), i, count)

        return xr.DataArray(data=count, dims=("y", "x"))

    def test_293_api(self):
        path = os.path.join(os.path.split(__file__)[0],"area_293_min.nc")
        ds = xr.open_dataset(path)
        layers_path = os.path.join(os.path.split(__file__)[0],"example_layers.json")
        output_folder = os.path.join(os.path.split(__file__)[0], "area_293_output_api")
        with open(layers_path) as f:
            config = json.loads(f.read())
        gen = HTMLGenerator(config=config, input_ds=ds, output_folder=output_folder, title="area 293", sample_count=None, sample_cases=None,
            download_from=path, filter_controls=False)
        gen.run()

    def test_293_commandline(self):
        cli_test = 'python -m netcdf_explorer.cli.generate_html --input-path area_293_min.nc --title "area_293" --output-folder area_293_output_cli --config-path example_layers.yaml --download-data area_293_min.nc'
        os.system(f'(cd {os.path.split(__file__)[0]}; {cli_test})')

    def test_bigplot(self):
        da = self.__make_mandlebrot(500,500,256)

        from netcdf_explorer.api.bigplot import BigPlot
        bp = BigPlot(data_array=da,
                     x="x", y="y", vmin=0, vmax=256, vformat="%d",
                     cmap_name="viridis",
                     title="mandelbrot", output_path="mandelbrot.png")
        bp.run()
        # check the PNG was generated correctly - should automate this

    def test_bigplot_commandline(self):
        da = self.__make_mandlebrot(500, 500, 256)
        ds = xr.Dataset()
        ds["mandlebrot"] = da
        ds.to_netcdf("mandlebrot.nc")
        cli_test = 'python -m netcdf_explorer.cli.bigplot --input-path mandlebrot.nc --input-variable mandlebrot --output-path mandlebrot_cmdline.png --title "mandlebrot" --vmin 0 --vmax 256 --cmap viridis --vformat "%d"'
        os.system(f'(cd {os.path.split(__file__)[0]}; {cli_test})')
