import os

import pandas as pd

__data_dir = os.path.join(os.path.dirname(__file__), "data")

__dataset_smiles_file = os.path.join(__data_dir, "dataset_smiles.csv")
__sample_smiles_file = os.path.join(__data_dir, "sample_smiles.csv")
__isomer_design_subset_file = os.path.join(__data_dir, "isomer_design_subset.csv")

DATASET_SMILES = pd.read_csv(__dataset_smiles_file)
SAMPLE_SMILES = pd.read_csv(__sample_smiles_file)
ISOMER_DESIGN_SUBSET = pd.read_csv(__isomer_design_subset_file)
