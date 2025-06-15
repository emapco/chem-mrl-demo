"""
Unit tests for the MolecularEmbeddingService class.
Tests the core functionality including canonical SMILES generation,
molecular embedding creation, and similarity search.
"""

import os
import sys
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from service import MolecularEmbeddingService


@pytest.fixture
def mock_dependencies(monkeypatch):
    """Mock all external dependencies for MolecularEmbeddingService."""
    # Mock SentenceTransformer
    mock_model_instance = Mock()
    mock_model_class = Mock(return_value=mock_model_instance)
    monkeypatch.setattr("service.SentenceTransformer", mock_model_class)

    # Mock Redis
    mock_redis_instance = Mock()
    mock_redis_class = Mock(return_value=mock_redis_instance)
    monkeypatch.setattr("service.redis.Redis", mock_redis_class)

    # Mock MorganFingerprinter
    mock_morgan_class = Mock()
    mock_morgan_class.canonicalize_smiles.side_effect = lambda x: x if x and x.strip() else None
    monkeypatch.setattr("service.MorganFingerprinter", mock_morgan_class)

    # Mock dataset
    mock_dataset = pd.DataFrame(
        {
            "smiles": ["CCO", "CC(C)O", "CCCO"],
            "name": ["Ethanol", "Isopropanol", "Propanol"],
            "properties": ["Alcohol", "Alcohol", "Alcohol"],
        }
    )
    monkeypatch.setattr("service.ISOMER_DESIGN_DATASET", mock_dataset)

    return {
        "model": mock_model_instance,
        "redis": mock_redis_instance,
        "morgan": mock_morgan_class,
    }


@pytest.fixture
def service(mock_dependencies):
    """Create a MolecularEmbeddingService instance with mocked dependencies."""
    return MolecularEmbeddingService()


class TestMolecularEmbeddingService:
    """Test cases for MolecularEmbeddingService"""

    @pytest.mark.parametrize(
        "invalid_smiles",
        [
            "INVALID",
            "C(C",  # Unmatched parenthesis
            "C=C=C=C",  # Invalid bonding
            "",  # Empty string
            "   ",  # Whitespace only
        ],
    )
    def test_get_canonical_smiles_invalid_smiles(self, service, invalid_smiles):
        """Test canonical SMILES generation with invalid SMILES strings."""
        result = service.get_canonical_smiles(invalid_smiles)
        # Should return the original string or empty string for invalid input
        assert isinstance(result, str)

    @pytest.mark.parametrize(
        "input_value,expected",
        [
            (None, ""),
            ("", ""),
            ("   ", ""),
        ],
    )
    def test_get_canonical_smiles_edge_cases(self, service, input_value, expected):
        """Test canonical SMILES generation with edge cases."""
        result = service.get_canonical_smiles(input_value)
        assert result == expected

    def test_get_molecular_embedding_valid_input(self, service, mock_dependencies):
        """Test molecular embedding generation with valid inputs."""
        # Mock the model's encode method
        mock_embedding = np.random.rand(1024).astype(np.float32)
        mock_dependencies["model"].encode.return_value = [mock_embedding]

        # Test with valid SMILES and embedding dimension
        smiles = "CCO"
        embed_dim = 512

        result = service.get_molecular_embedding(smiles, embed_dim)

        # Verify the result
        assert isinstance(result, np.ndarray)
        assert result.shape == (embed_dim,)
        mock_dependencies["model"].encode.assert_called_once()

    @pytest.mark.parametrize("invalid_dim", [0, -1])
    def test_get_molecular_embedding_invalid_dimension(self, service, invalid_dim):
        """Test molecular embedding generation with invalid dimensions."""
        smiles = "CCO"

        with pytest.raises(ValueError):
            service.get_molecular_embedding(smiles, invalid_dim)

    def test_truncate_and_normalize_embedding(self, service):
        """Test embedding truncation and normalization."""
        # Create a test embedding
        original_embedding = np.array([3.0, 4.0, 5.0, 6.0], dtype=np.float32)

        # Test truncation to smaller dimension
        result = service._truncate_and_normalize_embedding(original_embedding, 2)
        assert result.shape == (2,)

        # Test normalization (L2 norm should be 1)
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-6

        # Test no truncation needed
        result = service._truncate_and_normalize_embedding(original_embedding, 4)
        assert result.shape == (4,)
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-6

    def test_find_similar_molecules_success(self, service, mock_dependencies):
        """Test successful similarity search."""
        # Mock Redis search results
        mock_doc1 = Mock()
        mock_doc1.smiles = "CCO"
        mock_doc1.name = "Ethanol"
        mock_doc1.properties = "Alcohol"
        mock_doc1.score = "0.95"

        mock_doc2 = Mock()
        mock_doc2.smiles = "CC(C)O"
        mock_doc2.name = "Isopropanol"
        mock_doc2.properties = "Alcohol"
        mock_doc2.score = "0.87"

        mock_results = Mock()
        mock_results.docs = [mock_doc1, mock_doc2]

        mock_dependencies["redis"].ft.return_value.search.return_value = mock_results

        # Test the search
        query_embedding = np.random.rand(512).astype(np.float32)
        results = service.find_similar_molecules(query_embedding, 512, k=2)

        # Verify results
        assert len(results) == 2
        assert isinstance(results[0], dict)
        assert results[0]["smiles"] == "CCO"
        assert results[0]["name"] == "Ethanol"
        assert results[0]["properties"] == "Alcohol"
        assert results[0]["score"] == 0.95

    def test_find_similar_molecules_redis_error(self, service, mock_dependencies):
        """Test similarity search with Redis error."""
        # Mock Redis to raise an exception
        mock_dependencies["redis"].ft.return_value.search.side_effect = Exception("Redis error")

        query_embedding = np.random.rand(512).astype(np.float32)
        results = service.find_similar_molecules(query_embedding, 512)

        # Should return empty list on error
        assert results == []

    @pytest.mark.parametrize(
        "embed_dim,expected",
        [
            (512, "embedding_512"),
            (1024, "embedding_1024"),
        ],
    )
    def test_embedding_field_name(self, embed_dim, expected):
        """Test embedding field name generation."""
        assert MolecularEmbeddingService.embedding_field_name(embed_dim) == expected

    @pytest.mark.parametrize(
        "smiles,expected",
        [
            ("CCO", "mol:CCO"),
            ("c1ccccc1", "mol:c1ccccc1"),
        ],
    )
    def test_molecule_index_prefix(self, smiles, expected):
        """Test molecule index prefix generation."""
        assert MolecularEmbeddingService.molecule_index_prefix(smiles) == expected
