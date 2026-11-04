#David Carrasco Rivera + Dylan Cowley: 03/03/2026

# %% (0) IMPORT PACKAGES
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

def classifier(model_params, x_train, y_train, img, depth_mask, val_data):
    # %% UNPACK INPUT PARAMS
    band_names = model_params['band_names']
    n_trees = model_params['n_trees']
    min_samples_leaf = model_params['min_samples_leaf']
    random_state = model_params['random_state']
    n_rows = model_params['n_rows']
    n_cols = model_params['n_cols']
    x_val = model_params['val_data']

    # %% TRAIN CLASSIFIER
    # --------------- (a) initialise RF classifier ---------------
    rf_classifier = RandomForestClassifier(
        n_estimators = n_trees,
        min_samples_leaf = min_samples_leaf,
        random_state = random_state,
        class_weight = 'balanced_subsample',
        n_jobs = -1, # use all CPU cores
        verbose = 0
    )

    rf_classifier.fit(x_train, y_train)

    # --------------- (b) report band importance ---------------
    band_importance = pd.DataFrame({
        'band': band_names,
        'importance': rf_classifier.feature_importances_
    }).sort_values('importance', ascending=False)
    
    # %% CLASSIFY IMAGE
    # --------------- (a) classify depth masked areas ---------------
    n_pixels = depth_mask.shape[0]
    classification_masked = rf_classifier.predict(img)

    # create full classification array
    classification_flat = np.zeros(n_pixels, dtype=np.uint8)
    classification_flat[depth_mask] = classification_masked.astype(np.uint8)

    # reshape to image dimensions
    classification = classification_flat.reshape(n_rows, n_cols)
    
    y_pred = rf_classifier.predict(x_val)

    # %% SAVE OUTPUT
    return classification, band_importance, y_pred