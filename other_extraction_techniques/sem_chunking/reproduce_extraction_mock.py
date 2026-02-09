
import sys
import unittest
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Mock the dependencies before importing ai_extractor
sys.modules['langchain_ollama'] = MagicMock()
sys.modules['langchain_core.prompts'] = MagicMock()
sys.modules['langchain_core.output_parsers'] = MagicMock()
sys.modules['langchain_core.exceptions'] = MagicMock()

# Now import the class to test
# We need to manually define the class if we can't import due to missing deps in the environment,
# but let's try to import it assuming the file exists and we just mocked the external deps.
# However, the file imports them at the top level, so the mocks above should work.

from ai_extractor import SustainabilityExtractor, SustainabilityData

class TestSustainabilityExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = SustainabilityExtractor()
        # Mock the chain
        self.extractor.llm = MagicMock()
        self.extractor.parser = MagicMock()
        
    def test_process_data_merging(self):
        # Create dummy data with 3 chunks
        # Chunk 1: Returns emission_value only
        # Chunk 2: Returns emission_unit and sources
        # Chunk 3: Returns assurance (and redundant emission_value)
        
        input_data = [{
            "company": "TestCorp",
            "year": "2023",
            "content": [{
                "document_name": "test_doc.pdf",
                "document_path": "test/path.pdf",
                "content": {
                    "semantic_chunks": ["chunk1", "chunk2", "chunk3"]
                }
            }]
        }]
        
        # Mock extract_from_text to return different results based on input
        def mock_extract(text):
            if text == "chunk1":
                return {
                    "emission_value": 100.5,
                    "emission_unit": None,
                    "emission_sources": [],
                    "assurance": None,
                    "relevant_info": None
                }
            elif text == "chunk2":
                 return {
                    "emission_value": None,
                    "emission_unit": "tCO2e",
                    "emission_sources": ["Report", "Table 1"],
                    "assurance": None,
                    "relevant_info": None
                }
            elif text == "chunk3":
                 return {
                    "emission_value": 200.0, # Should be ignored if already filled
                    "emission_unit": None,
                    "emission_sources": [],
                    "assurance": True,
                    "relevant_info": "Some info"
                }
            return None

        self.extractor.extract_from_text = MagicMock(side_effect=mock_extract)
        
        # Run processing
        result = self.extractor.process_data(input_data)
        
        # Verify results
        doc_data = result[0]["content"][0]["ai_extracted_data"]
        
        print("Final Extracted Data:", doc_data)
        
        self.assertEqual(doc_data["emission_value"], 100.5, "Should keep first found value")
        self.assertEqual(doc_data["emission_unit"], "tCO2e", "Should fill from second chunk")
        self.assertEqual(doc_data["emission_sources"], ["Report", "Table 1"], "Should fill from second chunk")
        self.assertEqual(doc_data["assurance"], True, "Should fill from third chunk")
        self.assertEqual(doc_data["relevant_info"], "Some info", "Should fill from third chunk")
        
    def test_dynamic_fields(self):
        # Test if it handles all fields defined in SustainabilityData
        # We know what fields are there.
        fields = SustainabilityData.model_fields.keys()
        
        input_data = [{
            "company": "TestCorp",
            "year": "2023",
            "content": [{
                "document_name": "test_doc.pdf",
                "document_path": "test/path.pdf",
                "content": {
                    "semantic_chunks": ["chunk1"]
                }
            }]
        }]
        
        mock_result = {field: "test_val" for field in fields}
        # fix types for specific fields if needed
        if "emission_value" in mock_result: mock_result["emission_value"] = 123.0
        if "emission_sources" in mock_result: mock_result["emission_sources"] = ["src"]
        if "assurance" in mock_result: mock_result["assurance"] = True
        
        self.extractor.extract_from_text = MagicMock(return_value=mock_result)
        
        result = self.extractor.process_data(input_data)
        doc_data = result[0]["content"][0]["ai_extracted_data"]
        
        for field in fields:
            self.assertIn(field, doc_data)
            self.assertIsNotNone(doc_data[field])

if __name__ == '__main__':
    unittest.main()
