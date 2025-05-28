import logging
import os
from typing import TypedDict

import numpy as np
import pandas as pd
import redis
from dotenv import load_dotenv
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from sentence_transformers import SentenceTransformer

from constants import (
    EMBEDDING_DIMENSION,
    HNSW_DISTANCE_METRIC,
    HNSW_EF_CONSTRUCTION,
    HNSW_EF_RUNTIME,
    HNSW_INITIAL_CAP,
    HNSW_M,
    MODEL_NAME,
    SUPPORTED_EMBEDDING_DIMENSIONS,
)
from data import DATASET_SMILES, ISOMER_DESIGN_SUBSET

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimilarMolecule(TypedDict):
    smiles: str
    name: str
    category: str
    score: float


class MolecularEmbeddingService:
    def __init__(self):
        self.model_name = MODEL_NAME
        self.index_name = "molecule_embeddings"
        self.model_embed_dim = EMBEDDING_DIMENSION

        self.model = self._initialize_model()
        self.redis_client = self._initialize_redis()
        self._initialize_datastore()

    def _initialize_model(self):
        """Initialize the Hugging Face transformers model"""
        try:
            model = SentenceTransformer(self.model_name)  # type: ignore
            model.eval()
            return model
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def _initialize_redis(self):
        """Initialize Redis connection"""
        try:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", 6379))
            redis_password = os.getenv("REDIS_PASSWORD", None)
            redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True,
            )
            redis_client.ping()
            return redis_client
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _initialize_datastore(self):
        self.__create_hnsw_index()
        self.__populate_sample_data(DATASET_SMILES)
        self.__populate_sample_data(ISOMER_DESIGN_SUBSET)

    def __create_hnsw_index(self):
        """Create HNSW index for molecular embeddings"""
        try:
            self.redis_client.ft(self.index_name).info()
            logger.info(f"Index {self.index_name} already exists")
            return
        except redis.exceptions.ResponseError:
            pass

        try:
            schema: list[TextField | VectorField] = [
                VectorField(
                    self.embedding_field_name(dim),
                    "HNSW",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": dim,
                        "DISTANCE_METRIC": HNSW_DISTANCE_METRIC,
                        "INITIAL_CAP": HNSW_INITIAL_CAP,
                        "M": HNSW_M,
                        "EF_CONSTRUCTION": HNSW_EF_CONSTRUCTION,
                        "EF_RUNTIME": HNSW_EF_RUNTIME,
                    },
                )
                for dim in SUPPORTED_EMBEDDING_DIMENSIONS
            ]
            schema.insert(0, TextField("smiles"))

            self.redis_client.ft(self.index_name).create_index(
                schema,
                definition=IndexDefinition(prefix=[self.molecule_prefix("")], index_type=IndexType.HASH),
            )

            logger.info(f"Created HNSW index: {self.index_name}")

        except Exception as e:
            logger.error(f"Failed to create HNSW index: {e}")
            raise

    def __populate_sample_data(self, df: pd.DataFrame):
        """Populate Redis with sample molecular data"""
        logger.info("Populating sample molecular data...")
        try:
            for _, row in df.iterrows():
                try:
                    key = self.molecule_prefix(row["smiles"])
                    if self.redis_client.exists(key):
                        continue

                    mapping: dict[str, bytes | str] = {
                        self.embedding_field_name(embed_dim): self.get_molecular_embedding(
                            row["smiles"], embed_dim
                        ).tobytes()
                        for embed_dim in SUPPORTED_EMBEDDING_DIMENSIONS
                    }
                    mapping = {**mapping, **row.to_dict()}

                    self.redis_client.hset(
                        key,
                        mapping=mapping,
                    )

                except Exception as e:
                    logger.error(f"Failed to process molecule {row}: {e}")
                    continue

            logger.info(f"Populated {len(df)} sample molecules")

        except Exception as e:
            logger.error(f"Failed to populate sample data: {e}")

    def get_molecular_embedding(self, smiles: str, embed_dim: int) -> np.ndarray:
        """Generate molecular embedding using ChemMRL"""
        try:
            if embed_dim <= 0:
                raise ValueError("embed_dim must be positive")

            embedding: np.ndarray = self.model.encode(
                [smiles],
                show_progress_bar=False,
                convert_to_numpy=True,
            )[0]

            if embed_dim < len(embedding):
                embedding = embedding[:embed_dim]

            norms = np.linalg.norm(embedding, ord=2, keepdims=True)
            return embedding / np.where(norms == 0, 1, norms)

        except Exception as e:
            logger.error(f"Failed to generate embedding for {smiles}: {e}")
            raise

    def find_similar_molecules(self, query_embedding: np.ndarray, embed_dim: int, k: int = 10) -> list[SimilarMolecule]:
        """Find k most similar molecules using HNSW"""
        try:
            query_vector = query_embedding.astype(np.float32).tobytes()
            query = (
                Query(f"*=>[KNN {k} @{self.embedding_field_name(embed_dim)} $vec AS score]")
                .sort_by("score")
                .return_fields("smiles", "name", "category", "score")
                .dialect(2)
            )

            results = self.redis_client.ft(self.index_name).search(query, query_params={"vec": query_vector})

            neighbors: list[SimilarMolecule] = []
            for doc in results.docs:
                neighbors.append(
                    {"smiles": doc.smiles, "name": doc.name, "category": doc.category, "score": float(doc.score)}
                )

            return neighbors

        except Exception as e:
            logger.error(f"Failed to find similar molecules: {e}")
            return []

    @staticmethod
    def embedding_field_name(dim: int) -> str:
        return f"embedding_{dim}"

    @staticmethod
    def molecule_prefix(smiles: str) -> str:
        return f"mol:{smiles}"
