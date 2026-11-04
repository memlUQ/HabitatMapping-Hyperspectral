#David Carrasco Rivera + Dylan Cowley: 09/09/2026
#Python version 3.12
#Packages requirements: 
#   - numpy, pandas, rasterio, geopandas, tensorflow, scikit-learn, time, os, sys

# %% (0) IMPORT PACKAGES
# general packages
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from sklearn.metrics import confusion_matrix, accuracy_score
import zarr
import time
import os 
import sys

# read variables from configuration files
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))) # add folder for this script to path
from params import YEAR_MONTH, SITE_NAME, SITE_FLDR, SITE_ID, SENSOR # site + sensor details
from params import DEPTH_MAX # physical parameters
from params import TARGET_CRS # coordinate reference system
from params import ROOT # file/folder details

# %% (1) USER INPUT
s = time.time()
print("Defining user input...", end=" ")

# --------------- (a) define classification model ---------------
# options: 
#   - 'RF'  (random forest)
#   - 'KNN' (k-nearest neighbours)
#   - 'MLC' (maximum likelihood classifier)
#   - 'SVM' (support vector machine)
METHOD = 'RF' # switching variable for classification method

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

# --------------- (e) setup asset directories and define file names ---------------
pwd = os.path.join(ROOT, SITE_FLDR, 'Mapping')

# inputs
roi_geometry = SITE_NAME+'_Shpfl.shp' # FILE for region of interest [SHAPEFILE]
phys_fldr = os.path.join(pwd, '02_physical_layers') # FOLDER for physical layers
roi_file = os.path.join(phys_fldr, roi_geometry) # FILE geometry for mapping region of interest
raw_image = os.path.join(pwd, '03_raw_imagery', YEAR_MONTH, SITE_NAME+'_'+SENSOR+'_'+YEAR_MONTH) # FOLDER for unprocessed satellite imagery
processed_image = os.path.join(pwd, '04_processed_imagery', YEAR_MONTH, SITE_ID+'_'+SENSOR+'_'+YEAR_MONTH+'_processed.tif') # FILE for processed satellite imagery
mc_zarr_input = os.path.join(pwd, '05_training_data', YEAR_MONTH, SITE_ID+'_'+SENSOR+'_'+YEAR_MONTH+'_mc_training.zarr') # FILE for Monte Carlo training data

# outputs
classification_output = os.path.join(pwd, '06_classified_imagery', YEAR_MONTH, METHOD, SITE_ID+'_'+SENSOR+'_'+YEAR_MONTH+'_classified.tif')
accuracy_output = os.path.join(pwd, '07_accuracy', YEAR_MONTH, METHOD, SITE_ID+'_'+SENSOR+'_accuracy_'+YEAR_MONTH+'.csv')
mc_class_probability_output = os.path.join(pwd, '07_accuracy', YEAR_MONTH, METHOD, SITE_ID+'_'+SENSOR+'_MC_class_probability_'+YEAR_MONTH+'.tif')

# extra outputs
probability_output = os.path.join(pwd, '07_accuracy', YEAR_MONTH, METHOD, SITE_ID+'_'+SENSOR+'_probability_'+YEAR_MONTH+'.tif')
history_output = os.path.join(pwd, '07_accuracy', YEAR_MONTH, METHOD, SITE_ID+'_'+SENSOR+'_training_history_'+YEAR_MONTH+'.csv')
confidence_output = os.path.join(pwd, '07_accuracy', YEAR_MONTH, METHOD, SITE_ID+'_'+SENSOR+'_confidence_'+YEAR_MONTH+'.tif')

# create output directory if it doesn't exist
os.makedirs(os.path.join(pwd, '06_classified_imagery', YEAR_MONTH, METHOD), exist_ok=True)
os.makedirs(os.path.join(pwd, '07_accuracy', YEAR_MONTH, METHOD), exist_ok=True)

print("done.\nSuccess! User input defined.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (2) LOAD IMAGE ASSETS
s = time.time()
print("\nLoading image data...", end=" ")

# --------------- (a) load mapping extent ---------------
roi_gdf = gpd.read_file(roi_file)
roi_gdf = roi_gdf.to_crs(TARGET_CRS)
roi_geom = [geom.__geo_interface__ for geom in roi_gdf.geometry] # convert to GeoJSON format

# --------------- (b) load processed image ---------------
with rasterio.open(processed_image) as src:
    clipped_img, clipped_transform = mask(src, roi_geom, crop=True)
    clipped_meta = src.meta.copy()
    
    clipped_meta.update({
        "height": clipped_img.shape[1],
        "width": clipped_img.shape[2],
        "transform": clipped_transform
    })
    
    n_bands = clipped_img.shape[0]
    all_band_names = list(src.descriptions)

depth_band_idx = all_band_names.index('depth')

# --------------- (b) define band names ---------------
band_names = [b for b in all_band_names if b not in RMV_BANDS]

# --------------- (d) apply depth mask ---------------
# valid pixels where depth band is non-zero
roi_mask = clipped_img[depth_band_idx] != 0

# combine with depth mask
depth_band = clipped_img[depth_band_idx]
depth_mask = (depth_band >= 0) & (depth_band <= DEPTH_MAX) & roi_mask

# --------------- (e) apply depth mask ---------------
img_reshaped = clipped_img.reshape(n_bands, -1).T # reshape so pixels are rows
depth_mask_flat = depth_mask.flatten() # true/false depth mask per pixel
img_masked = img_reshaped[depth_mask_flat] # all valid pixels

# subset to only the bands used for training
band_indices = [all_band_names.index(b) for b in band_names]
img_masked = img_masked[:, band_indices]

# --------------- (f) normalise image pixels to [0, 1] ---------------
# store min/max from training pixels to apply consistently during inference
feat_min = img_masked.min(axis=0)
feat_max = img_masked.max(axis=0)
feat_range = np.where((feat_max-feat_min) == 0, 1, feat_max-feat_min)
img_masked_norm = (img_masked-feat_min)/feat_range

print("done.\nSuccess! Image data loaded.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (3) LOAD TRAINING DATA
s = time.time()
print("\nLoading Monte Carlo training data into memory...", end=" ")

# --------------- (a) load training points ---------------
_store = zarr.open(mc_zarr_input, mode='r')
N_MC = _store.attrs['n_mc_iterations']
_cal_features = _store['cal_features'][:] # (N_MC, max_cal_pts, n_bands) float32
_cal_labels = _store['cal_labels'][:] # (N_MC, max_cal_pts) int32
_cal_counts = _store['cal_counts'][:] # (N_MC,) int32
_val_features = _store['val_features'][:] # (N_MC, max_val_pts, n_bands) float32
_val_labels = _store['val_labels'][:] # (N_MC, max_val_pts) int32
_val_counts = _store['val_counts'][:] # (N_MC,) int32
if hasattr(_store, 'store') and hasattr(_store.store, 'close'):
    _store.store.close()
del _store
 
print(f"done.\n  {N_MC} iterations loaded.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (4) DEFINE CLASSIFICATON PARAMETERS
s = time.time()
print("\nDefining classification parameters...", end=" ")

# --------------- (a) general paramaters ---------------
_sample_cal = _cal_features[0, :_cal_counts[0], :]
_sample_cls = _cal_labels[0, :_cal_counts[0]]

unique_classes = np.unique(_sample_cls)
n_classes = len(unique_classes)

n_features = _sample_cal.shape[1]

# --------------- (b) model specific paramaters ---------------
inputs = {} # for model paramaters
match METHOD:
    case 'RF': # select random forest classifier
        from params import RF_N_TREES, RF_MIN_SAMPLES_LEAF, RF_RANDOM_STATE
        import classRF as classifier
        inputs.update({'n_trees': RF_N_TREES, 'min_samples_leaf': RF_MIN_SAMPLES_LEAF, 
                       'random_state': RF_RANDOM_STATE, 'band_names': band_names,
                       'n_rows': clipped_img.shape[1], 'n_cols': clipped_img.shape[2]})
    case 'KNN': # select k-nearest neighbour classifier
        from params import KNN_N_NEIGHBOURS, KNN_WEIGHTS, KNN_METRIC, KNN_ALGORITHM
        import classKNN as classifier
        inputs.update({'n_neighbours': KNN_N_NEIGHBOURS, 'weights': KNN_WEIGHTS,
                       'metric': KNN_METRIC, 'algorithm': KNN_ALGORITHM,
                       'n_rows': clipped_img.shape[1], 'n_cols': clipped_img.shape[2]})
    case 'MLC': # select maximum likelihood classifier
        from params import MLC_STORE_COVARIANCE, MLC_SHRINKAGE, MLC_SOLVER
        import classMLC as classifier
        inputs.update({'store_covariance': MLC_STORE_COVARIANCE, 'solver_opt': MLC_SOLVER,
                       'n_rows': clipped_img.shape[1], 'n_cols': clipped_img.shape[2],
                       'shrinkage_opt': MLC_SHRINKAGE})
    case 'SVM':
        from params import SVM_KERNEL, SVM_C, SVM_GAMMA, SVM_PROBABILITY
        import classSVM as classifier
        inputs.update({'kernel': SVM_KERNEL, 'C': SVM_C,
                       'gamma': SVM_GAMMA, 'svm_probability': SVM_PROBABILITY,
                       'n_rows': clipped_img.shape[1], 'n_cols': clipped_img.shape[2]}) # pass the array, drop cal_data

print("done.\nSuccess! Classification parameters defined.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (5) MONTE CARLO CLASSIFICATION LOOP
s = time.time()
print(f"\nRunning {N_MC} Monte Carlo classifications ({METHOD})...", end=" ")

# --------------- (a) setup ---------------
mc_results = [] # list of dicts — one per iteration
 
best_oa = -1.0
best_mc_iter = -1
best_outputs = None
best_x_train_raw = None
best_y_train_raw = None
best_x_val = None
best_y_val = None

# per-pixel, per-class vote tally across all N_MC iterations.
n_rows_img = clipped_img.shape[1]
n_cols_img = clipped_img.shape[2]
class_vote_counts = np.zeros((n_classes, n_rows_img, n_cols_img), dtype=np.uint16)

# --------------- (b) run classifier ---------------
for mc_iter in range(N_MC):
 
    # slice pre-loaded arrays using counts
    nc = int(_cal_counts[mc_iter])
    nv = int(_val_counts[mc_iter])
    x_train_raw = _cal_features[mc_iter, :nc, :].astype(np.float64)
    y_train_raw = _cal_labels[mc_iter, :nc]
    x_val = _val_features[mc_iter, :nv, :].astype(np.float64)
    y_val = _val_labels[mc_iter, :nv]
    
    # read val_data from the inputs dictionary (per-iteration)
    inputs['val_data'] = x_val
 
    # classify
    if METHOD == 'RF':
        outputs = classifier.classifier(inputs, x_train_raw, y_train_raw,
                                        img_masked, depth_mask_flat, x_val)
    else:
        outputs = classifier.classifier(inputs, x_train_raw, y_train_raw,
                                        img_masked, depth_mask_flat)
    
    # tally this iteration's full-image classification into the per-class vote counts
    classification_iter = outputs[0] # shape (n_rows_img, n_cols_img)
    for ci, cls in enumerate(unique_classes):
        class_vote_counts[ci] += (classification_iter == cls)
 
    # predict on validation set for accuracy
    if METHOD == 'KNN':
        model = outputs[1]
        scaler = outputs[3]
        x_val_scaled = scaler.transform(x_val)
        y_pred = model.predict(x_val_scaled)
        y_pred_proba = model.predict_proba(x_val_scaled)
 
    elif METHOD in ('RF', 'MLC', 'SVM'):
        y_pred = outputs[2]
 
    # accuracy metrics
    overall_accuracy = accuracy_score(y_val, y_pred)*100
    conf_matrix = confusion_matrix(y_val, y_pred, labels=unique_classes)
    
    col_sums = conf_matrix.sum(axis=0) # predicted totals per class
    row_sums = conf_matrix.sum(axis=1) # reference totals per class

    producers_acc = np.where(col_sums > 0, conf_matrix.diagonal()/np.where(col_sums == 0, 1, col_sums), 0.0)
    consumers_acc = np.where(row_sums > 0, conf_matrix.diagonal()/np.where(row_sums == 0, 1, row_sums), 0.0)
 
    row = {'mc_iter': mc_iter, 'overall_accuracy': overall_accuracy}
    for i, cls in enumerate(np.unique(y_val)):
        row[f'producers_accuracy_cls{cls}'] = producers_acc[i]
        row[f'consumers_accuracy_cls{cls}'] = consumers_acc[i]

    # flatten confusion matrix into cm_true{i}_pred{j} columns, fixed to unique_classes order
    for i, true_cls in enumerate(unique_classes):
        for j, pred_cls in enumerate(unique_classes):
            row[f'cm_true{true_cls}_pred{pred_cls}'] = conf_matrix[i, j]

    mc_results.append(row)
 
    # track best iteration
    if overall_accuracy > best_oa:
        best_oa = overall_accuracy
        best_mc_iter = mc_iter
        best_outputs = outputs
        best_x_train_raw = x_train_raw
        best_y_train_raw = y_train_raw
        best_x_val = x_val
        best_y_val = y_val
 
    # progress every 10 iterations
    if (mc_iter+1)%10 == 0:
        print(f"\n  Iteration {mc_iter + 1}/{N_MC} — current best OA: {best_oa:.2f}% "
              f"(iteration {best_mc_iter}) | {time.time()-s:.1f}s elapsed.")
 
print("\ndone.\nSuccess! Monte Carlo classification complete.")
print(f"  Best overall accuracy: {best_oa:.2f}% (MC iteration {best_mc_iter}).")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (6) EXPORT ACCURACY SUMMARY
s = time.time()
print("\nExporting accuracy summary...", end=" ")
 
accuracy_df = pd.DataFrame(mc_results)
accuracy_df.to_csv(accuracy_output, index=False)
 
print("done.\nSuccess! Accuracy summary exported.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))
 
# %% (7) EXPORT BEST CLASSIFICATION
s = time.time()
print(f"\nExporting classified image for best MC iteration ({best_mc_iter})...", end=" ")
 
classification = best_outputs[0] # classified image array
 
# --------------- (a) update metadata ---------------
output_meta = clipped_meta.copy()
output_meta.update({'count': 1, 'dtype': 'uint8', 'nodata': 0})
 
# --------------- (b) write classification ---------------
with rasterio.open(classification_output, 'w', **output_meta) as dst:
    dst.write(classification, 1)
 
print("done.\nSuccess! Best classification exported.")
print(f"  Overall accuracy: {best_oa:.2f}%  |  MC iteration: {best_mc_iter}")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (8) EXPORT MONTE CARLO PER-CLASS PROBABILITY MAP
s = time.time()
print(f"\nExporting Monte Carlo per-class probability map ({n_classes} classes, {N_MC} iterations)...", end=" ")
 
# --------------- (a) convert vote counts to probabilities ---------------
class_probability = class_vote_counts.astype(np.float32) / N_MC # (n_classes, n_rows, n_cols)
 
# --------------- (b) flag pixels outside the valid depth/ROI mask as nodata ---------------
NODATA_VAL = -1.0
class_probability[:, ~depth_mask] = NODATA_VAL
 
# --------------- (c) write multi-band raster, one band per class ---------------
mc_prob_meta = clipped_meta.copy()
mc_prob_meta.update({'count': n_classes, 'dtype': 'float32', 'nodata': NODATA_VAL})
 
with rasterio.open(mc_class_probability_output, 'w', **mc_prob_meta) as dst:
    for i, cls in enumerate(unique_classes):
        dst.write(class_probability[i], i+1)
        dst.set_band_description(i+1, f'class_{cls}_probability')
 
print("done.\nSuccess! Monte Carlo class probability map exported.")
print(f"  Bands: {[f'class_{c}_probability' for c in unique_classes]}")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))