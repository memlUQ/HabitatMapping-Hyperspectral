# Habitat Mapping (Hyperspectral)
Python based habitat mapping scripts for repeated creation of benthic cover maps, using hyperspectral satellite imagery. Scripts require georeferenced benthic photoquadrat data classified in [ReefCloud](https://reefcloud.ai/), satellite hyperspectral imagery, and bathymetry. The processing scripts are initially setup for mapping across: the Eastern Banks in Moreton Bay, Queensland (seagrass); Heron Reef in the Southern Great Barrier Reef, Queensland (coral); Coral Bay in Ningaloo Reef, Western Australia (coral); and the Adelaide metropolitan coast, South Australia (seagrass), all in Australia. These scripts are divided into:
- Field data pre-processing.
- Image pre-processing.
- Calibration/validation assignment.
- Habitat map classification.

> [!WARNING]
> Several variables are defined in the separate `params.py` file, which is imported into all scripts used here.
> 
> Each script has a **user input** section just under the package imports. Any major changes required to produce output at different sites than those described here will be made in this section. If any further changes are required, these are specified where relevant below.
>
> The HPC version of these scripts also utilises the package [argparse](https://docs.python.org/3/library/argparse.html).
> 
> These scripts were written with Python v3.10.

# Field Data Pre-Processing (Optional)
See: `00_ClassAssignment.py`

> [!IMPORTANT]
> Packages required: [NumPy](https://numpy.org/), [Pandas](https://pandas.pydata.org/), [os](https://docs.python.org/3/library/os.html), [sys](https://docs.python.org/3/library/sys.html), and [time](https://docs.python.org/3/library/time.html).

Classified photoquadrat data from [ReefCloud](https://reefcloud.ai/) is reorganised into the desired benthic classes required for creating habitat maps. Field data is aggregated into thematic classes separated by site, which require user specification for modification, with two specific input spreadsheets. Example input spreadsheets are provided here for the Heron Reef site as `HR_202411.csv` and `HR_labelmap.csv`.

> [!NOTE]
> Paths for input and output folder/files need to be changed to fit the users location and name of field data files. Thematic classes and class assignment thresholds also need to be adjusted from those existing in this script.

## Field Data
Any in situ training data can be used for training and validation (not just derived from ReefCloud), requiring at least the following fields as a spreadsheet in a `.csv` format (e.g., as in `HR_202411.csv`):
| Longitude | Latitude | _benthic cover details_ |
| ---------- | ---------- | ---------- |
| Longitude in decimal degrees (float) | Latitude in decimal degrees (float) | Percentage cover of benthic features at each field data point (from 0 -> 100) |

Section 2 (b) also has a few lines to retain some metadata, if required. Currently, it retains the `image_name` (string), `yearmonth` (integer), and `date_UTC` (string) columns. This requires manual adjustment if columns are named differently.

> [!NOTE]
> There are a number of columns in the _benthic cover details_ section equal to the number of benthic classes (see `HR_202411.csv` as an example).

## Thematic Classes
Benthic classes are aggregated into thematic classes using the label mapping provided in the second input sreadsheet (e.g., as in `HR_labelmap.csv`). The label mapping input provides a key for class aggregation and requires user specification to ensure labels are correctly assigned between **benthic classes** and **thematic classes**. This input requires the following columns at mininum:
| map_group | class_label |
| ---------- | ---------- |
| Thematic mapping class that will be used to aggregate the **Field Data** | Class labels derived from the **Field Data** spreadsheet |

# Image Pre-Processing
See: `01_ImageProcessing.py`

> [!IMPORTANT]
> Packages required: [GeoPandas](https://geopandas.org/en/stable/), [Rasterio](https://rasterio.readthedocs.io/en/stable/), [Matplotlib](https://matplotlib.org/), [scikit-learn](https://scikit-learn.org/stable/), [scikit-image](https://scikit-image.org/), [SciPy](https://scipy.org/), [NumPy](https://numpy.org/), [os](https://docs.python.org/3/library/os.html), [sys](https://docs.python.org/3/library/sys.html), and [time](https://docs.python.org/3/library/time.html).

> [!WARNING]
> Depth information **must** be included in this preprocessing stage as it is used for masking and subsequent classification. If depth data is not available, this script will need to be modified (mostly in section 5 and 6).

Image preprocessing here includes ROI masking, white whater masking, calculation of basic statistics, removal of unnecessary bands, inclusion of supporting physical information (depth, slope, or waves), principal components analysis (PCA), image texture (using a grey-level co-occurrence matrix), and image segmentation via Simple Linear Iterative Clustering (SLIC). As a result, the script requires **bathymetry** (as a `.tiff`) and a **region of interest** file (as a shapefile).

Other important specifications include the designation of which red, green, and blue bands to consider for analysis and those for visualisation. As the script is setup at the current stage, an equal number of red, green, and blue bands are required for image statistics, but only one of each is required for visualisation.

The processed, segmented image is exported as a raster (`.tiff`) which includes all statistical layers, the first three principal components, texture metrics, physical layers, and image segment information.

# Points Processing
See: `02_PointsProcessing.py`

> [!IMPORTANT]
> Packages required: [GeoPandas](https://geopandas.org/en/stable/), [Rasterio](https://rasterio.readthedocs.io/en/stable/), [Pandas](https://pandas.pydata.org/), [Matplotlib](https://matplotlib.org/), [NumPy](https://numpy.org/), [Shapely](https://shapely.readthedocs.io/en/stable/), [zarr-python](https://zarr.readthedocs.io/en/stable/), [warnings](https://docs.python.org/3/library/warnings.html), [os](https://docs.python.org/3/library/os.html), [sys](https://docs.python.org/3/library/sys.html), and [time](https://docs.python.org/3/library/time.html).

This script assigns the reclassified field data (from `00_ClassAssignment.py` or defined manually) into calibration and validation data. Field data are aggregated spatially, dependent on pixel size, to ensure one representative point is used for a specific pixel if multiple field observations are contained within. Cal/val data is then split using a uniform random sampling approach 100 times and the training scenarios are saved into a zarr store to be read by the classification script in subsequent stages. This script also ensures the number of cal/val points for thematic classes are balanced, with no single class dominating the training dataset. As such, if one class has a very small number of training points available for cal/val assignment, the other classes will also have a smaller number of training points to ensure there is no major class imbalances. It is recommended to investigate the plots produced by this script to see the balance of cal/val points across all thematic classes and reassign or reassess thematic classes where necessary.

# Image Classification
See: `03_Classification.py`

> [!IMPORTANT]
> Packages required: [GeoPandas](https://geopandas.org/en/stable/), [Rasterio](https://rasterio.readthedocs.io/en/stable/), [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/), [scikit-learn](https://scikit-learn.org/stable/), [zarr-python](https://zarr.readthedocs.io/en/stable/), [os](https://docs.python.org/3/library/os.html), [sys](https://docs.python.org/3/library/sys.html), and [time](https://docs.python.org/3/library/time.html).

> [!IMPORTANT]
> This script has 4 dependent scripts (`classKNN.py`, `classMLC.py`, `classRF.py`, and `classSVM.py`), which contain the classification functions and parameters used for each classification methodology.

This script provides a thematic classification for the segmented image from `01_ImageProcessing.py` using the training data in `02_PointsProcessing.py` and, as such, requires these scripts to be run first. The classification methodology is user defined, with other specifics drawn from the params file. Note that the script also contains specific bands that are used for classification, which is sensor dependent. It is recommended to investigate the **user input** section and adjust where necessary. 

Each image is classified with the defined methodology 100 times, using the predefined training scenarios from `02_PointsProcessing.py`. A raster file for the classification with the best overall accuracy is produced, along with ccuracy metrics (overall, user's, and producer's accuracies) and summary raster files that show the probability of assignment at each pixel, per thematic class. This probability is derived from the 100 classified images, showing the chance that each pixel is assigned to a specific thematic class, giving an indication of classification variability and persistence.

# See Also
Existing MEML UQ multispectral [Habitat Mapping](https://github.com/memlUQ/HabitatMapping) scripts for continuous multispectral habitat mapping.

# References
Description...
