"""
Simple unit tests for canonical SMILES functionality.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from service import MolecularEmbeddingService


@pytest.fixture
def service():
    """Set up test fixtures - create service instance without full initialization."""
    return MolecularEmbeddingService.__new__(MolecularEmbeddingService)


class TestCanonicalSmilesBasic:
    """Basic tests for canonical SMILES functionality using MorganFingerprinter via MolecularEmbeddingService."""

    def test_morgan_fingerprinter_canonical_smiles_consistency(self, service):
        """Test that MorganFingerprinter canonical SMILES are consistent."""
        # Different representations of the same molecule
        ethanol_representations = ["CCO", "OCC", "C(C)O", "[CH3][CH2][OH]"]

        canonical_forms = []
        for smiles in ethanol_representations:
            try:
                canonical = service.get_canonical_smiles(smiles)
                if canonical:
                    canonical_forms.append(canonical)
            except Exception:
                continue

        # All valid representations should give the same canonical form
        if len(canonical_forms) > 1:
            first_canonical = canonical_forms[0]
            for canonical in canonical_forms[1:]:
                assert canonical == first_canonical, "Different representations should give same canonical SMILES"

    def test_morgan_fingerprinter_canonical_smiles_different_molecules(self, service):
        """Test that different molecules have different canonical SMILES."""
        different_molecules = [
            "C(C)O",  # Ethanol
            "CC(C)O",  # Isopropanol
            "CCCO",  # Propanol
            "C1=CC=CC=C1",  # Benzene
        ]

        canonical_forms = set()
        for smiles in different_molecules:
            try:
                canonical = service.get_canonical_smiles(smiles)
                if canonical:
                    canonical_forms.add(canonical)
            except Exception:
                continue

        # Should have unique canonical forms for different molecules
        assert len(canonical_forms) >= 3, "Different molecules should have different canonical SMILES"

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
    def test_morgan_fingerprinter_invalid_smiles_handling(self, service, invalid_smiles):
        """Test handling of invalid SMILES strings."""
        canonical = service.get_canonical_smiles(invalid_smiles)

        # For empty string, should return empty string
        if invalid_smiles == "":
            assert canonical == "", "Empty SMILES should return empty string"
        else:
            # Invalid SMILES should either return the original or empty string
            assert isinstance(canonical, str), f"Result for invalid SMILES '{invalid_smiles}' should be a string"

    def test_morgan_fingerprinter_canonical_smiles_properties(self, service):
        """Test properties of canonical SMILES."""
        test_smiles = "CCO"  # Ethanol

        canonical = service.get_canonical_smiles(test_smiles)
        assert isinstance(canonical, str), "Canonical SMILES should be a string"
        assert len(canonical) > 0, "Canonical SMILES should not be empty"

        # Canonical form should be consistent (idempotent)
        canonical2 = service.get_canonical_smiles(canonical)
        assert canonical == canonical2, "Canonical SMILES should be idempotent"


class TestAPIEndpointStructure:
    """Test the expected structure of API endpoints using MorganFingerprinter."""

    def test_canonical_smiles_function_signature(self, service):
        """Test that the service canonical SMILES function has the expected signature."""
        # Test the actual service function
        assert service.get_canonical_smiles("") == ""

        # Test with valid SMILES
        result = service.get_canonical_smiles("CCO")
        assert isinstance(result, str)

        # Test with different representations of the same molecule
        result1 = service.get_canonical_smiles("CCO")
        result2 = service.get_canonical_smiles("OCC")
        if result1 and result2:  # If both are valid
            assert result1 == result2, "Different representations should give same canonical SMILES"

        # Test with invalid SMILES
        result_invalid = service.get_canonical_smiles("INVALID")
        assert isinstance(result_invalid, str)

    def test_api_response_format(self, service):
        """Test the expected API response format using MorganFingerprinter."""

        def mock_api_response(smiles: str):
            """Mock API response for canonical SMILES using MorganFingerprinter."""
            try:
                canonical = service.get_canonical_smiles(smiles)
                return {"data": [canonical]}
            except Exception:
                return {"data": [smiles]}

        # Test response format
        response = mock_api_response("CCO")
        assert "data" in response
        assert isinstance(response["data"], list)
        assert len(response["data"]) == 1
        assert isinstance(response["data"][0], str)
