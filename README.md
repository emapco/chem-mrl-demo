# Chem-MRL Demo

A web application for demoing Chem-MRL model with similarity search capabilities.

## Features

- 🧪 **Interactive Molecule Editor**: Draw molecules using ChemWriter editor
- 🤖 **AI-Powered Embeddings**: Generate molecular embeddings using ChemMRL
- 🔍 **Similarity Search**: Find similar molecules using Redis hierarchical navigable small world (HNSW) algorithm

## Quick Start

### Using Docker (Recommended)

```bash
git clone https://github.com/emapco/chem-mrl-demo.git
cd chem-mrl-demo
docker compose up
```

### Manual Setup

1. **Install Dependencies**

```bash
pip install -r requirements.txt
```

2. **Start Redis**

```bash
redis-server
```

3. **Start App**

```bash
python app.py
```

### Access Application
Navigate to [http://localhost:7860](http://localhost:7860)

## Architecture

```
┌────────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  ChemWriter Editor │───▶  Gradio API      ───▶│  Chem-MRL       │
│  (Frontend)        │    │  (Backend)      │    │  (HF Model)     │
└────────────────────┘    └─────────────────┘    └─────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │  Redis + HNSW   │
                          │  (Vector DB)    │
                          └─────────────────┘
                                   │
                                   │
                                   ▼
                          ┌─────────────────┐
                          │Similar Molecules│
                          │   (Results)     │
                          └─────────────────┘
```

## Configuration

Environment variables in `.env`:

- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_PASSWORD`

## Visualization Data

The `visualization` directory contains embeddings of the [Isomer Design](https://isomerdesign.com/pihkal/search) SMILES dataset ([![License: CC BY-NC-SA 4.0](https://mirrors.creativecommons.org/presskit/buttons/80x15/svg/by-nc-sa.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)), with various embedding sizes. The `.tsv` files can be visualized using [TensorFlow Projector](https://projector.tensorflow.org/) or viewed directly using the links below.

| Embedding Dimension | URL |
|---------------------|-----|
| 1024 | [1024 embeddings](https://projector.tensorflow.org/?config=https://raw.githubusercontent.com/emapco/chem-mrl-demo/refs/heads/main/visualization/1024-template_project_config.json) |
| 512 | [512 embeddings](https://projector.tensorflow.org/?config=https://raw.githubusercontent.com/emapco/chem-mrl-demo/refs/heads/main/visualization/512-template_project_config.json) |
| 128 | [128 embeddings](https://projector.tensorflow.org/?config=https://raw.githubusercontent.com/emapco/chem-mrl-demo/refs/heads/main/visualization/128-template_project_config.json) |
| 32 | [32 embeddings](https://projector.tensorflow.org/?config=https://raw.githubusercontent.com/emapco/chem-mrl-demo/refs/heads/main/visualization/32-template_project_config.json) |
| 4 | [4 embeddings](https://projector.tensorflow.org/?config=https://raw.githubusercontent.com/emapco/chem-mrl-demo/refs/heads/main/visualization/4-template_project_config.json) |
| 2 | [2 embeddings](https://projector.tensorflow.org/?config=https://raw.githubusercontent.com/emapco/chem-mrl-demo/refs/heads/main/visualization/2-template_project_config.json) |

## License

Apache-2.0 license
