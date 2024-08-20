import argparse
import logging
import os.path
import glob
import xarray as xr
import numpy as np
import itertools

def test_pairs(collisions):
    permutations = list(itertools.permutations(collisions,2))
    pairs = set()
    for (a,b) in permutations:
        if (a,b) not in pairs and (b,a) not in pairs:
            pairs.add((a,b))
    return pairs

def test_duplicates(input_paths, variables, output_folder):

    if output_folder:
        os.makedirs(output_folder,exist_ok=True)

    hashes = {}
    for variable in variables:
        hashes[variable] = {}

    # look for hash collisions
    for path in input_paths:
        logging.info(f"Opening {path}")
        ds = xr.open_dataset(path)
        n = ds.i.shape[0]
        for variable in variables:
            for i in range(n):
                arr = ds[variable].isel(i=i).data
                bytes = arr.tobytes()
                hv = str(hash(bytes))
                if hv in hashes[variable]:
                    hashes[variable][hv].append((i,path))
                else:
                    hashes[variable][hv] = [(i,path)]

    # check if collisions are true duplicates
    duplicates = 0
    removals = {}
    for variable in hashes:
        for hv in hashes[variable]:
            collisions = hashes[variable][hv]
            for (collision1,collision2) in test_pairs(collisions):
                (i1, path1) = collision1
                (i2, path2) = collision2
                da1 = xr.open_dataset(path1)[variable]
                da2 = xr.open_dataset(path2)[variable]
                arr1 = da1.isel(i=i1)
                arr2 = da2.isel(i=i2)
                if np.array_equal(arr1,arr2):
                    logging.warning(f"Arrays {path1}/{variable}/{i1} and {path2}/{variable}/{i2} are identical")
                    # schedule for removal
                    if path1 < path2 or (path1 == path2 and i1 < i2):
                        removal_path = path2
                        removal_index = i2
                    else:
                        removal_path = path1
                        removal_index = i1
                    if removal_path not in removals:
                        removals[removal_path] = []
                    if removal_index not in removals[removal_path]:
                        removals[removal_path].append(removal_index)
                    duplicates += 1

    logging.info(f"Found {duplicates} duplicates")

    if output_folder:
        for path in input_paths:
            ds = xr.open_dataset(path)
            output_path = os.path.join(output_folder,os.path.split(path)[-1])
            logging.info(f"Deduplicating {path} to {output_path}")
            if path in removals:
                indices = removals[path]
                logging.info(f"\tRemoving {len(indices)} duplicate items")
                ds = ds.drop_isel(i=indices)
            ds.to_netcdf(output_path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-path", help="netcdf4 file or folder containing netcdf4 files to check for duplicates",
                        required=True)
    parser.add_argument("--variables", nargs="+", required=True,
                        help="variables to test for")
    parser.add_argument("--output-folder", help="folder to write de-duplicated files to")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if os.path.isfile(args.input_path):
        input_paths = [args.input_path]
    else:
        input_paths = glob.glob(os.path.join(args.input_path,"*.nc"),recursive=True)

    test_duplicates(input_paths, args.variables, args.output_folder)

if __name__ == '__main__':
    main()