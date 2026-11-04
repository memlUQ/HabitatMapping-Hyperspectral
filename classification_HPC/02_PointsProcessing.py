#Dylan Cowley: 09/09/2026
#Python version 3.10 or greater required
#Package requirements:
#    - rasterio, numpy, pandas, matplotlib, geopandas, shapely, zarr, warnings, os, time

# %% (0) IMPORT PACKAGES
import rasterio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
from shapely.geometry import Point
import zarr
import warnings
import argparse
import os
import time
import sys

# read variables from configuration files
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))) # add folder for this script to path
from params import TARGET_CRS # coordinate reference system
from params import CLASS_COLUMN, ROOT # file/folder details

# parse command-line arguments
parser = argparse.ArgumentParser(description='Preprocess satellite imagery for benthic habitat mapping.')
parser.add_argument('YEAR_MONTH', type=str, help='Year and month of imagery (e.g., 202502)')
parser.add_argument('SITE_NAME', type=str, help='Site name (e.g., Adelaide)')
parser.add_argument('SITE_ID', type=str, help='Site identifier (e.g., AD)')
parser.add_argument('SENSOR', type=str, choices=['Planet', 'PRISMA', 'PRISMA_PAN_sharpened', 'EnMAP', 'Kanyini', 'Wyvern'], help='Sensor/platform name')
parser.add_argument('DEPTH_MAX', type=str, help='Maximum depth for mapping in cm (e.g., 2000)')
args = parser.parse_args()
 
YEAR_MONTH = args.YEAR_MONTH
SITE_NAME = args.SITE_NAME
SITE_ID = args.SITE_ID
SENSOR = args.SENSOR
DEPTH_MAX = args.DEPTH_MAX

# %% (1) USER INPUT
s = time.time()
print("Defining user input...", end=" ")

# --------------- (a) set main constants ---------------
CAL_PER = 80 # percentage of field data used for calibration
N_MC = 100 # number of Monte Carlo iterations
SAMP_SEED = 42 # specific seed for initiation

# --------------- (b) define red, green, and blue bands ---------------
if SENSOR == 'Planet':
    R = 6 # assign RED band (for visualisation)
    G = 4 # assign GREEN band (for visualisation)
    B = 2 # assign BLUE band (for visualisation)
    RMV_BANDS = [] # bands to remove
elif SENSOR == 'PRISMA':
    R = 36 # assign RED band (for visualisation)
    G = 48 # assign GREEN band (for visualisation)
    B = 60 # assign BLUE band (for visualisation)
    RMV_BANDS = ['b1','b2','b66'] # bands to remove

# --------------- (c) setup asset directories and define file names ---------------
pwd = os.path.join(ROOT, SITE_FLDR, 'Mapping_Joanna')

# inputs
roi_geometry = SITE_NAME+'_Shpfl.shp' # FILE for region of interest [SHAPEFILE]
phys_fldr = os.path.join(pwd, '02_physical_layers') # FOLDER for physical layers
roi_file = os.path.join(phys_fldr, roi_geometry) # FILE geometry for mapping region of interest
raw_image = os.path.join(pwd, '03_raw_imagery', YEAR_MONTH, SITE_NAME+'_'+SENSOR+'_'+YEAR_MONTH) # FOLDER for unprocessed satellite imagery
processed_image = os.path.join(pwd, '04_processed_imagery', YEAR_MONTH, SITE_ID+'_'+SENSOR+'_'+YEAR_MONTH+'_processed') # FILE for processed satellite imagery
field_data = os.path.join(pwd, '01_benthic_data', YEAR_MONTH, SITE_ID+'_'+YEAR_MONTH+'_classified') # FILE for field data

# outputs
mc_zarr_output = os.path.join(pwd, '05_training_data', YEAR_MONTH, SITE_ID+'_'+SENSOR+'_'+YEAR_MONTH+'_mc_training.zarr') # Monte Carlo training points
tpts_output = os.path.join(pwd, '05_training_data', YEAR_MONTH, SITE_ID+'_'+SENSOR+'_'+YEAR_MONTH + '_tpts.csv')

os.makedirs(os.path.join(pwd, '05_training_data', YEAR_MONTH), exist_ok=True)

print("done.\nSuccess! User input defined.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (2) LOAD ASSETS
s = time.time()
print("\nLoading processed image...", end=" ")

# --------------- (a) load processed image ---------------
pi = rasterio.open(processed_image+'.tif')

print("done.\nLoading field data...", end=" ")

# --------------- (b) load field data ---------------
tpts = pd.read_csv(field_data+'.csv')

print("done.\nChecking CRS alignment...", end=" ")

# --------------- (c) check CRS alignment ---------------
# create GeoDataFrame from the training points
geometry = [Point(xy) for xy in zip(tpts['Longitude'], tpts['Latitude'])]
tpts_gdf = gpd.GeoDataFrame(tpts, geometry=geometry, crs=TARGET_CRS)

# ensure CRS matches
tpts_gdf = tpts_gdf.to_crs(TARGET_CRS)

# update the coordinates in the dataframe
tpts['Longitude'] = tpts_gdf.geometry.x
tpts['Latitude'] = tpts_gdf.geometry.y

# convert back to regular DataFrame
tpts = pd.DataFrame(tpts_gdf.drop(columns='geometry'))

print("done.\nSuccess! Field data loaded.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (3) PREPARE IMAGE BANDS AND PIXEL LOOKUP
s = time.time()
print("\nPreparing image bands and extracting pixel values...", end=" ")

# --------------- (a) read all image bands once ---------------
all_bands = pi.read() # shape: (n_bands, height, width)
n_bands_raw = all_bands.shape[0]

# --------------- (b) remove unwanted bands ---------------
band_names_raw = list(pi.descriptions)
rmv_idx = [i for i, b in enumerate(band_names_raw) if b in RMV_BANDS]
keep_idx = [i for i in range(n_bands_raw) if i not in rmv_idx]

all_bands = all_bands[keep_idx, :, :]
band_names_filtered = [band_names_raw[i] for i in keep_idx]
n_bands = all_bands.shape[0]

# --------------- (c) convert point coordinates to row/col ---------------
all_lons = tpts['Longitude'].values
all_lats = tpts['Latitude'].values
all_rows, all_cols = rasterio.transform.rowcol(pi.transform, all_lons, all_lats)
all_rows = np.array(all_rows)
all_cols = np.array(all_cols)

tpts = tpts.copy()
tpts['_pixel_row'] = all_rows
tpts['_pixel_col'] = all_cols

# --------------- (d) extract pixel data ---------------
n_tpts = len(tpts) # number of training points
all_px_vals = np.full((n_tpts, n_bands), np.nan)

in_bounds = (
    (all_rows >= 0) & (all_rows < pi.height) &
    (all_cols >= 0) & (all_cols < pi.width)
)

if in_bounds.any():
    all_px_vals[in_bounds, :] = all_bands[:, all_rows[in_bounds], all_cols[in_bounds]].T
    
# --------------- (e) remove erroneous points ---------------
all_zero_mask = np.all(all_px_vals == 0, axis=1)
n_zero = int(all_zero_mask.sum())

if n_zero > 0:
    print(f"\n  Removing {n_zero} point(s) with all-zero band values across all bands...", end=" ")
    tpts = tpts[~all_zero_mask].reset_index(drop=True)
    all_px_vals = all_px_vals[~all_zero_mask]
   
# --------------- (f) class summaries ---------------
classes = np.unique(tpts[CLASS_COLUMN])
n_classes = len(classes)
min_class_count = int(tpts[CLASS_COLUMN].value_counts().min())

n_per_class_cal = int(np.floor(min_class_count*(CAL_PER/100)))
n_per_class_val = int(np.floor(min_class_count*(1-CAL_PER/100)))

if n_per_class_val < 1: # ensure there is at least one validation point
    n_per_class_val = 1
    n_per_class_cal = min_class_count-1

print(f"\n  {n_classes} classes detected — smallest class has {min_class_count} points.")
print(f"  Sampling {n_per_class_cal} cal / {n_per_class_val} val points per class.")
   
print("done.\nSuccess! Image bands prepared and pixel values extracted.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (4) MONTE CARLO SAMPLING
s = time.time()
print(f"\nRunning {N_MC} Monte Carlo iterations...")

# --------------- (a) prebuild numpy structures ---------------
tpts_class_arr = tpts[CLASS_COLUMN].values.astype(np.int32) # class label per point
tpts_row_arr = tpts['_pixel_row'].values.astype(np.int32) # pixel row per point
tpts_col_arr = tpts['_pixel_col'].values.astype(np.int32) # pixel col per point
tpts_idx_arr = np.arange(len(tpts), dtype=np.int32) # positional index per point
tpts_lon_arr = tpts['Longitude'].values.astype(np.float64) # longitude per point
tpts_lat_arr = tpts['Latitude'].values.astype(np.float64) # latitude per point

# prebuild array per class for efficiency
class_indices = {cls: np.where(tpts_class_arr == cls)[0] for cls in classes}

rc_keys = tpts_row_arr*(tpts_col_arr.max()+1)+tpts_col_arr # unique key per pixel
rc_sort_order = np.argsort(rc_keys)
rc_keys_sorted = rc_keys[rc_sort_order]

# --------------- (b) define balanced sampling function ---------------
def SampleClassN(class_idx_arr, n_samples, rng, exclude_mask=None):
    candidates = class_idx_arr
    
    if exclude_mask is not None:
        candidates = candidates[~exclude_mask[candidates]]
        
    n_samples = min(n_samples, len(candidates))
    chosen = rng.choice(candidates, size=n_samples, replace=False)
    return chosen

# --------------- (c) define pixel deduplication function ---------------
def DeduplicateByPixel(pos_idx): # for aggregating training data across pixels when multiple points are present
    if len(pos_idx) == 0:
        warnings.warn("Oops! There's nothing here, returning empty arrays.")
        return pos_idx, np.array([], dtype=np.int32)
    
    rows = tpts_row_arr[pos_idx]
    cols = tpts_col_arr[pos_idx]
    labels = tpts_class_arr[pos_idx]
 
    # encode each pixel
    key = rows*(cols.max()+1)+cols
    _, first_occurrence, inverse = np.unique(key, return_index=True, return_inverse=True)
 
    # majority class per pixel
    n_pixels = len(first_occurrence)
    n_classes_local = int(labels.max())+1
    vote_mat = np.zeros((n_pixels, n_classes_local), dtype=np.int32)
    np.add.at(vote_mat, (inverse, labels), 1)
    majority = vote_mat.argmax(axis=1).astype(np.int32)
 
    # return the first-occurrence positional index with corrected majority label
    dedup_pos = pos_idx[first_occurrence]
    dedup_labels = majority # overwrite labels after aggregation
 
    return dedup_pos, dedup_labels
    
# --------------- (d) build the row/col to pixel array lookup ---------------
# setup storage
mc_cal_features = []
mc_cal_labels = []
mc_val_features = []
mc_val_labels = []
mc_cal_lon = []
mc_cal_lat = []
mc_val_lon = []
mc_val_lat = []

for mc_iter in range(N_MC):
    rng = np.random.default_rng(seed=mc_iter) # seed for reproducibility
    
    # sample calibration points
    cal_pos_list = [SampleClassN(class_indices[cls], n_per_class_cal, rng) for cls in classes]
    cal_pos = np.concatenate(cal_pos_list)
    
    # build exclusion mask for validation point sampling
    exclude_mask = np.zeros(len(tpts), dtype=bool)
    exclude_mask[cal_pos] = True
    
    # sample validation points
    val_pos_list = [SampleClassN(class_indices[cls], n_per_class_val, rng, exclude_mask=exclude_mask) for cls in classes]
    val_pos = np.concatenate(val_pos_list)
    
    # assign majority class for repeated points per pixel
    cal_dedup_pos, cal_dedup_labels = DeduplicateByPixel(cal_pos)
    val_dedup_pos, val_dedup_labels = DeduplicateByPixel(val_pos)
    
    # look up coordinates for the deduplicated points
    cal_lon, cal_lat = tpts_lon_arr[cal_dedup_pos], tpts_lat_arr[cal_dedup_pos]
    val_lon, val_lat = tpts_lon_arr[val_dedup_pos], tpts_lat_arr[val_dedup_pos]
    
    # lookup pixel values
    cal_px = all_px_vals[cal_dedup_pos, :]
    val_px = all_px_vals[val_dedup_pos, :]
    
    # drop NaN rows
    cal_valid = ~np.isnan(cal_px).any(axis=1)
    val_valid = ~np.isnan(val_px).any(axis=1)
    cal_px, cal_dedup_labels, cal_lon, cal_lat = (
        cal_px[cal_valid], cal_dedup_labels[cal_valid], cal_lon[cal_valid], cal_lat[cal_valid])
    val_px, val_dedup_labels, val_lon, val_lat = (
        val_px[val_valid], val_dedup_labels[val_valid], val_lon[val_valid], val_lat[val_valid])
    
    # accumulate in memory
    mc_cal_features.append(cal_px.astype(np.float32))
    mc_cal_labels.append(cal_dedup_labels.astype(np.int32))
    mc_val_features.append(val_px.astype(np.float32))
    mc_val_labels.append(val_dedup_labels.astype(np.int32))
    mc_cal_lon.append(cal_lon.astype(np.float64))
    mc_cal_lat.append(cal_lat.astype(np.float64))
    mc_val_lon.append(val_lon.astype(np.float64))
    mc_val_lat.append(val_lat.astype(np.float64))
    
    # plot cal/val class distribution for iteration 0 only
    if mc_iter == 0:
        cal_counts = np.array([int((cal_dedup_labels == cls).sum()) for cls in classes])
        val_counts = np.array([int((val_dedup_labels == cls).sum()) for cls in classes])
 
        df_plot = pd.DataFrame(
            {'Calibration Points': cal_counts, 'Validation Points': val_counts},
            index=classes
        )
 
        ax = df_plot.plot(kind='bar', stacked=True, figsize=(10, 6), color=['#bababa', '#f4a582'])
        ax.set_xlabel('Class', fontsize=16)
        ax.set_ylabel('Count', fontsize=16)
        ax.tick_params(axis='both', labelsize=14)
 
        for container in ax.containers:
            labels = [str(int(v.get_height())) if v.get_height() > 50 else '' for v in container]
            ax.bar_label(container, labels=labels, label_type='center', fontsize=9)
 
        totals = df_plot.sum(axis=1)
        for i, (idx, total) in enumerate(totals.items()):
            ax.text(i, total, str(total), ha='center', va='bottom', fontsize=10, fontweight='bold')
 
        ax.set_title('Cal/Val class distribution (MC iteration 0)', fontsize=14)
        ax.legend(fontsize=14, loc='upper left', frameon=True)
        plt.tight_layout()
        plt.show()
    
    # progress reporting every 10 iterations
    if (mc_iter+1) % 10 == 0:
        print(f"  Iteration {mc_iter + 1}/{N_MC} complete ({time.time()-s:.1f}s elapsed).")

# --------------- (e) write all MC results to zarr in a single open/close ---------------
print("\nStacking MC results...", end=" ")
 
n_bands_out = mc_cal_features[0].shape[1]
max_cal_pts = max(a.shape[0] for a in mc_cal_features)
max_val_pts = max(a.shape[0] for a in mc_val_features)
  
cal_feat_arr = np.zeros((N_MC, max_cal_pts, n_bands_out), dtype=np.float32)
cal_lbl_arr = np.full((N_MC, max_cal_pts), -1, dtype=np.int32)
cal_cnt_arr = np.zeros(N_MC, dtype=np.int32)
  
val_feat_arr = np.zeros((N_MC, max_val_pts, n_bands_out), dtype=np.float32)
val_lbl_arr = np.full((N_MC, max_val_pts), -1, dtype=np.int32)
val_cnt_arr = np.zeros(N_MC, dtype=np.int32)

cal_lon_arr = np.full((N_MC, max_cal_pts), np.nan, dtype=np.float64)
cal_lat_arr = np.full((N_MC, max_cal_pts), np.nan, dtype=np.float64)
val_lon_arr = np.full((N_MC, max_val_pts), np.nan, dtype=np.float64)
val_lat_arr = np.full((N_MC, max_val_pts), np.nan, dtype=np.float64)
  
for i in range(N_MC):
    nc = mc_cal_features[i].shape[0]
    nv = mc_val_features[i].shape[0]
    cal_feat_arr[i, :nc, :] = mc_cal_features[i]
    cal_lbl_arr[i, :nc] = mc_cal_labels[i]
    cal_cnt_arr[i] = nc
    val_feat_arr[i, :nv, :] = mc_val_features[i]
    val_lbl_arr[i, :nv] = mc_val_labels[i]
    val_cnt_arr[i] = nv
    
    cal_lon_arr[i, :nc] = mc_cal_lon[i]
    cal_lat_arr[i, :nc] = mc_cal_lat[i]
    val_lon_arr[i, :nv] = mc_val_lon[i]
    val_lat_arr[i, :nv] = mc_val_lat[i]
  
print("done.\nWriting zarr store...", end=" ")
 
# chunk along the iteration axis in blocks of 50
chunk_iters = min(50, N_MC)
_store = zarr.open(mc_zarr_output, mode='w')
_store.attrs['band_names'] = band_names_filtered
_store.attrs['class_column'] = CLASS_COLUMN
_store.attrs['n_mc_iterations'] = N_MC
_store.attrs['cal_per'] = CAL_PER
_store.attrs['max_cal_pts'] = int(max_cal_pts)
_store.attrs['max_val_pts'] = int(max_val_pts)
  
_store['cal_features'] = cal_feat_arr # single write, one chunk file per 50 iters
_store['cal_labels'] = cal_lbl_arr
_store['cal_counts'] = cal_cnt_arr
_store['cal_lon'] = cal_lon_arr
_store['cal_lat'] = cal_lat_arr
_store['val_features'] = val_feat_arr
_store['val_labels'] = val_lbl_arr
_store['val_counts'] = val_cnt_arr
_store['val_lon'] = val_lon_arr
_store['val_lat'] = val_lat_arr
  
if hasattr(_store, 'store') and hasattr(_store.store, 'close'):
    _store.store.close()
del _store, cal_feat_arr, cal_lbl_arr, val_feat_arr, val_lbl_arr, cal_lon_arr, cal_lat_arr, val_lon_arr, val_lat_arr
 
# --------------- (f) export tpts summary CSV ---------------
tpts = tpts.drop(columns=['_pixel_row', '_pixel_col'])
tpts.to_csv(tpts_output, index=False)
 
print(f"\ndone.\nSuccess! {N_MC} Monte Carlo training datasets written.")
print("Training point summary exported.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))