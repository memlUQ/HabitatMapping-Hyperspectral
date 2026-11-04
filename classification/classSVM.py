#David Carrasco Rivera + Dylan Cowley: 05/03/2026

# %% IMPORT PACKAGES
import numpy as np
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler

def classifier(model_params, x_train, y_train, img, depth_mask):
    # %% UNPACK INPUT PARAMS
    kernel = model_params['kernel']
    C = model_params['C']
    gamma = model_params['gamma']
    svm_probability = model_params['svm_probability']
    n_rows = model_params['n_rows']
    n_cols = model_params['n_cols']
    val_data = model_params['val_data']

    # %% TRAIN CLASSIFIER
    # --------------- (a) initialise and train SVM ---------------
    # SVM with RBF kernel finds optimal hyperplanes to separate classes in high-dimensional space
    # probability=True enables predict_proba via Platt scaling (adds training overhead)
    svm_classifier = SVC(
        kernel=kernel,
        C=C,
        gamma=gamma,
        probability=svm_probability,
        decision_function_shape='ovr' # one-vs-rest for multiclass
    )
    
    scaler = StandardScaler()
    x_train = scaler.fit_transform(x_train)
    img = scaler.transform(img)
    val_data = scaler.transform(val_data)
    
    svm_classifier.fit(x_train, y_train)

    # %% CLASSIFY IMAGE
    # --------------- (a) predict on masked pixels ---------------
    n_pixels = depth_mask.shape[0]
    batch_size = 50000
    n_samples = img.shape[0]
    classification_masked = np.zeros(n_samples, dtype=np.uint8)
    probability_masked = np.zeros(n_samples, dtype=np.float32)

    for i in range(0, n_samples, batch_size):
        end_idx = min(i + batch_size, n_samples)
        
        classification_masked[i:end_idx] = svm_classifier.predict(img[i:end_idx])
        
        proba = svm_classifier.predict_proba(img[i:end_idx])
        probability_masked[i:end_idx] = np.max(proba, axis=1)

    # create full classification array
    classification_flat = np.zeros(n_pixels, dtype=np.uint8)
    classification_flat[depth_mask] = classification_masked
    
    probability_flat = np.zeros(n_pixels, dtype=np.float32)
    probability_flat[depth_mask] = probability_masked
    
    # reshape to image dimensions
    classification = classification_flat.reshape(n_rows, n_cols)
    probability = probability_flat.reshape(n_rows, n_cols)

    # %% SAVE OUTPUT
    y_pred = svm_classifier.predict(val_data)
    return classification, probability, y_pred