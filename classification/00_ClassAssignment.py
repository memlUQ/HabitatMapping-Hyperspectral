#David Carrasco + Dylan Cowley: 30/03/2026
#Python version 3.10 or greater required
#Package requirements:
#    - numpy, pandas, os, time, sys

# %% (0) IMPORT PACKAGES
import numpy as np
import pandas as pd
import os
import time
import sys

# read variables from configuration files
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))) # add folder for this script to path
from params import YEAR_MONTH, SITE_NAME, SITE_FLDR, SITE_ID # site + sensor details
from params import CLASS_COLUMN, ROOT # file/folder details

# %% (1) USER INPUT
print("Defining user input...", end=" ")
s = time.time()

# --------------- (a) setup asset directories and define file names ---------------
pwd = os.path.join(ROOT, SITE_FLDR, 'Mapping')
    
# inputs
field_data = os.path.join(pwd, '01_benthic_data', YEAR_MONTH, SITE_ID+'_'+YEAR_MONTH) # FILE for field data
map_file = os.path.join(pwd, '01_benthic_data', SITE_ID+'_labelmap') # FILE for data mapping

# output
output_file = os.path.join(pwd, '01_benthic_data', YEAR_MONTH, SITE_ID+'_'+YEAR_MONTH+'_classified.csv') # FILE for aggregated data

print("done.\nSuccess! User input defined.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (2) READ AND AGGREGATE REEFCLOUD DATA
print("\nLoading field data...", end=" ")
s = time.time()

# --------------- (a) load field data and mappings ---------------
rc = pd.read_csv(field_data+'.csv')
mapping = pd.read_csv(map_file+'.csv')

print("done.\nAggregating classes...", end=" ")

# --------------- (b) organise field data ---------------
mg = np.unique(mapping.map_group)
data = rc[mapping.class_label] # select only the cover data

mg_tots = np.zeros((len(data), len(mg)))
for i in np.arange(0, len(mg)):
    TF = mapping.map_group==mg[i] # select relevant columns
    cols_to_select = mapping.class_label[TF]
    mg_tots[:,i] = data[cols_to_select].sum(axis=1)

mg_tots = pd.DataFrame(mg_tots, columns=mg) # adjust column names
mg_tots = mg_tots.drop(columns='other') # remove "Other" column
mg_tots['tot'] = np.sum(mg_tots, axis=1)

# add coordinates
mg_tots.insert(loc=0, column='Longitude', value=rc.Longitude)
mg_tots.insert(loc=1, column='Latitude', value=rc.Latitude)

# retain metadata
mg_tots.insert(loc=2, column='image_name', value=rc.image_name)
mg_tots.insert(loc=3, column='yearmonth', value=rc.yearmonth)
mg_tots.insert(loc=4, column='date_UTC', value=rc['date (UTC)'])

print("done.\nFiltering for bad data...", end=" ")

# remove irrelevant rows
mask = mg_tots['tot'].ge(90)
df = mg_tots[mask]
print('done.\nSuccess! Data loaded and aggregated, {0:.2f}% of data removed.'.format(((len(mg_tots)-sum(mask))/len(mg_tots))*100))

print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (3) DEFINE MAPPING CLASSES
print("\nDefining mapping classes...", end=" ")
s = time.time()

# ---------------- (a) classification function ----------------
# this section requires some significant modification if the sites and classes are different, refer to the README file
def classify_benthos(df, SITE_NAME):
    
    dom_ben = np.zeros(len(df))

    if SITE_NAME == 'Heron':
        map_classes = ['Coral', 'Rock', 'Sand', 'Mixed']

        dom_ben[df.coral >= 30] = 1 # coral dominant
        dom_ben[(df.coral < 30) & (df.rock >= 50) & (dom_ben == 0)] = 2 # turf/rock dominant
        dom_ben[(df.coral < 30) & (df.sand >= 50) & (dom_ben == 0)] = 3 # sand dominant
        dom_ben[dom_ben == 0] = 4 # mixed benthos
    
    elif SITE_NAME == 'CoralBay':
        map_classes = ['Coral', 'Macroalgae', 'Rock', 'Sand', 'Mixed']
        
        dom_ben[df.coral >= 30] = 1 # coral dominant
        dom_ben[(df.coral < 30) & (df.algae >= 50) & (dom_ben == 0)] = 2 # macroalgae dominant
        dom_ben[(df.coral < 30) & (df.rock >= 50) & (dom_ben == 0)] = 3 # rock dominant
        dom_ben[(df.coral < 30) & (df.sand >= 50) & (dom_ben == 0)] = 4 # sand dominant
        dom_ben[dom_ben == 0] = 5 # mixed benthos
    
    elif SITE_NAME == 'Adelaide':
        map_classes = ['Posidonia', 'Amphibolis', 'Sparse Seagrass', 'Seagrass Mixed', 'Sand', 'Mixed']
        
        dom_ben[df.posidonia >= 50] = 1 # posidonia dominant
        dom_ben[(df.posidonia < 50) & (df.amphibolis >= 50) & (dom_ben == 0)] = 2 # amphibolis dominant
        dom_ben[(df.posidonia < 50) & (df.amphibolis < 50) & (df.seagrass_sparse >= 25) & (dom_ben == 0)] = 3 # sparse seagrass
        # mixed seagrass
        dom_ben[(df.posidonia < 50) & (df.amphibolis < 50) & (df.seagrass_sparse < 25) & (df.sand >= 50) & (dom_ben == 0)] = 4 # sand dominant
        dom_ben[dom_ben == 0] = 5 # mixed benthos
    
    elif SITE_NAME == 'EasternBanks':
        map_classes = ['Oceana', 'Zostera', 'Sparse Seagrass', 'Seagrass Mixed', 'Sand', 'Mixed']
        
        dom_ben[df.oceana >= 50] = 1 # oceana dominant
        dom_ben[(df.oceana < 50) & (df.zostera >= 50) & (dom_ben == 0)] = 2 # zostera dominant
        dom_ben[(df.oceana < 50) & (df.zostera < 50) & (df.seagrass_sparse >= 25) & (dom_ben == 0)] = 3 # sparse seagrass
        # mixed seagrass
        dom_ben[(df.posidonia < 50) & (df.amphibolis < 50) & (df.seagrass_sparse < 25) & (df.sand >= 50) & (dom_ben == 0)] = 4 # sand dominant
        dom_ben[dom_ben == 0] = 5 # mixed benthos
    
    return dom_ben, map_classes

# ---------------- (b) run classification ----------------
dom_ben, map_classes = classify_benthos(df, SITE_NAME)
df.insert(loc=len(df.columns), column=CLASS_COLUMN, value=dom_ben) # save dominant benthos classification
    
print("done.\nSuccess! Mapping classes defined.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))

# %% (4) EXPORT CLASS DATA
print("\nExporting aggregated data...", end=" ")
s = time.time()

df.to_csv(output_file, index=False)

print("done.\nSuccess! Data exported.")
print('{0:.2f} seconds elapsed.'.format(time.time()-s))