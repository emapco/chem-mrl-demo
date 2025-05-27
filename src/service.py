import logging
import os

import numpy as np
import redis
from dotenv import load_dotenv
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from sentence_transformers import SentenceTransformer

from constants import (
    DATASET_SMILES,
    EMBEDDING_DIMENSION,
    HNSW_DISTANCE_METRIC,
    HNSW_EF_CONSTRUCTION,
    HNSW_EF_RUNTIME,
    HNSW_INITIAL_CAP,
    HNSW_M,
    MODEL_NAME,
    SUPPORTED_EMBEDDING_DIMENSIONS,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        self.__populate_sample_data()

    def __create_hnsw_index(self):
        """Create HNSW index for molecular embeddings"""
        try:
            try:
                self.redis_client.ft(self.index_name).info()
                logger.info(f"Index {self.index_name} already exists")
                return
            except redis.exceptions.ResponseError:
                pass

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
                definition=IndexDefinition(prefix=["mol:"], index_type=IndexType.HASH),
            )

            logger.info(f"Created HNSW index: {self.index_name}")

        except Exception as e:
            logger.error(f"Failed to create HNSW index: {e}")
            raise

    def __populate_sample_data(self):
        """Populate Redis with sample molecular data"""
        try:
            # Check if data already exists
            if self.redis_client.exists("mol:sample_1"):
                logger.info("Sample data already exists")
                return

            logger.info("Populating sample molecular data...")

            for i, smiles in enumerate(DATASET_SMILES):
                try:
                    mapping: dict[str, bytes | str] = {
                        self.embedding_field_name(embed_dim): self.get_molecular_embedding(smiles, embed_dim).tobytes()
                        for embed_dim in SUPPORTED_EMBEDDING_DIMENSIONS
                    }
                    mapping["smiles"] = smiles

                    key = f"mol:sample_{i + 1}"
                    self.redis_client.hset(
                        key,
                        mapping=mapping,
                    )

                except Exception as e:
                    logger.error(f"Failed to process molecule {smiles}: {e}")
                    continue

            logger.info(f"Populated {len(DATASET_SMILES)} sample molecules")

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

    def find_similar_molecules(self, query_embedding: np.ndarray, embed_dim: int, k: int = 10) -> list[dict]:
        """Find k most similar molecules using HNSW"""
        try:
            query_vector = query_embedding.astype(np.float32).tobytes()
            query = (
                Query(f"*=>[KNN {k} @{self.embedding_field_name(embed_dim)} $vec AS score]")
                .sort_by("score")
                .return_fields("smiles", "score")
                .dialect(2)
            )

            results = self.redis_client.ft(self.index_name).search(query, query_params={"vec": query_vector})

            neighbors = []
            for doc in results.docs:
                neighbors.append({"smiles": doc.smiles, "score": float(doc.score)})

            return neighbors

        except Exception as e:
            logger.error(f"Failed to find similar molecules: {e}")
            return []

    @staticmethod
    def embedding_field_name(dim: int) -> str:
        """Generate embedding field name based on dimension"""
        return f"embedding_{dim}"
