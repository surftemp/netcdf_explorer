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

import xarray as xr
import argparse
try:
    from .generate_html import subset
except:
    from generate_html import subset

import glob

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-paths", nargs="+", help="netcdf4 files to combine", required=True)
    parser.add_argument("--output-path", help="folder to write html output", default="combined.nc")
    parser.add_argument("--file-count", type=int, default=None,
                        help="randomly sample this many files")

    args = parser.parse_args()

    all_input_paths = []
    for input_path in args.input_paths:
        all_input_paths += glob.glob(input_path,recursive=True)

    ds = xr.open_mfdataset(all_input_paths)
    ds.to_netcdf(args.output_path)

if __name__ == '__main__':
    main()