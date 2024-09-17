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
import os
import json
import xarray as xr
import numpy as np
import logging
import yaml
import sys

from netcdf_explorer.api.html_generator import HTMLGenerator, strip_json5_comments

def subset(ds, case_dimension, sample_count, sample_cases):
    n = len(ds[case_dimension])
    selected_indexes = list(range(n))

    if sample_cases:
        selected_indexes = sample_cases

    if sample_count and sample_count < n:
        selected_indexes = np.random.choice(np.array(selected_indexes), sample_count, replace=False).tolist()

    if sample_cases or sample_count:
        ds = ds.isel(**{case_dimension:selected_indexes})
    return ds, selected_indexes

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", help="Set the title of the plot", required=True)
    parser.add_argument("--input-path", help="netcdf4 file or folder containing netcdf4 files to visualise",
                        required=True)
    parser.add_argument("--netcdf-download-filename",
                        help="include the netcdf4 file with this name and add download link in the HTML")
    parser.add_argument("--output-folder", help="folder to write html output", default="html_output")
    parser.add_argument("--config-path", help="JSON or YAML file specifying one or more layer specifications",
                        default="layers.json", required=True)

    parser.add_argument("--sample-count", type=int, default=None,
                        help="randomly sample this many cases from each file for display")
    parser.add_argument("--file-count", type=int, default=None,
                        help="randomly sample this many files for display")
    parser.add_argument("--sample-cases", nargs="+", type=int, default=None,
                        help="display these sample cases (provide their indices, starting at 0)")
    parser.add_argument("--filter-controls", action="store_true",
                        help="add month filter controls to the overlay view")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    with open(args.config_path) as f:
        if args.config_path.endswith(".yml") or args.config_path.endswith(".yaml"):
            config = yaml.load(f, Loader=yaml.FullLoader)
        else:
            stripped = strip_json5_comments(f.read())
            config = json.loads(stripped)
        dimensions = config.get("dimensions", {})
        coordinates = config.get("coordinates", {})
        case_dimension = dimensions.get("case", None)

    ds_list = []
    filename_list = []
    indices_list = []

    if os.path.isfile(args.input_path):
        input_paths = [args.input_path]
    elif os.path.isdir(args.input_path):
        input_paths = list(map(lambda name: os.path.join(args.input_path, name),
                               list(filter(lambda name: name.endswith(".nc"),os.listdir(args.input_path)))))
    else:
        print(f"Error - {args.input_path} is not a file or directory")
        sys.exit(-1)

    file_count = 0
    for input_path in input_paths:
        file_count += 1
        print(f"[Reading {input_path} {file_count}/{len(input_paths)}]")
        ds = xr.open_dataset(input_path)
        if case_dimension:
            ds, indices = subset(ds, case_dimension, sample_count=args.sample_count, sample_cases=args.sample_cases)
            n = ds[case_dimension].shape[0]
            if case_dimension not in ds[coordinates["x"]].dims:
                ds[coordinates["x"]] = ds[coordinates["x"]].expand_dims({case_dimension:n},axis=0)
            if case_dimension not in ds[coordinates["y"]].dims:
                ds[coordinates["y"]] = ds[coordinates["y"]].expand_dims({case_dimension:n},axis=0)
            for i in indices:
                filename_list.append(input_path)
                indices_list.append(i)
        else:
            filename_list.append(input_path)
            indices_list.append(0)
        ds_list.append(ds)
        if args.file_count is not None and file_count >= args.file_count:
            break

    if case_dimension is None:
        # create a dummy case dimension
        case_dimension = "case"
        config["dimensions"]["case"] = case_dimension
    input_ds = xr.concat(ds_list, dim=case_dimension)

    input_ds["source_filenames"] = xr.DataArray(filename_list,dims=(case_dimension,))
    input_ds["source_indices"] = xr.DataArray(indices_list, dims=(case_dimension,))



    g = HTMLGenerator(config, input_ds, os.path.abspath(args.output_folder), args.title,
                                 sample_count=args.sample_count, sample_cases=args.sample_cases,
                                 netcdf_download_filename=args.netcdf_download_filename,
                                 filter_controls=args.filter_controls)

    g.run()


if __name__ == '__main__':
    main()
