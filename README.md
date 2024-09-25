# netcdf_explorer

Generate static HTML and images for visualising array data read from a netcdf4 file


* `generate_html`: overlay view
  
![image](https://github.com/user-attachments/assets/7da5100e-f15c-4d76-8d07-b920752c5ec2)

* `generate_html`: grid view
  
![image](https://github.com/user-attachments/assets/b6a408dc-54d4-479f-9bd8-0f50b2326c89)

## Installation

Installation into a miniforge enviromnent is suggested.  See [https://github.com/conda-forge/miniforge](https://github.com/conda-forge/miniforge) for installing miniforge.

```
mamba create -n netcdfexplorer_env python=3.10
mamba activate netcdfexplorer_env
mamba install netcdf4 xarray matplotlib requests datashader pyproj mako pyyaml seaborn pandas flask
pip install git+https://github.com/surftemp/netcdf_explorer.git
```

## generate_html

Use `generate_html` to create a static HTML file and images from a netcdf4 file

```
wget https://github.com/surftemp/netcdf_explorer/raw/main/test/area_293_min.nc
wget https://github.com/surftemp/netcdf_explorer/raw/main/test/example_layers.json5
generate_html --input-path area_293_min.nc --title "area_293" --output-folder output_folder_with_html --config-path example_layers.json5
```

This will:

* read a dataset from file `area_293_min.nc`
* create HTML output with layers defined in the file `example_layers.json5` (see below) entitled "Test output for netcdf2html"
* write the generated output html, image files and other associated files to folder `output_folder_with_html`

Open the file `output_folder_with_html/index.html` in your browser to explore the generated imagery

### configuration file

You will need to define a JSON file or YAML formatted which maps variables in the input dataset to layers in the generated visualisations

This [commented example configuration file](test/example_layers.json5) should explain how the configuration file works

### common command line options

| option          | description                                                                                       | example                   |
|-----------------|---------------------------------------------------------------------------------------------------|---------------------------|
 | --title         | specify a title to display at the top of the page                                                 | --title "My Title"        |
 | --input-path    | specify the path of a netcdf4 file containing the input data or a folder containing netcdf4 files | --input-path input.nc     |
 | --config-path   | specify the path of a JSON file containing the configuration                                      | --config-path config.json | 
 | --output-folder | specify output folder into which index.html and image files are written                           | --output-folder html_out  | 

### other command line options

| option                     | description                           | example                              |
|----------------------------|---------------------------------------|--------------------------------------|
 | --sample-count             | limit the number of cases to display  | --sample-count 100                   |
 | --sample-cases             | specify which cases to display        | --sample-cases 4 10 12               |
 | --netcdf-download-filename | provide a link to download the data in the generated html  | --netcdf-download-filename area97.nc | 


## bigplot

Use `bigplot` to generate potentially large image files as png or pdf files

```
usage: bigplot.py [-h] --input-path INPUT_PATH --input-variable INPUT_VARIABLE
                  [--x X] [--y Y] [--selector coordinate min max]
                  [--iselector dimension min max] [--flip] [--vmin VMIN]
                  [--vmax VMAX] [--vformat VFORMAT] [--cmap CMAP]
                  [--legend-width LEGEND_WIDTH]
                  [--legend-height LEGEND_HEIGHT] [--title TITLE]
                  [--title-height TITLE_HEIGHT] [--font-path FONT_PATH]
                  [--output-path OUTPUT_PATH] [--plot-width PLOT_WIDTH]
```

Example usage:

```
bigplot --input-path data.nc --input-variable myvar --title "MyVAR plot" --cmap viridis --vmin 0 --vmax 100 --output-path plot.png
```

## acknowledgements

`generate_html` incorporates code from leafletjs - see [https://leafletjs.com/](https://leafletjs.com/)




