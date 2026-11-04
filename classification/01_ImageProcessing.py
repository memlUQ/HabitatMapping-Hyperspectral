#Dylan Cowley: 26/03/2026
#Python version 3.10 or greater required
#Package requirements:
#    - geopandas, rasterio, matplotlib, scikit-learn, scikit-image, scipy, numpy, os, time

# %% (0) IMPORT PACKAGES
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from skimage.feature import graycomatrix, graycoprops
from skimage.segmentation import slic
from scipy.ndimage import convolve, maximum_filter, median_filter
import numpy as np
import sys
import os
import time

# read variables from configuration files
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))) # add folder for this script to path
from params import YEAR_MONTH, SITE_NAME, SITE_FLDR, SITE_ID, SENSOR # site + sensor details
from params import TARGET_CRS # coordinate reference system
from params import ROOT # file/folder details
from params import DEPTH_MAX # depth extent

# %% (1) USER INPUT
print("Defining user input...", end=" ")
s = time.time()

# to manually define the number of segments in the segmentation step, edit the n_segments variable on line 507

# --------------- (a) define band specifics ---------------
if SENSOR == 'Planet':
    R_VIS = 6 # assign RED band (for visualisation)
    G_VIS = 4 # assign GREEN band (for visualisation)
    B_VIS = 2 # assign BLUE band (for visualisation)
    
    R = np.array([6]) # select RED bands for statistics
    G = np.array([4]) # select GREEN bands for statistics
    B = np.array([2]) # select BLUE bands for statistics
    
    RMV_BANDS = [] # bands to remove
elif SENSOR == 'PRISMA':
    R_VIS = 36 # assign RED band (for visualisation)
    G_VIS = 48 # assign GREEN band (for visualisation)
    B_VIS = 60 # assign BLUE band (for visualisation)
    
    R = np.arange(26,37) # select RED bands for statistics
    G = np.arange(42,53) # select GREEN bands for statistics
    B = np.arange(54,65) # select BLUE bands for statistics
    
    RMV_BANDS = ['b1','b2','b66'] # bands to remove

# --------------- (b) define physical attributes ---------------
PHYSICAL_LAYER = SITE_ID+'_d' # FILE for depth, slope, and wave information [TIFF]
DW_BANDS = ['b1']#, 'b2', 'b3'] # define which bands to use: in the order [depth, waves, slope] -- depth MUST be used
DW_BAND_NAMES = ['depth']#, 'slope', 'waves'] # define band names for physical layer

# --------------- (c) setup asset directories and define file names ---------------
pwd = os.path.join(ROOT, SITE_FLDR, 'Mapping_Joanna')

# inputs
roi_geometry = SITE_NAME+'_Shpfl.shp' # FILE for region of interest [SHAPEFILE]
phys_fldr = os.path.join(pwd, '02_physical_layers') # FOLDER for physical layers
physical_layer_path = os.path.join(phys_fldr, PHYSICAL_LAYER+".tif") # FILE for physical layers [TIF]
roi_file = os.path.join(phys_fldr, roi_geometry) # FILE geometry for mapping region of interest
raw_image = os.path.join(pwd, '03_raw_imagery', YEAR_MONTH, SITE_NAME+'_'+SENSOR+'_'+YEAR_MONTH) # FOLDER for unprocessed satellite imagery

# output
output_file_name = os.path.join(pwd, '04_processed_imagery', YEAR_MONTH, SITE_ID+'_'+SENSOR+'_'+YEAR_MONTH+'_processed.tif')

print("done.\nSuccess! User input defined.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (2) BASIC DISPLAY
s = time.time()
print("\nDefining ROI...", end=" ")

# --------------- (a) define region of interest ---------------
roi_gdf = gpd.read_file(roi_file)

print("done.\nMasking image based on ROI...", end=" ")

# --------------- (b) create extent mask as raster ---------------
ext = '.tif'
with rasterio.open(raw_image+ext) as src: 
    roi_gdf = roi_gdf.to_crs(src.crs) # ensure ROI CRS is correct
    shapes = [geom for geom in roi_gdf.geometry] # extract geometry
    clipped_image, clipped_transform = mask(src, shapes, crop=True) # clip image to ROI
    clipped_meta = src.meta.copy()
    
    # update metadata
    clipped_meta.update({
        'height': clipped_image.shape[1],
        'width': clipped_image.shape[2],
        'transform': clipped_transform
    })
    
    # reproject the clipped image to the defined CRS
    transform_crs, width_crs, height_crs = calculate_default_transform(
        src.crs, TARGET_CRS, clipped_image.shape[2], clipped_image.shape[1], 
        *rasterio.transform.array_bounds(clipped_image.shape[1], clipped_image.shape[2], clipped_transform)
    )
    
    # create output array
    reprojected_image = np.zeros((clipped_image.shape[0], height_crs, width_crs), dtype=clipped_image.dtype)
    
    # reproject each band
    for i in range(clipped_image.shape[0]):
        reproject(
            source = clipped_image[i],
            destination = reprojected_image[i],
            src_transform = clipped_transform,
            src_crs = src.crs,
            dst_transform = transform_crs,
            dst_crs = TARGET_CRS,
            resampling = Resampling.bilinear
        )
    
    # update metadata for reprojected image
    reprojected_meta = clipped_meta.copy()
    reprojected_meta.update({
        'crs': TARGET_CRS,
        'transform': transform_crs,
        'width': width_crs,
        'height': height_crs
    })
    
    # update variables to use reprojected data
    clipped_image = reprojected_image
    clipped_transform = transform_crs
    clipped_meta = reprojected_meta

roi_gdf = roi_gdf.to_crs(TARGET_CRS) # reproject ROI to target CRS for plotting

print("done.\nDisplaying true colour image...", end=" ")

# --------------- (c) display true colour image ---------------
fig, ax = plt.subplots(1, 1, figsize=(12, 8))

red_vis = clipped_image[R_VIS] # clipped image RED band
green_vis = clipped_image[G_VIS] # clipped image GREEN band
blue_vis = clipped_image[B_VIS] # clipped image BLUE band
rgb = np.dstack((red_vis, green_vis, blue_vis)) # stack bands for RGB display

# normalise to 0-1 range for display (min-max feature scaling)
rgb_normalised = np.zeros_like(rgb, dtype=np.float32)
for i in range(3):
    band = rgb[:, :, i].astype(np.float32)
    band_min, band_max = np.percentile(band[band>0], [5, 98]) # 5-98 percentile stretch
    rgb_normalised[:, :, i] = np.clip((band-band_min)/(band_max-band_min), 0, 1)
    
# display the image
ax.imshow(rgb_normalised, extent=[
    clipped_transform[2],
    clipped_transform[2]+clipped_transform[0]*clipped_meta['width'],
    clipped_transform[5]+clipped_transform[4]*clipped_meta['height'],
    clipped_transform[5]
])

# overlay ROI boundary
roi_gdf.boundary.plot(ax=ax, color='yellow', linewidth=2, label='ROI Boundary')
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

print("done.\nSuccess! True colour image displayed.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (3) IMAGE STATISTICS
s = time.time()
print("\nSelecting bands...", end=" ")

# --------------- (a) select bands for statistics ---------------
if SENSOR == 'Planet':
    rgb_bands = clipped_image[[R-1,G-1,B-1], :, :] # for indexing differences in Planet imagery
else: 
    rgb_bands = clipped_image[[R,G,B], :, :]

print("done.\nComputing basic statistics (mean, median, standard deviation)...", end=" ")

# --------------- (b) add basic statistics ---------------
valid_mask = rgb_bands>0

statistics = {}
statistics['mean'] = np.mean(clipped_image, axis=0) # compute mean
statistics['median'] = np.median(clipped_image, axis=0) # compute median
statistics['stdDev'] = np.std(clipped_image, axis=0) # compute standard deviation

print("done.\nAdding statistical bands to the image...", end=" ")

# --------------- (c) add statistics as bands to the image ---------------
red_band = clipped_image[R] # clipped image RED bands
green_band = clipped_image[G] # clipped image GREEN bands
blue_band = clipped_image[B] # clipped image BLUE bands

def compute_ratio(numerator, denominator, name_prefix, num_name, den_name):
    results = []
    for i, num in enumerate(numerator):
        name1 = num_name[i]
            
        for j, den in enumerate(denominator):
            name2 = den_name[j]
                
            ratio = np.zeros_like(num, dtype=np.int16)
            valid = den > 0
            ratio[valid] = np.clip(
                (num[valid].astype(np.float32)/den[valid].astype(np.float32))*1000,
                -32768, 32767
            ).astype(np.int16)
            results.append((ratio, f'{name_prefix}_b{name1}_{name2}'))
    return results

# compute all pairwise ratios: R/B, G/B, R/G
ratio_pairs = [
    (red_band, blue_band, 'rb', R, B),
    (green_band, blue_band, 'gb', G, B),
    (red_band, green_band, 'rg', R, G),
]

ratio_bands = []
ratio_names = []
for num, den, prefix, num_name, den_name in ratio_pairs:
    for arr, name in compute_ratio(num, den, prefix, num_name, den_name):
        ratio_bands.append(arr)
        ratio_names.append(name)

# create image with statistics
stat_bands = []
stat_names = []

for stat_name, stat_value in statistics.items():
    stat_bands.append(stat_value.astype(np.float32))
    stat_names.append(stat_name)
    
# stack all bands together (original + stats + ratios)
all_bands = [clipped_image[i] for i in range(clipped_image.shape[0])]
all_bands.extend(stat_bands)
all_bands.extend(ratio_bands)

original_band_names = [f'b{i+1}' for i in range(clipped_image.shape[0])]
all_band_names = original_band_names+stat_names+ratio_names

# stack into single array
image_with_stats = np.stack(all_bands, axis=0)

print("done.\nSuccess! Basic statistical bands added to image stack.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (4) PRINCIPAL COMPONENTS ANALYSIS
s = time.time()
print("\nSetting up bands for PCA...", end=" ")

# --------------- (a) setup for PCA ---------------
PCA_bands = np.concatenate([R, G, B]) # select bands to perform PCA on

pca_data = clipped_image[PCA_bands, :, :]
#pca_data = pca_data.squeeze(axis=0)
n_bands, height, width = pca_data.shape
pca_reshaped = pca_data.reshape(n_bands, -1).T # reshape for matrix calculations
valid_pixels = np.all(pca_reshaped>0, axis=1) # create mask for valid pixels (non-zero in all bands)

print("done.\nConducting PCA...", end=" ")

# --------------- (b) conduct PCA ---------------
pca = PCA(n_components=3)
pca_transformed = np.zeros((pca_reshaped.shape[0], 3))

# fit PCA on valid pixels
pca_transformed[valid_pixels] = pca.fit_transform(pca_reshaped[valid_pixels])

# reshape back to image dimensions
pc1 = pca_transformed[:, 0].reshape(height, width)
pc2 = pca_transformed[:, 1].reshape(height, width)
pc3 = pca_transformed[:, 2].reshape(height, width)

# stack principal components
pc_image = np.stack([pc1, pc2, pc3], axis=0)
pc_names = ['pc1', 'pc2', 'pc3']

print("done.\nVisualising PCA results...", end=" ")

# --------------- (c) visualise PCA ---------------
fig, ax = plt.subplots(1, 1, figsize=(16, 12))

# composite of PC1, PC2, PC3
pc_rgb = np.zeros((height, width, 3))
for i in range(3):
    band = pc_image[i]
    if np.any(band != 0):
        band_min, band_max = np.percentile(band[band != 0], [2, 98])
        pc_rgb[:, :, i] = np.clip((band-band_min)/(band_max-band_min), 0, 1)

ax.imshow(pc_rgb, extent=[
    clipped_transform[2],
    clipped_transform[2]+clipped_transform[0]*clipped_meta['width'],
    clipped_transform[5]+clipped_transform[4]*clipped_meta['height'],
    clipped_transform[5]
])
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
roi_gdf.boundary.plot(ax=ax, color='yellow', linewidth=1.5, alpha=0.7)

plt.tight_layout()
plt.show()

# add PC bands to the full image stack
all_bands.extend([pc1, pc2, pc3])
all_band_names.extend(pc_names)

# update stacked image array
image_with_stats = np.stack(all_bands, axis=0)

print("done.\nSuccess! PCA results added to image stack.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (5) DEPTH MASKING
s = time.time()

print("\nExtracting physical layers from file...", end=" ")

# --------------- (a) extract physical layers (depth, slope, waves) ---------------
with rasterio.open(physical_layer_path) as dw_src:
    roi_gdf_dw = roi_gdf.to_crs(dw_src.crs) # ensure CRS is correct
    shapes_dw = [geom for geom in roi_gdf_dw.geometry] # ROI geometry
    dw_clipped, dw_transform = mask(dw_src, shapes_dw, crop=True) # clip physical layer to ROI
    
    # select and rename bands based on dwBands variable
    band_indices = {'b1': 0, 'b2': 1, 'b3': 2}
    selected_bands = [band_indices[band] for band in DW_BANDS]
    
    dw_image = dw_clipped[selected_bands, :, :]
    
    # reproject to match clipped_image
    dw_reprojected = np.zeros((len(selected_bands), height_crs, width_crs), dtype=np.int16)
    
    for i in range(len(selected_bands)):
        reproject(
            source = dw_image[i],
            destination = dw_reprojected[i],
            src_transform = dw_transform,
            src_crs = dw_src.crs,
            dst_transform = transform_crs,
            dst_crs = TARGET_CRS,
            resampling = Resampling.bilinear
        )
    
    dw_image = dw_reprojected.astype(np.int16)

# create depth mask
depth_mask = dw_image[0] # first band is depth
depth_mask_bool = (depth_mask > 0) & (depth_mask <= DEPTH_MAX)
depth_mask = np.where(depth_mask_bool, depth_mask, 0)

print("done.\nCreating GLCMs...", end=" ")

# --------------- (b) GLCM (grey level co-occurrence matrix) texture bands ---------------
print("\n  Depth GLCM...", end=" ")
# depth GLCM
depth_glcm = np.zeros_like(depth_mask, dtype=np.int16)
valid_depth = depth_mask != 0
if np.any(valid_depth):
    # normalise depth image to 0-255 range for GLCM
    img_normalised = np.zeros_like(depth_mask, dtype=np.uint8)
    img_min = float(np.min(depth_mask[valid_depth]))
    img_max = float(np.max(depth_mask[valid_depth]))
    if img_max > img_min:
        depth_float = depth_mask[valid_depth].astype(np.float32)
        img_normalised[valid_depth] = ((depth_float-img_min)/(img_max-img_min)*255).astype(np.uint8)
    
    # calculate GLCM
    glcm = graycomatrix(img_normalised, distances=[1], angles=[0], 
                        levels=256, symmetric=True, normed=True)
    
    # calculate entropy manually from GLCM
    glcm_matrix = glcm[:, :, 0, 0]
    glcm_matrix = glcm_matrix+1e-10 # to avoid log(0)
    entropy = -np.sum(glcm_matrix*np.log2(glcm_matrix))
    
    # apply focal maximum
    depth_entropy = maximum_filter(np.full_like(depth_mask, entropy, dtype=np.float32), size=5)
    depth_glcm = (depth_entropy*100).astype(np.int16)
    depth_glcm[~valid_depth] = 0

print("done.\n  Blue band GLCM...", end=" ")

# blue band GLCM sum average with focal median
blue_band_data = clipped_image[B].mean(axis=0).astype(np.float32)
blue_glcm = np.zeros_like(blue_band_data, dtype=np.int16)
valid_blue = blue_band_data>0
if np.any(valid_blue):
    blue_normalised = np.zeros_like(blue_band_data, dtype=np.uint8)
    blue_float = blue_band_data[valid_blue].astype(np.float32)
    blue_min = blue_float.min()
    blue_max = blue_float.max()
    blue_normalised[valid_blue] = ((blue_float-blue_min)/(blue_max-blue_min)*255).astype(np.uint8)
    glcm_blue = graycomatrix(blue_normalised, distances=[1], angles=[0],
                             levels=256, symmetric=True, normed=True)
    
    savg = graycoprops(glcm_blue, 'ASM').mean() # use ASM as proxy for average
    blue_texture = median_filter(np.full_like(blue_band_data, savg*1000, dtype=np.float32), size=5)
    blue_glcm = blue_texture.astype(np.int16)
    blue_glcm[~valid_blue] = 0

print("done.\n  Green band GLCM...", end=" ")

# green band GLCM sum average with focal median
green_band_data = clipped_image[G].mean(axis=0).astype(np.float32)
green_glcm = np.zeros_like(green_band_data, dtype=np.int16)
valid_green = green_band_data>0
if np.any(valid_green):
    green_normalised = np.zeros_like(green_band_data, dtype=np.uint8)
    green_float = green_band_data[valid_green].astype(np.float32)
    green_min = green_float.min()
    green_max = green_float.max()
    green_normalised[valid_green] = ((green_float-green_min)/(green_max-green_min)*255).astype(np.uint8)
    glcm_green = graycomatrix(green_normalised, distances=[1], angles=[0],
                              levels=256, symmetric=True, normed=True)
    
    savg = graycoprops(glcm_green, 'ASM').mean()
    green_texture = median_filter(np.full_like(green_band_data, savg*1000, dtype=np.float32), size=5)
    green_glcm = green_texture.astype(np.int16)
    green_glcm[~valid_green] = 0

print("done.\nComputing additional statistics (depth and red band standard deviation)...", end=" ")

# --------------- (c) additional statistics ---------------
# depth standard deviation
depth_var = np.zeros_like(depth_mask, dtype=np.int16)
valid_depth = depth_mask != 0
if np.any(valid_depth):
    depth_f = depth_mask.astype(np.float32)
    kernel = np.ones((3, 3), dtype=np.float32)/9
    
    mean = convolve(depth_f, kernel, mode='constant')
    mean_sq = convolve(depth_f**2, kernel, mode='constant')
    depth_std = np.sqrt(np.maximum(mean_sq-mean**2, 0))
    depth_var = (depth_std*10).astype(np.int16)
    depth_var[~valid_depth] = 0

# red band standard deviation
red_band_data = clipped_image[R].mean(axis=0).astype(np.float32)
red_var = np.zeros_like(red_band_data, dtype=np.int16)
valid_red = red_band_data>0
if np.any(valid_red):
    red_f = red_band_data.astype(np.float32)
    kernel = np.ones((3, 3), dtype=np.float32)/9
    
    mean = convolve(red_f, kernel, mode='constant')
    mean_sq = convolve(red_f**2, kernel, mode='constant')
    red_std = np.sqrt(np.maximum(mean_sq-mean**2, 0))
    red_var = (red_std*10).astype(np.int16)
    red_var[~valid_red] = 0

# add all new bands to the stack
texture_names = ['depth_maxent', f'b{B[0]}-{B[-1]}_savg', f'b{G[0]}-{G[-1]}_savg', 'depth_stdDev', 'red_stdDev']
all_bands.extend([depth_glcm, blue_glcm, green_glcm, depth_var, red_var])
all_band_names.extend(texture_names)

# add physical layer bands
for i, band_name in enumerate(DW_BAND_NAMES):
    all_bands.append(dw_image[i])
    all_band_names.append(band_name)

# update final stacked image
image_with_stats = np.stack(all_bands, axis=0)

print("done.\nSuccess! GLCMs and statistical bands added to image stack.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (6) SEGMENTATION
s = time.time()

print("\nPreparing image stack for segmentation...", end=" ")

# --------------- (a) prepare bands for segmentation --------------- 
segmentation_bands = image_with_stats.copy()

# apply depth mask
depth_mask_bool = depth_mask != 0
for i in range(segmentation_bands.shape[0]):
    segmentation_bands[i][~depth_mask_bool] = 0

print("done.\nNormalising bands...", end=" ")

# --------------- (b) normalise image data for segmentation ---------------
image_normalised = segmentation_bands.copy().astype(np.float32)
for i in range(segmentation_bands.shape[0]):
    band = segmentation_bands[i].astype(np.float32)
    valid_band = band[depth_mask_bool]
    if len(valid_band) > 0 and np.any(valid_band != 0):
        band_min = np.min(valid_band)
        band_max = np.max(valid_band)
        if band_max > band_min:
            image_normalised[i][depth_mask_bool] = (band[depth_mask_bool]-band_min)/(band_max-band_min)

# transpose for SLIC: (bands, height, width) to (height, width, bands)
image_for_slic = np.transpose(image_normalised, (1, 2, 0))

print("done.\nRunning SLIC segmentation...", end=" ")

# --------------- (c) run SLIC segmentation ---------------
valid_pixel_count = np.sum(depth_mask_bool)
n_segments = int(np.floor(0.6*valid_pixel_count)) # number of segments across the image, varied by number of pixels

segments = slic(
    image_for_slic,
    n_segments = n_segments,
    compactness = 4,
    max_num_iter = 10,
    start_label = 0,
    channel_axis = 2,
    mask = depth_mask_bool
)

print("done.\nCalculating segment means...", end=" ")

# --------------- (d) calculate mean values for each segment ---------------
segmented_data_mean = np.zeros_like(image_with_stats, dtype=np.float32)

# prepare segment data
segments_flat = segments.ravel()
valid_mask = segments_flat != -1
segments_valid = segments_flat[valid_mask]

# get unique segments
unique_segments = np.unique(segments_valid)
n_segments = len(unique_segments)

# create mapping from segment ID to index for faster lookup
max_segment_id = segments_valid.max()
segment_to_idx = np.full(max_segment_id + 1, -1, dtype=np.int32)
segment_to_idx[unique_segments] = np.arange(n_segments)

# process all bands
for band_idx in range(image_with_stats.shape[0]):
    band_data = image_with_stats[band_idx].astype(np.float32)
    band_flat = band_data.ravel()[valid_mask]
    
    # separate zero and non-zero values
    nonzero_mask = band_flat != 0
    
    if np.any(nonzero_mask):
        # get segments and values for non-zero pixels only
        segments_nonzero = segments_valid[nonzero_mask]
        values_nonzero = band_flat[nonzero_mask]
        
        # calculate sum and count for each segment
        segment_sums = np.bincount(segments_nonzero, weights=values_nonzero, minlength=max_segment_id+1)
        segment_counts = np.bincount(segments_nonzero, minlength=max_segment_id+1)
        
        # calculate means
        segment_means = np.zeros(max_segment_id+1, dtype=np.float32)
        valid_segments = segment_counts>0
        segment_means[valid_segments] = segment_sums[valid_segments] / segment_counts[valid_segments]
        
        # map segment means back to all pixels
        result = np.zeros_like(segments_flat, dtype=np.float32)
        result[valid_mask] = segment_means[segments_valid]
        segmented_data_mean[band_idx] = result.reshape(band_data.shape)

print("done.\nSuccess! Segmentation completed, processed image ready for export.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (7) EXPORT PROCESSED IMAGE
print("\nExporting image...", end=" ")
s = time.time()

# --------------- (a) remove unwanted bands ---------------
if len(RMV_BANDS) > 0:
    rmv_indices = [all_band_names.index(b) for b in RMV_BANDS if b in all_band_names]
    segmented_data_mean = np.delete(segmented_data_mean, rmv_indices, axis=0)
    all_band_names = [b for b in all_band_names if b not in RMV_BANDS]

# --------------- (b) write processed image as raster ---------------
with rasterio.open(
    output_file_name,
    'w',
    driver = 'GTiff',
    height = segmented_data_mean.shape[1],
    width = segmented_data_mean.shape[2],
    count = segmented_data_mean.shape[0], # number of bands
    dtype = segmented_data_mean.dtype,
    crs = TARGET_CRS,
    transform = clipped_transform,
) as dst:
    # write band descriptions
    for i, band_name in enumerate(all_band_names, start=1):
        dst.set_band_description(i, band_name)
    dst.write(segmented_data_mean)
    
print("done.\nSuccess! Processed image exported.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))