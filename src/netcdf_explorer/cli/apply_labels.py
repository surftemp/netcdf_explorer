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

import argparse
import json
import xarray as xr

def apply_labels(labels_path, netcdf_path):
    with open(labels_path) as f:
        labels = json.loads(f.read())
    case_dimension = labels["case_dimension"]
    values = labels["values"]
    ds = xr.Dataset()
    for label_group in values:
        ds[label_group] = xr.DataArray(values[label_group],dims=(case_dimension,))
    ds.to_netcdf(netcdf_path, mode="a")

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("labels_path", help="path to labels file")
    parser.add_argument("netcdf_path", help="path to netcdf4 file to annotate with labels")

    args = parser.parse_args()
    apply_labels(args.labels_path, args.netcdf_path)



if __name__ == '__main__':
    main()
