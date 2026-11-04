#David Carrasco Rivera + Dylan Cowley: 09/03/2026

# %% IMPORT PACKAGES
import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

def classifier(model_params, x_train, y_train, img, depth_mask):
    # %% UNPACK INPUT PARAMS
    n_neighbours = model_params['n_neighbours']
    weights = model_params['weights']
    metric = model_params['metric']
    algorithm = model_params['algorithm']
    n_rows = model_params['n_rows']
    n_cols = model_params['n_cols']
    
    # %% TRAIN CLASSIFIER
    # --------------- (a) initialise standard scaler ---------------
    scaler = StandardScaler()

    # fit and transform training data
    x_train_scaled = scaler.fit_transform(x_train)

    # scale the full image for classification
    img_masked_scaled = scaler.transform(img)

    # --------------- (b) initialise and train kNN ---------------
    knn_classifier = KNeighborsClassifier(
        n_neighbors=n_neighbours,
        weights=weights,
        metric=metric,
        algorithm=algorithm,
        n_jobs=-1 # use all CPU cores
    )

    knn_classifier.fit(x_train_scaled, y_train)

    # %% CLASSIFY IMAGE
    # --------------- (a) predict on masked pixels ---------------
    n_pixels = depth_mask.shape[0]
    batch_size = 50000
    n_samples = img_masked_scaled.shape[0]
    classification_masked = np.zeros(n_samples, dtype=np.uint8)
    confidence_masked = np.zeros(n_samples, dtype=np.float32)

    for i in range(0, n_samples, batch_size):
        end_idx = min(i + batch_size, n_samples)
        
        # get class predictions
        classification_masked[i:end_idx] = knn_classifier.predict(img_masked_scaled[i:end_idx])
        
        # get probability/confidence for each pixel
        proba = knn_classifier.predict_proba(img_masked_scaled[i:end_idx])
        confidence_masked[i:end_idx] = np.max(proba, axis=1)

    # create full classification array
    classification_flat = np.zeros(n_pixels, dtype=np.uint8)
    classification_flat[depth_mask] = classification_masked
    
    confidence_flat = np.zeros(n_pixels, dtype=np.float32)
    confidence_flat[depth_mask] = confidence_masked
    
    # reshape to image dimensions
    classification = classification_flat.reshape(n_rows, n_cols)
    confidence = confidence_flat.reshape(n_rows, n_cols)

    # %% SAVE OUTPUT
    return classification, knn_classifier, confidence, scaler