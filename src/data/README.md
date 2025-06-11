# Data Directory

This directory contains molecular data used by the Chem-MRL demo application.

## Dataset Information

### Isomer Design Dataset

The molecular data used in this application is sourced from the **Isomer Design** molecular library.

- **Dataset Source**: [Isomer Design](https://isomerdesign.com/pihkal/home)
- **License**: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) [![License: CC BY-NC-SA 4.0](https://mirrors.creativecommons.org/presskit/buttons/80x15/svg/by-nc-sa.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
- **License Type**: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International

### License Terms

This dataset is licensed under CC BY-NC-SA 4.0, which means:

- ✅ **Attribution**: You must give appropriate credit to the original source
- ❌ **NonCommercial**: You may not use the material for commercial purposes
- ✅ **ShareAlike**: If you remix, transform, or build upon the material, you must distribute your contributions under the same license

### Usage in This Project

The dataset is used to:
- Populate the Redis vector database with molecular embeddings
- Provide sample molecules for demonstration purposes
- Enable similarity search functionality through HNSW indexing

### Data Processing

The original SMILES data from Isomer Design has been processed through the following pipeline:

1. **Canonicalization**: SMILES strings were canonicalized using RDKit's implementation to ensure consistent molecular representations
2. **Embedding Generation**: Canonical SMILES were processed using the Chem-MRL model to generate molecular embeddings at various dimensions (2, 4, 32, 128, 512, 1024)
3. **Vector Storage**: The resulting embeddings are stored in the Redis vector database and indexed using HNSW for efficient similarity search operations

### Citation

If you use this data in your research or applications, please cite the original Isomer Design dataset and respect the CC BY-NC-SA 4.0 license terms.