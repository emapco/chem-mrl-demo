import os

import pandas as pd

__data_dir = os.path.join(os.path.dirname(__file__), "data")

__sample_smiles_file = os.path.join(__data_dir, "sample_smiles.csv")
__isomer_design_dataset_file = os.path.join(__data_dir, "isomer_design_dataset.csv")

SAMPLE_SMILES = pd.read_csv(__sample_smiles_file)
ISOMER_DESIGN_DATASET = pd.read_csv(__isomer_design_dataset_file, sep="\t")
