import logging
import os
import time
from typing import TypedDict

import numpy as np
import pandas as pd
import redis
import torch
from chem_mrl.molecular_fingerprinter import MorganFingerprinter
from dotenv import load_dotenv
from rdkit import Chem, RDLogger
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from sentence_transformers import SentenceTransformer

from constants import (
    EMBEDDING_DIMENSION,
    HNSW_K,
    HNSW_PARAMETERS,
    MODEL_NAME,
    SUPPORTED_EMBEDDING_DIMENSIONS,
    USE_HALF_PRECISION,
)
from data import ISOMER_DESIGN_DATASET


def setup_logger(clear_handler=False):
    if clear_handler:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)  # issue with sentence-transformer's logging handler
    RDLogger.DisableLog("rdApp.*")  # type: ignore - DisableLog is an exported function
    logging.basicConfig(format="%(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=logging.INFO)
    logger = logging.getLogger(__name__)
    return logger


load_dotenv("../.env")
logger = setup_logger(clear_handler=True)


class SimilarMolecule(TypedDict):
    smiles: str
    name: str
    properties: str
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
            model = SentenceTransformer(
                self.model_name,
                model_kwargs={
                    "torch_dtype": torch.float16 if USE_HALF_PRECISION else torch.float32,
                },
            )
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
            logger.info(
                f"Connecting to Redis at {redis_host}:{redis_port} with password: {'***' if redis_password else 'None'}"
            )
            redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True,
            )
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

        while True:
            try:
                redis_client.ping()
                break
            except redis.exceptions.BusyLoadingError:
                time_out = 5
                logger.warning(f"Redis is loading the dataset in memory. Retrying in {time_out} seconds...")
                time.sleep(time_out)

        return redis_client

    def _initialize_datastore(self):
        self.__create_hnsw_index()
        self.__populate_sample_data(ISOMER_DESIGN_DATASET)

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
                        **HNSW_PARAMETERS,
                        "DIM": dim,
                    },
                )
                for dim in SUPPORTED_EMBEDDING_DIMENSIONS
            ]
            schema.insert(0, TextField("smiles"))

            self.redis_client.ft(self.index_name).create_index(
                schema,
                definition=IndexDefinition(prefix=[self.molecule_index_prefix("")], index_type=IndexType.HASH),
            )

            logger.info(f"Created HNSW index: {self.index_name}")

        except Exception as e:
            logger.error(f"Failed to create HNSW index: {e}")
            raise

    def __populate_sample_data(self, df: pd.DataFrame):
        """Populate Redis with sample molecular data"""
        logger.info("Populating Redis with sample molecular data...")
        for _, row in df.iterrows():
            try:
                key = self.molecule_index_prefix(row["smiles"])
                if self.redis_client.exists(key):
                    continue

                embedding_cache: np.ndarray = self.get_molecular_embedding(row["smiles"], EMBEDDING_DIMENSION)

                mapping: dict[str, bytes | str] = {
                    self.embedding_field_name(embed_dim): self._truncate_and_normalize_embedding(
                        embedding_cache.copy(), embed_dim
                    ).tobytes()
                    for embed_dim in SUPPORTED_EMBEDDING_DIMENSIONS
                }
                mapping = {**mapping, **row.to_dict()}

                self.redis_client.hset(
                    key,
                    mapping=mapping,  # type: ignore
                )

            except Exception as e:
                logger.error(f"Failed to process molecule {row}: {e}")
                continue

        logger.info(f"Populated {len(df)} sample molecules")

    def get_molecular_embedding(self, smiles: str, embed_dim: int) -> np.ndarray:
        """Generate molecular embedding using ChemMRL"""
        try:
            if embed_dim <= 0:
                raise ValueError("embed_dim must be positive")

            # Preprocess smiles similarly as training data for optimal performance
            smiles = MorganFingerprinter.canonicalize_smiles(smiles) or smiles

            embedding: np.ndarray = self.model.encode(
                [smiles],
                show_progress_bar=False,
                convert_to_numpy=True,
            )[0]

            return self._truncate_and_normalize_embedding(embedding, embed_dim)

        except Exception as e:
            logger.error(f"Failed to generate embedding for {smiles}: {e}")
            raise

    def _truncate_and_normalize_embedding(self, embedding: np.ndarray, embed_dim: int) -> np.ndarray:
        """Truncate and normalize embedding"""
        if embed_dim < len(embedding):
            embedding = embedding[:embed_dim]
        norms = np.linalg.norm(embedding, ord=2, keepdims=True)
        return embedding / np.where(norms == 0, 1, norms)

    def find_similar_molecules(
        self, query_embedding: np.ndarray, embed_dim: int, k: int = HNSW_K
    ) -> list[SimilarMolecule]:
        """Find k most similar molecules using HNSW"""
        try:
            query_vector = query_embedding.tobytes()
            query = (
                Query(f"*=>[KNN {k} @{self.embedding_field_name(embed_dim)} $vec AS score]")
                .sort_by("score")
                .return_fields("smiles", "name", "properties", "score")
                .dialect(2)
            )

            results = self.redis_client.ft(self.index_name).search(
                query,
                query_params={
                    "vec": query_vector,  # type: ignore
                },
            )

            neighbors: list[SimilarMolecule] = [
                {"smiles": doc.smiles, "name": doc.name, "properties": doc.properties, "score": float(doc.score)}
                for doc in results.docs
            ]

            return neighbors

        except Exception as e:
            logger.error(f"Failed to find similar molecules: {e}")
            return []

    @staticmethod
    def get_canonical_smiles(smiles: str | None) -> str:
        """Convert SMILES to canonical SMILES representation"""
        if not smiles or smiles.strip() == "":
            return ""

        canonical = MorganFingerprinter.canonicalize_smiles(smiles.strip())
        if canonical is None:
            return smiles.strip()
        return canonical

    @staticmethod
    def get_smiles_from_mol_file(mol_file: str) -> str:
        """Convert SMILES to canonical SMILES representation"""
        if not mol_file or mol_file.strip() == "":
            return ""

        mol = Chem.rdmolfiles.MolFromMolBlock(mol_file)
        if mol is None:
            return ""
        return Chem.MolToSmiles(mol, canonical=True)

    @staticmethod
    def embedding_field_name(dim: int) -> str:
        return f"embedding_{dim}"

    @staticmethod
    def molecule_index_prefix(smiles: str) -> str:
        return f"mol:{smiles}"
