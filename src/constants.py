# Model config
MODEL_NAME = "Derify/Chem-MRL-alpha"
SUPPORTED_EMBEDDING_DIMENSIONS = [1024, 768, 512, 256, 128, 64, 32, 16, 8, 4, 2]
EMBEDDING_DIMENSION = max(SUPPORTED_EMBEDDING_DIMENSIONS)

# HNSW config
HNSW_K = 6
HNSW_DISTANCE_METRIC = "COSINE"
HNSW_INITIAL_CAP = 100
HNSW_M = 8
HNSW_EF_CONSTRUCTION = 100
HNSW_EF_RUNTIME = 10

# Example data
SAMPLE_MOLECULES = [
    ("CCO", "Ethanol"),
    ("CC(=O)O", "Acetic acid"),
    ("c1ccccc1", "Benzene"),
    ("CC(C)O", "Isopropanol"),
    ("c1ccc(cc1)O", "Phenol"),
    ("CC(=O)OC1=CC=CC=C1C(=O)O", "Aspirin"),
    ("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "Caffeine"),
    ("CCN(CC)CC", "Triethylamine"),
    ("c1ccc2c(c1)cccn2", "Quinoline"),
    ("c1ccc(cc1)N", "Aniline"),
]
DATASET_SMILES = [
    "CCO",  # Ethanol
    "CC(=O)O",  # Acetic acid
    "c1ccccc1",  # Benzene
    "CC(C)O",  # Isopropanol
    "CCN(CC)CC",  # Triethylamine
    "c1ccc(cc1)O",  # Phenol
    "CC(=O)OC1=CC=CC=C1C(=O)O",  # Aspirin
    "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # Caffeine
    "CC(C)(C)OC(=O)NC1CCC(CC1)O",  # Boc-protected cyclohexanol
    "CCCCCCCCCCCCCCC(=O)O",  # Palmitic acid
    "c1ccc2c(c1)cccn2",  # Quinoline
    "CC1=CC=C(C=C1)C",  # p-Xylene
    "CCCCO",  # Butanol
    "CC(C)C",  # Isobutane
    "c1ccc(cc1)N",  # Aniline
    "CC(=O)N",  # Acetamide
    "CCCCCCCCCCCCCCCCCC(=O)O",  # Stearic acid
    "c1ccc(cc1)C(=O)O",  # Benzoic acid
    "CCc1ccccc1",  # Ethylbenzene
    "CC(C)CC(C)(C)C",  # 2,2,4-trimethylpentane
]
