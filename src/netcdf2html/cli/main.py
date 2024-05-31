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


from netcdf2html.api.netcdf2html_converter import Netcdf2HtmlConverter

def strip_json5_comments(original):
    # perform a minimal filtering of // comments (a subset of JSON5) and return a JSON compatible string
    lines = original.split("\n")
    parsed = ""
    for line in lines:
        line = line.rstrip()
        inq = False
        for idx in range(len(line)-1):
            if line[idx] == '"':
                inq = not inq
            else:
                if not inq:
                    if line[idx:idx+2] == "//":
                        line = line[:idx].rstrip()  # cut off comment
                        break
        if line:
            if parsed:
                parsed += "\n"
            parsed += line
    return parsed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", help="Set the title of the plot", required=True)
    parser.add_argument("--input-path", help="netcdf4 file or folder containing netcdf4 files to visualise",
                        required=True)
    parser.add_argument("--netcdf-download-filename", help="include the netcdf4 file with this name and add download link in the HTML")
    parser.add_argument("--output-folder", help="folder to write html output", default="html_output")
    parser.add_argument("--config-path", help="JSON file specifying one or more layer specifications",
                        default="layers.json", required=True)

    parser.add_argument("--sample-count", type=int, default=None,
                        help="randomly sample this many cases for display")
    args = parser.parse_args()

    input_ds = xr.open_dataset(args.input_path)

    with open(args.config_path) as f:
        stripped = strip_json5_comments(f.read())
        config = json.loads(stripped)
        c = Netcdf2HtmlConverter(config, input_ds, os.path.abspath(args.output_folder), args.title, sample_count=args.sample_count, netcdf_download_filename=args.netcdf_download_filename)

    c.run()


if __name__ == '__main__':
    main()
