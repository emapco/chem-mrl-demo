# Model config
MODEL_NAME = "Derify/ChemMRL-alpha"
SUPPORTED_EMBEDDING_DIMENSIONS = [1024, 768, 512, 256, 128, 64, 32, 16, 8, 4, 2]
EMBEDDING_DIMENSION = max(SUPPORTED_EMBEDDING_DIMENSIONS)
USE_HALF_PRECISION = True

# HNSW index parameters
HNSW_K = 6
HNSW_PARAMETERS = {
    # Embedding vector dtype
    "TYPE": "FLOAT16" if USE_HALF_PRECISION else "FLOAT32",
    # Embedding vectors are normalized so COSINE and IP are equivalent
    "DISTANCE_METRIC": "IP",
    # Defines the initial capacity of the vector index. It helps in pre-allocating space for the index.
    "INITIAL_CAP": 440,
    # Max number of outgoing edges (connections) for each node in a graph layer.
    "M": 24,
    # Max number of connected neighbors to consider during graph building.
    # Higher values increase accuracy, but also increase index build time.
    "EF_CONSTRUCTION": 384,
    # Max top candidates during KNN search. Higher values increase accuracy, but also increase search latency.
    "EF_RUNTIME": 12,
}

# Gradio launch parameters
LAUNCH_PARAMETERS = {
    "server_name": "0.0.0.0",
    "server_port": 7860,
    "share": False,
    "debug": False,
    "show_api": False,
    "pwa": True,
    "mcp_server": False,
}
