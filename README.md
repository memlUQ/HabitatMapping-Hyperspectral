# Habitat Mapping (Hyperspectral)
Python based habitat mapping scripts for repeated creation of benthic cover maps, using hyperspectral satellite imagery. Scripts require georeferenced benthic photoquadrat data classified in [ReefCloud](https://reefcloud.ai/), satellite hyperspectral imagery, and bathymetry. The processing scripts are initially setup for mapping across: the Eastern Banks in Moreton Bay, Queensland (seagrass); Heron Reef in the Southern Great Barrier Reef, Queensland (coral); Coral Bay in Ningaloo Reef, Western Australia (coral); and the Adelaide metropolitan coast, South Australia (seagrass), all in Australia. These scripts are divided into:
- Field data pre-processing.
- Image pre-processing.
- Calibration/validation assignment.
- Habitat map classification.

# Field Data Pre-Processing (Optional)
Classified photoquadrat data from [ReefCloud](https://reefcloud.ai/) is reorganised into the desired benthic classes required for creating habitat maps. Field data is aggregated into thematic classes in the `00_ClassAssignment.py` script. Thematic class assignments are separated by site and require user specification for modification per site, with two specific input spreadsheets. Example input spreadsheets are provided here for the Heron Reef site as `HR_202411.csv` and `HR_labelmap.csv`.

> [!NOTE]
> Paths for input and output folder/files need to be changed to fit the users location and name of field data files. Thematic classes and class assignment thresholds also need to be adjusted from those existing in this script.

## Field Data
Any in situ training data can be used for training and validation (not just derived from ReefCloud), requiring the following fields as a spreadsheet in a `.csv` format (e.g., as in `HR_202411.csv`):
| Longitude | Latitude | _benthic cover details_ |
| ---------- | ---------- | ---------- |
| Longitude in decimal degrees (float) | Latitude in decimal degrees (float) | Percentage cover of benthic features at each field data point (from 0 -> 100) |

## Thematic Classes
Benthic classes are aggregated into thematic classes using the label mapping provided in the second input sreadsheet (e.g., as in `HR_labelmap.csv`). The label mapping input provides a key for class aggregation and requires user specification to ensure labels are correctly assigned between **benthic classes** and **thematic classes**. This input requires the following columns at mininum:
| map_group | class_label |
| ---------- | ---------- |
| Thematic mapping class that will be used to aggregate the **Field Data** | Class labels derived from the **Field Data** spreadsheet |

# Image Pre-Processing
Description...

# Points Processing
Description...

# Image Classification
Description...

# See Also
The [Habitat Mapping](https://github.com/memlUQ/HabitatMapping) scripts for continuous multispectral habitat mapping.

# References
Description...
