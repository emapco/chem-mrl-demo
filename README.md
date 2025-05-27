# Chem-MRL Demo

A web application for demoing Chem-MRL model with similarity search capabilities.

## Features

- 🧪 **Interactive Molecule Editor**: Draw molecules using JSME editor
- 🤖 **AI-Powered Embeddings**: Generate molecular embeddings using ChemMRL
- 🔍 **Similarity Search**: Find similar molecules using Redis HNSW algorithm
- 📊 **Real-time Analysis**: Instant SMILES generation and analysis

## Quick Start

### Using Docker (Recommended)

```bash
git clone <repository>
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

4. **Open Application**
Navigate to `http://localhost:7860`

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   JSME Editor   │───▶  Gradio API      ───▶│  Chem-MRL       │
│   (Frontend)    │    │  (Backend)      │    │  (HF Model)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
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

## License

MIT License