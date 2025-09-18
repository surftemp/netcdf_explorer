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
generate_html --input-path area_293_min.nc --title "area_293" --output-folder output_folder_with_html --config-path example_layers.yaml
```

This will:

* read a dataset from file `area_293_min.nc`
* create HTML output with layers defined in the file `example_layers.yaml` (see below) entitled "Test output for netcdf2html"
* note - configuration files may be supplied in yaml or json format
* write the generated output html, image files and other associated files to folder `output_folder_with_html`

Open the file `output_folder_with_html/index.html` in your browser to explore the generated imagery

### configuration file

You will need to define a JSON file or YAML formatted which maps variables in the input dataset to layers in the generated visualisations

This [commented example configuration file](test/example_layers.yaml) should explain how the configuration file works

### common command line options

| option          | description                                                                                       | example                   |
|-----------------|---------------------------------------------------------------------------------------------------|---------------------------|
 | --title         | specify a title to display at the top of the page                                                 | --title "My Title"        |
 | --input-path    | specify the path of a netcdf4 file containing the input data or a folder containing netcdf4 files | --input-path input.nc     |
 | --config-path   | specify the path of a JSON file containing the configuration                                      | --config-path config.json | 
 | --output-folder | specify output folder into which index.html and image files are written                           | --output-folder html_out  | 

### other command line options

| option          | description                                                | example                   |
|-----------------|------------------------------------------------------------|---------------------------|
 | --sample-count  | limit the number of cases to display                       | --sample-count 100        |
 | --sample-cases  | specify which cases to display                             | --sample-cases 4 10 12    |
 | --download-data | provide a link to download this data in the generated html | --download-data area97.nc | 


## bigplot

Use `bigplot` to generate potentially large image files as png or pdf files

```
usage: bigplot [-h] --input-path INPUT_PATH --input-variable INPUT_VARIABLE [INPUT_VARIABLE ...] [--x X] [--y Y] [--selector coordinate min max] [--iselector dimension min max] [--flip] [--vmin VMIN]
               [--vmax VMAX] [--vformat VFORMAT] [--cmap CMAP] [--legend-width LEGEND_WIDTH] [--legend-height LEGEND_HEIGHT] [--title TITLE] [--title-height TITLE_HEIGHT] [--attrs ATTRS [ATTRS ...]]
               [--attr-height ATTR_HEIGHT] [--font-path FONT_PATH] [--output-path OUTPUT_PATH] [--plot-width PLOT_WIDTH]

```

Example usage - plot a single variable:

```
bigplot --input-path data.nc --input-variable myvar --title "MyVAR plot" --cmap viridis --vmin 0 --vmax 100 --output-path plot.png
```

Example usage - true colour plot of red, green and blue bands

```
bigplot --input-path 20250129124009-NCEO-L1C-Landsat9-v2.0-fv01.0.nc --input-variable B4 B3 B2 --output-path test.png --title "Iceland Scene" --attrs acquisition_time platform
```

<img width="532" height="624" alt="image" src="https://github.com/user-attachments/assets/48355014-2a7e-4b13-a935-a9844d05cd36" />



## General Command Line Options:

| option           | description                                                                                                            | example                                        |
|------------------|------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| --input-path     | path to netcdf input file                                                                                              | --input-path test_data.nc                      |
| --input-variable | name of variable(s) to plot. Supply either one variable or three variables (red,green,blue)                            | --input-variable V3                            |
| --x              | name of x dimension if not "x"                                                                                         | --x lon                                        |
| --y              | name of y dimension if not "y"                                                                                         | --y lat                                        |                                                                      
| --selector       | provide a coordinate selector in the format <coordinate> <min> <max>                                                   | --selector lat 40 41 --selector lon 20 21      |
| --iselector      | provide a dimension selector in the format <dimension> <min> <max>                                                     | --iselector x 3000 4000 -iselector y 2500 3500 |
| --flip           | whether to flip the image upside down                                                                                  |                                                | 
| --title          | Set a title for the plot                                                                                               | --title "My Plot"                              |
| --title-height   | Set the height of title text in pixels                                                                                 | --title-height 40                              |
| --attrs          | Specify one or more attributes to display under the title                                                              | --attrs platform sensor                        |
| --attr-height    | Height of attribute text                                                                                               | --attr-height 20                               |
| --font-path      | Path to a true-type (.ttf) font to use (defaults to Roboto)                                                            | --font-path myfont.ttf                         |
| --output-path    | Path to an output png or pdf file                                                                                      | --output-path output.pdf                       | 
| --plot-width     | Width of the main image plot, in pixels                                                                                | --plot-width 500                               |

## Command Line Options for plotting continuous data from a single variable

| option           | description                                                                                                            | example                                        |
|------------------|------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| --vmin           | minimum input variable value to use in colour scale                                                                    | --vmin 0                                       |
| --vmax           | maximum input variable value to use in colour scale                                                                    | --vmax 1                                       |
| --vformat        | format to use when printing values                                                                                     | --vformat "%0.1f"                              |
| --cmap           | colour scale to use, should be the name of a matplotlib color map                                                      | --cmap viridis                                 |
| --legend-width   | set the width of the legend in pixels                                                                                  | --legend-width 300                             |
| --legend-height  | set the height of the legend in pixels                                                                                 | --legend-height 50                             |                         

## Command Line Options for plotting discrete data from a single variable

| option          | description                                                                                                            | example                                        |
|-----------------|------------------------------------------------------------------------------------------------------------------------|------------------------------------------------|
| --cchart <PATH> | path to a JSON format {<value>:<colour>} colour chart mapping nominal values to colours, overrides --cmap if specified | --chart colour_map.json                        |

The format of the JSON `cchart` file is explained by the following example which maps value 0 to "red", 1 to "green" and 2 to "blue:

```json
{
  "0": "#FF0000",
  "1": "#00FF00",
  "2": "#0000FF"
}
```

## Acknowledgements

This repo incorporates code from:

| Project   | License              | GitHub                                                                             |
|-----------|----------------------|------------------------------------------------------------------------------------|
| leafletjs | BSD 2-Clause License | [https://leafletjs.com/](https://leafletjs.com/)                                   |
| babylonJS | Apache V2 License    | [https://github.com/BabylonJS/Babylon.js](https://github.com/BabylonJS/Babylon.js) |
| dygraphs  | MIT License          | [https://github.com/danvk/dygraphs](https://github.com/danvk/dygraphs)             |






