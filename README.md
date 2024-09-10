# netcdf_explorer

Generate static HTML for visualising array data read from a netcdf4 file

## Installation

```
conda create -n netcdfexplorer_env python=3.10
conda activate netcdfexplorer_env
conda install netcdf4 xarray matplotlib requests datashader pyproj mako
pip install git+https://github.com/surftemp/netcdf2html.git
```

## Running

```
generate_html --input-path test_input_area97.nc --title "area_97" --output-folder output_folder_with_html --config-path example_layers.json5
```

This will:

* read a dataset from file `test_input.nc`
* create HTML output with layers defined in the file `example_layers.json5` (see below) entitled "Test output for netcdf2html"
* write the generated output html, image files and other associated files to folder `output_folder_with_html`

Open the file `output_folder_with_html/index.html` in your browser to explore the generated imagery

## configuration file

You will need to define a JSON file which maps variables in the input dataset to layers in the generated visualisations

This [commented example configuration file](src/netcdf2html/cli/example_layers.json5) should explain how the configuration file works

## common command line options

| option          | description                                                                                       | example                   |
|-----------------|---------------------------------------------------------------------------------------------------|---------------------------|
 | --title         | specify a title to display at the top of the page                                                 | --title "My Title"        |
 | --input-path    | specify the path of a netcdf4 file containing the input data or a folder containing netcdf4 files | --input-path input.nc     |
 | --config-path   | specify the path of a JSON file containing the configuration                                      | --config-path config.json | 
 | --output-folder | specify output folder into which index.html and image files are written                           | --output-folder html_out  | 

## other command line options

| option                     | description                           | example                              |
|----------------------------|---------------------------------------|--------------------------------------|
 | --sample-count             | limit the number of cases to display  | --sample-count 100                   |
 | --sample-cases             | specify which cases to display        | --sample-cases 4 10 12               |
 | --netcdf-download-filename | provide a link to download the data   | --netcdf-download-filename area97.nc | 


