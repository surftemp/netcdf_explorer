# source this file, ie . ./test_install.sh

mamba create -y -n netcdfexplorer_test_env python=3.10
mamba activate netcdfexplorer_test_env
mamba install -y netcdf4 xarray matplotlib requests datashader pyproj mako pyyaml seaborn pandas flask
pip install git+https://github.com/surftemp/netcdf_explorer.git

mkdir test_install
cd test_install

wget https://github.com/surftemp/netcdf_explorer/raw/main/test/area_293_min.nc
wget https://github.com/surftemp/netcdf_explorer/raw/main/test/example_layers.json5
generate_html --input-path area_293_min.nc --title "area_293" --output-folder output_folder_with_html --config-path example_layers.json5

mamba deactivate
mamba env remove -n netcdf_explorer_env -y
