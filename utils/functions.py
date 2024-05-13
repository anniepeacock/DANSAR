#!/usr/bin/env python

"""
Functions for making GIS-ready products with UAVSAR and NISAR Simulated Data 
"""

import os
import numpy as np
import math
import rasterio as rio
from osgeo import gdal
import requests

def download_files(urls, destination_dir, username=username, password=password):
  """
  Function to download files from a list of URLs and save them to a specified destination directory.
  
  Args:
  - urls (list): List of URLs to download files from
  - destination_dir (str): Directory where downloaded files will be saved
  - username (str): NASA Earthdata Username for download authentication
  - password (str): NASA Earthdata Username Password for download authentication
   """
   os.makedirs(destination_dir, exist_ok=True)  # Create destination directory if it doesn't exist
   
   for url in urls:
    filename = os.path.basename(url)
    destination_path = os.path.join(destination_dir, filename)
    
    # Download file from URL
    response = requests.get(url, auth=(username, password))
    if response.status_code == 200:
      with open(destination_path, 'wb') as f:
        f.write(response.content)
        print(f"Downloaded: {filename}")
        else:
          print(f"Failed to download: {filename}, Status code: {response.status_code}")


def process_grd_files(input_dir, output_dir, window=None, projection=None):
  """
  Function to take all the UAVSAR GRD files in an input directory and save as GeoTIFFs.
  Can set new extents and projections for the output GeoTIFF.

  Args:
  - input_dir (str): The directory path where the input UAVSAR GRD files are located.
  - output_dir (str): The directory path where the output GeoTIFF files will be saved.
  - window (tuple, optional): Specifies the output bounds for the GeoTIFF files. If not provided, input files' bounds will be used.
  - projection (str, optional): Specifies the output spatial reference system (SRS) for the GeoTIFF files. If not provided, input file's projection will be used.
  """
  grd_files = [file for file in os.listdir(input_dir) if file.endswith('.grd')]
  for grd_file in grd_files:
    input_path = os.path.join(input_dir, grd_file)
    output_path = os.path.join(output_dir, grd_file.replace('.grd', '_clipped.tif'))
    gdal.Warp(output_path, input_path, format='GTiff', outputBounds=window, dstSRS=projection)


def process_inc_files(input_dir, output_dir, window=None, projection=None):
  """ 
  Function to take all the UAVSAR local incidence angle (*.INC) files in an input directory and save as GeoTIFFs.
  Checks corresponding GRD filtes to resample the incidence angle file to match the GRD file (required for use with NISAR Simulate data)
  Can set new extents and projections for the output GeoTIFF.

  Args:
  - input_dir (str): The directory path where the input UAVSAR INC files are located.
  - output_dir (str): The directory path where the output GeoTIFF files will be saved.
  - window (tuple, optional): Specifies the output bounds for the GeoTIFF files. If not provided, input files' bounds will be used.
  - projection (str, optional): Specifies the output spatial reference system (SRS) for the GeoTIFF files. If not provided, input file's projection will be used.
  """
  inc_files = [file for file in os.listdir(input_dir) if file.endswith('.inc')]
  for inc_file in inc_files:
    input_path = os.path.join(input_dir, inc_file)
    output_path = os.path.join(output_dir, inc_file.replace('.inc', '_inc_resampled.tif'))
    # Get resolution from the corresponding GRD file (Incidence Angle files will need to be resampled for use with NISAR Simulated data)
    # to resample the incidence angle file to match the resolution of the GRD file.
    reprojected_grd = [file for file in os.listdir(output_dir) if file.endswith('_clipped.tif')]
    if reprojected_grd:
      reprojected_grd_path = os.path.join(output_dir, reprojected_grd[0])
      reprojected_grd_info = gdal.Info(reprojected_grd_path, format='json')
      x_resolution = reprojected_grd_info['geoTransform'][1]
      y_resolution = abs(reprojected_grd_info['geoTransform'][5])
      gdal.Warp(output_path, input_path, format='GTiff', outputBounds=window, dstSRS=projection, xRes=x_resolution, yRes=y_resolution)
    else:
        print("No clipped GRD file found")

def mask_and_save(input_directory, output_directory):
  """
  Function to mask the UAVSAR GeoTIFF files of high/low incidence angles and save the masked data as new GeoTIFF files.
  Matches data files (ending with '_clipped.tif') with corresponding incidence angle files (ending with '_inc_resampled.tif') 

  Args:
  - input_directory (str): The directory path where the input GeoTIFF files and their corresponding incidence angle files are located.
  - output_directory (str): The directory path where the masked GeoTIFF files will be saved.
  """
    files = os.listdir(input_directory)
    relevant_data_files = [file for file in files if file.endswith('_clipped.tif')]
    relevant_inc_files = [file for file in files if file.endswith('_inc_resampled.tif')]
    # Loop through each relevant data file
    for data_file in relevant_data_files:
        for inc_file in relevant_inc_files:
            if data_file[:12] == inc_file[:12]:  # Matching first 12 characters of GeoTIFF & corresponding incidence angle geotiff
                data_filename = os.path.join(input_directory, data_file)
                inc_filename = os.path.join(input_directory, inc_file)
                output_filename = os.path.join(output_directory, data_file.replace('_clipped.tif', '_masked.tif'))
                with rio.open(data_filename) as data_src, rio.open(inc_filename) as inc_src:
                    data = data_src.read(1)
                    inc_data = inc_src.read(1)
                    # Perform calculations on data
                    masked_data = data / np.cos(inc_data)
                    masked_data[inc_data < 0.261799] = np.nan # mask where incidence angle is less than 15 degrees (0.261799 radians)
                    masked_data[inc_data > 1.22173] = np.nan # mask where incidence angle is greater than 70 degrees (1.22173 radians)
                    # Save the masked data
                    profile = data_src.profile
                    profile.update(dtype=masked_data.dtype, nodata=np.nan)
                    with rio.open(output_filename, 'w', **profile) as dst:
                        dst.write(masked_data, 1)
                break  # Match found, exit inner loop

def convert_db(data):
  """
  Function to convert UAVSAR data in linear radar power units to decibels (dB)
  
  Args:
  - data (float): array of UAVSAR values in linear radar power units
  """
  db = 10*(math.log(data))
  return db


