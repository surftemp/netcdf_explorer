# MIT License
#
# Copyright (C) 2023-2024 National Centre For Earth Observation (NCEO)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software
# and associated documentation files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
# BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import xarray as xr

from netcdf_explorer.api.bigplot import BigPlot

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", help="path to netcdf input file", required=True)
    parser.add_argument("--input-variable", help="name of variable to plot", required=True)
    parser.add_argument("--x", help="name of x dimension", default="x")
    parser.add_argument("--y", help="name of y dimension", default="y")
    parser.add_argument("--selector", nargs=3, help="provide a coordinate selector", metavar=("coordinate","min","max"), action="append")
    parser.add_argument("--iselector", nargs=3, help="provide a dimension selector", metavar=("dimension", "min", "max"),
                        action="append")
    parser.add_argument("--flip", help="whether to flip the image upside down", action="store_true")
    parser.add_argument("--vmin", type=float, help="minimum input variable value to use in colour scale", default=275)
    parser.add_argument("--vmax", type=float, help="maximum input variable value to use in colour scale", default=305)
    parser.add_argument("--vformat", help="format to use when printing values", default="%0.0f")
    parser.add_argument("--cmap", help="colour scale to use, should be the  name of a matplotlib color map", default="turbo")
    parser.add_argument("--legend-width", help="width of the legend in pixels", type=int, default=100)
    parser.add_argument("--legend-height", help="height of the legend in pixels", type=int, default=50)
    parser.add_argument("--title", help="A title for the plot")
    parser.add_argument("--title-height", help="Height of title in pixels", default=50)
    parser.add_argument("--font-path", help="Path to a true-type (.ttf) font to use (defaults to Roboto)", default=None)
    parser.add_argument("--output-path", help="Path to an output png or pdf file", default="uk_scores.pdf")
    parser.add_argument("--plot-width", help="Width of the main image plot, in pixels", type=int, default=1024)

    args = parser.parse_args()

    selectors = {}
    iselectors = {}

    if args.selector:
        for (coordinate, min, max) in args.selector:
            selectors[coordinate] = slice(min,max)

    if args.iselector:
        for (dimension, min, max) in args.selector:
            iselectors[dimension] = range(min, max+1)

    ds = xr.open_dataset(args.input_path)

    da = ds[args.input_variable]

    bp = BigPlot(data_array=da,
            x=args.x, y=args.y, vmin=args.vmin, vmax=args.vmax,vformat=args.vformat,
            cmap_name=args.cmap,
            legend_width=args.legend_width, legend_height=args.legend_height,
            title=args.title,theight=args.title_height, output_path=args.output_path, plot_width=args.plot_width, flip=args.flip,
            selectors=selectors, iselectors=iselectors, font_path=args.font_path)
    bp.run()

if __name__ == '__main__':
    main()