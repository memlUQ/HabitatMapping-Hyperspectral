#David Carrasco Rivera + Dylan Cowley: 14/09/2026

# %% IMPORT PACKAGES
import numpy as np
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

def classifier(model_params, x_train, y_train, img, depth_mask):
    # %% UNPACK INPUT PARAMS
    store_covariance = model_params['store_covariance']
    shrinkage_opt = model_params['shrinkage_opt']
    solver_opt = model_params['solver_opt']
    n_rows = model_params['n_rows']
    n_cols = model_params['n_cols']
    val_data = model_params['val_data']

    # %% TRAIN CLASSIFIER
    # --------------- (a) initialise and train MLC ---------------
    # MLC is implemented using Linear Discriminant Analysis (LDA)
    mlc_classifier = LinearDiscriminantAnalysis(
        shrinkage=shrinkage_opt,
        solver=solver_opt,
        store_covariance=store_covariance
    )

    # fit and transform training data
    mlc_classifier.fit(x_train, y_train)

    # %% CLASSIFY IMAGE   
    # --------------- (a) predict on masked pixels ---------------
    n_pixels = depth_mask.shape[0]
    batch_size = 50000
    n_samples = img.shape[0]
    classification_masked = np.zeros(n_samples, dtype=np.uint8)
    probability_masked = np.zeros(n_samples, dtype=np.float32)

    for i in range(0, n_samples, batch_size):
        end_idx = min(i + batch_size, n_samples)
        
        # get class predictions
        classification_masked[i:end_idx] = mlc_classifier.predict(img[i:end_idx])
        
        # get maximum probability (confidence) for each pixel
        proba = mlc_classifier.predict_proba(img[i:end_idx])
        probability_masked[i:end_idx] = np.max(proba, axis=1)

    # create full classification array
    classification_flat = np.zeros(n_pixels, dtype=np.uint8)
    classification_flat[depth_mask] = classification_masked

    probability_flat = np.zeros(n_pixels, dtype=np.float32)
    probability_flat[depth_mask] = probability_masked

    # reshape to image dimensions
    classification = classification_flat.reshape(n_rows, n_cols)
    probability = probability_flat.reshape(n_rows, n_cols)
    
    y_pred = mlc_classifier.predict(val_data)
    
    # %% SAVE OUTPUT
    return classification, probability, y_pred