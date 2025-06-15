"""
Unit tests for the Gradio app.
Tests the App class methods for molecular similarity search functionality.
"""

import os
import sys
from unittest.mock import Mock

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app import App


class TestAppEndpoints:
    """Test cases for App API endpoints"""

    @pytest.fixture
    def app(self):
        """Set up test fixtures before each test method."""
        # Mock the embedding service to avoid actual model loading
        with pytest.MonkeyPatch().context() as m:
            mock_service_class = Mock()
            mock_service_instance = Mock()
            mock_service_class.return_value = mock_service_instance
            m.setattr("app.MolecularEmbeddingService", mock_service_class)

            app_instance = App()
            app_instance.embedding_service = mock_service_instance
            return app_instance

    def test_molecule_similarity_search_pipeline_valid_input(self, app):
        """Test similarity search pipeline with valid input."""
        # Mock the service methods
        mock_embedding = np.array([0.1, 0.2, 0.3, 0.4])
        mock_neighbors = [
            {"smiles": "CCO", "name": "Ethanol", "properties": "Alcohol", "score": 0.95},
            {"smiles": "CC(C)O", "name": "Isopropanol", "properties": "Alcohol", "score": 0.87},
        ]

        app.embedding_service.get_molecular_embedding.return_value = mock_embedding
        app.embedding_service.find_similar_molecules.return_value = mock_neighbors

        # Test the method
        embedding, neighbors, status = app.molecule_similarity_search_pipeline("CCO", 512)

        # Verify the results
        assert embedding == mock_embedding.tolist()
        assert neighbors == mock_neighbors
        assert status == "Search completed successfully"

        # Verify service calls
        app.embedding_service.get_molecular_embedding.assert_called_once_with("CCO", 512)
        app.embedding_service.find_similar_molecules.assert_called_once_with(mock_embedding, 512)

    def test_molecule_similarity_search_pipeline_empty_input(self, app):
        """Test similarity search pipeline with empty input."""
        # Test the method
        embedding, neighbors, status = app.molecule_similarity_search_pipeline("", 512)

        # Verify the results
        assert embedding == []
        assert neighbors == []
        assert status == "Please provide a valid SMILES string"

        # Verify service methods were not called
        app.embedding_service.get_molecular_embedding.assert_not_called()
        app.embedding_service.find_similar_molecules.assert_not_called()

    def test_molecule_similarity_search_pipeline_whitespace_input(self, app):
        """Test similarity search pipeline with whitespace-only input."""
        # Test the method
        embedding, neighbors, status = app.molecule_similarity_search_pipeline("   ", 512)

        # Verify the results
        assert embedding == []
        assert neighbors == []
        assert status == "Please provide a valid SMILES string"

    def test_molecule_similarity_search_pipeline_service_error(self, app):
        """Test similarity search pipeline when service raises an error."""
        # Mock the service method to raise an exception
        app.embedding_service.get_molecular_embedding.side_effect = Exception("Embedding error")

        # Test the method
        embedding, neighbors, status = app.molecule_similarity_search_pipeline("CCO", 512)

        # Verify the results
        assert embedding == []
        assert neighbors == []
        assert status.startswith("Search failed:")

    def test_handle_search_valid_input(self, app, monkeypatch):
        """Test handle_search method with valid input."""
        # Mock the pipeline method
        mock_embedding = [0.1, 0.2, 0.3, 0.4]
        mock_neighbors = [{"smiles": "CCO", "name": "Ethanol", "properties": "Alcohol", "score": 0.95}]
        mock_status = "Search completed successfully"

        mock_pipeline = Mock(return_value=(mock_embedding, mock_neighbors, mock_status))
        monkeypatch.setattr(app, "molecule_similarity_search_pipeline", mock_pipeline)

        mock_image = Mock()
        mock_draw = Mock(return_value=mock_image)
        monkeypatch.setattr(app, "_draw_molecule_grid", mock_draw)

        # Test the method
        embedding, neighbors, image, status = app.handle_search("CCO", 512)

        # Verify the results
        assert embedding == mock_embedding
        assert neighbors == mock_neighbors
        assert image == mock_image
        assert status == mock_status

    def test_handle_search_empty_input(self, app):
        """Test handle_search method with empty input."""
        # Test the method
        embedding, neighbors, image, status = app.handle_search("", 512)

        # Verify the results
        assert embedding == []
        assert neighbors == []
        assert image is None
        assert status == "Please draw a molecule or enter a SMILES string"

    def test_clear_all(self):
        """Test clear_all static method."""
        result = App.clear_all()

        # Verify the result
        expected = ("", "", [], [], None, "Cleared - Draw a new molecule or enter SMILES")
        assert result == expected

    def test_truncated_attribute(self):
        """Test _truncated_attribute static method."""
        # Test with short string
        obj = {"name": "Ethanol"}
        result = App._truncated_attribute(obj, "name", 10)
        assert result == "Ethanol"

        # Test with long string
        obj = {"name": "Very long molecule name that exceeds the limit"}
        result = App._truncated_attribute(obj, "name", 10)
        assert result == "Very long ..."


class TestAppIntegration:
    """Integration tests for the App class."""

    def test_app_initialization(self, monkeypatch):
        """Test that the app initializes correctly."""
        mock_service_class = Mock()
        monkeypatch.setattr("app.MolecularEmbeddingService", mock_service_class)

        app = App()

        # Verify the app has the required attributes
        assert app.embedding_service is not None
        assert app.demo is not None

    def test_gradio_interface_creation(self, monkeypatch):
        """Test that the Gradio interface is created correctly."""
        mock_service_class = Mock()
        monkeypatch.setattr("app.MolecularEmbeddingService", mock_service_class)

        app = App()

        # Verify the demo is created
        assert app.demo is not None

        # Check that the demo has the expected title
        assert app.demo.title == "Chem-MRL: Molecular Similarity Search Demo"
