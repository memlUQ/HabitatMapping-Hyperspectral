# date specification
YEAR_MONTH = '202411' # classification and field data tag based on imagery collection date

# sensor specification
SENSOR = 'PRISMA'

# site specification
DEPTH_MAX = 1000 # maximum depth in cm [CB = 2000, HR = 1000, EB = 1000, AD = 2000]
SITE_FLDR = 'Heron' # folder with data
SITE_NAME = 'Heron' # site name
SITE_ID = 'HR' # 2 character site identifier

# coordinate reference system
TARGET_CRS = "EPSG:4326"

# directory specification
CLASS_COLUMN = 'Class_num' # mapping class column name in field data
ROOT = '/path/to/working/directory'

# --------------- Random Forest parameters ---------------
RF_N_TREES = 500 # number of trees
RF_MIN_SAMPLES_LEAF = 2 # minimum number of leaves
RF_RANDOM_STATE = 42 # random seed

# --------------- k-Nearest Neighbour parameters ---------------
KNN_N_NEIGHBOURS = 5 # number of neighbours to consider
KNN_WEIGHTS = 'distance' # weighting functions: 'uniform' or 'distance'
KNN_METRIC = 'euclidean' # distance metric: 'euclidean', 'manhattan', 'minkowski'
KNN_ALGORITHM = 'auto' # searching algorithm: 'auto', 'ball_tree', 'kd_tree', or 'brute'

# --------------- Maximum Likelihood Classifier parameters ---------------
MLC_SHRINKAGE = 'auto' # options: 'auto', None (only for lsqr or eigen solvers), or a float in [0, 1]
MLC_STORE_COVARIANCE = True # whether to store class covariance matrices (only needed for svd solver, default True for others)
MLC_SOLVER = 'lsqr' # define the solver to be used: lsqr, svd, eigen

# --------------- Support Vector Machine parameters ---------------
SVM_KERNEL = 'rbf' # kernel type: 'rbf' (radial basis function), 'linear', 'poly' (polynomial), 'sigmoid' (sigmoidal function)
# notes for kernel choices (for mapping data into a higher dimensional space for more complex boundary definition within data):
#   - radial basis functions (utilising a series of Gaussian functions here) work better for highly non-linear data
#   - linear is best for easily separable data
#   - polynomial allows for simple curved decision boundaries, good for non-linear data
#   - sigmoidal functions are more useful for cases where there are clearly defined thresholds for separation in the original data
SVM_C = 50.0#20 # regularisation parameter (higher = less regularisation)
SVM_GAMMA = 0.05 # kernel coefficient: 'scale', 'auto', or 'float'
SVM_PROBABILITY = True # must be True to enable probability predictions