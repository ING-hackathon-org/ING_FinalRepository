#!/usr/bin/env python3
"""
Main script for processing PDF documents in a hierarchical folder structure.
Extracts text from PDFs, performs semantic chunking, and outputs structured JSON data.

Expected folder structure:
reports/
├── company_name_1/
│   ├── 2023/
│   │   ├── document1.pdf
│   │   └── document2.pdf
│   └── 2024/
│       └── document3.pdf
└── company_name_2/
    └── 2023/
        └── document4.pdf
"""

import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
from extractor import Extractor, TextType
from semantic_chunker import SemanticChunker
try:
    from ai_extractor import SustainabilityExtractor
except ImportError:
    SustainabilityExtractor = None



class DocumentProcessor:
    """
    Processes PDF documents from a hierarchical folder structure and generates structured JSON output.
    """
    
    def __init__(
        self,
        use_semantic_chunking: bool = True,
        similarity_threshold: float = 0.5,
        min_chunk_size: int = 1,
        max_chunk_size: int = 10,
        include_titles: bool = True
    ):
        """
        Initialize the document processor.
        
        Args:
            use_semantic_chunking: Whether to apply semantic chunking to extracted text
            similarity_threshold: Threshold for semantic similarity (0-1)
            min_chunk_size: Minimum number of sentences per chunk
            max_chunk_size: Maximum number of sentences per chunk
            include_titles: Whether to include titles and subtitles in extraction
        """
        self.extractor = Extractor(include_titles=include_titles)
        self.use_semantic_chunking = use_semantic_chunking
        
        if use_semantic_chunking:
            self.chunker = SemanticChunker(
                similarity_threshold=similarity_threshold,
                min_chunk_size=min_chunk_size,
                max_chunk_size=max_chunk_size,
                use_percentile=False
            )
        else:
            self.chunker = None
    
    def process_folder(self, root_folder: str) -> List[Dict[str, Any]]:
        """
        Process all PDF documents in the folder structure.
        
        Expected structure: root_folder/company/year/documents.pdf
        
        Args:
            root_folder: Path to the root folder containing company folders
            
        Returns:
            List of dictionaries with company, year, and content data
        """
        results = []
        root_path = Path(root_folder)
        
        if not root_path.exists():
            raise FileNotFoundError(f"Folder not found: {root_folder}")
        
        # Iterate through company folders
        for company_folder in sorted(root_path.iterdir()):
            if not company_folder.is_dir():
                continue
            
            company_name = company_folder.name
            
            # Iterate through year folders
            for year_folder in sorted(company_folder.iterdir()):
                if not year_folder.is_dir():
                    continue
                
                year = year_folder.name
                
                # Process all PDF files in this year folder
                documents = self._process_year_folder(year_folder)
                
                if documents:
                    results.append({
                        "company": company_name,
                        "year": year,
                        "content": documents
                    })
        
        return results
    
    def _process_year_folder(self, year_folder: Path) -> List[Dict[str, Any]]:
        """
        Process all PDF documents in a year folder.
        
        Args:
            year_folder: Path to the year folder
            
        Returns:
            List of processed documents with their content
        """
        documents = []
        
        # Find all PDF files (including in subdirectories)
        pdf_files = list(year_folder.rglob("*.pdf"))
        
        for pdf_file in sorted(pdf_files):
            try:
                document_data = self._process_pdf(pdf_file)
                documents.append(document_data)
            except Exception as e:
                print(f"Error processing {pdf_file}: {str(e)}")
                # Continue processing other files
                continue
        
        return documents
    
    def _process_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Process a single PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary containing document metadata and structured content
        """
        # Extract text with type classification
        extracted_data = self.extractor.extract_text(str(pdf_path))
        
        # Organize content by text type
        structured_content = self._structure_content(extracted_data)
        
        # Apply semantic chunking if enabled
        if self.use_semantic_chunking and structured_content.get("body_text"):
            structured_content["semantic_chunks"] = self._apply_semantic_chunking(
                structured_content["body_text"]
            )
        
        return {
            "document_name": pdf_path.name,
            "document_path": str(pdf_path.relative_to(pdf_path.parent.parent.parent)),
            "content": structured_content
        }
    
    def _structure_content(self, extracted_data: List[tuple]) -> Dict[str, Any]:
        """
        Structure extracted text by type (titles, subtitles, body text).
        
        Args:
            extracted_data: List of (TextType, str) tuples from extractor
            
        Returns:
            Dictionary with structured content
        """
        titles = []
        subtitles = []
        body_text = []
        
        for text_type, text in extracted_data:
            if text_type == TextType.TITLE:
                titles.append(text)
            elif text_type == TextType.SUBTITLE:
                subtitles.append(text)
            elif text_type == TextType.TEXT:
                body_text.append(text)
        
        # Combine body text into a single string for semantic chunking
        full_body_text = " ".join(body_text)
        
        return {
            "titles": titles,
            "subtitles": subtitles,
            "body_text": full_body_text,
            "raw_body_sentences": body_text
        }
    
    def _apply_semantic_chunking(self, text: str) -> List[Dict[str, Any]]:
        """
        Apply semantic chunking to text.
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of chunks with metadata
        """
        if not text.strip():
            return []
        
        chunks_with_metadata = self.chunker.chunk_text_with_metadata(text)
        return chunks_with_metadata


def main():
    """
    Main entry point for the document processing script.
    """
    parser = argparse.ArgumentParser(
        description="Process PDF documents from a hierarchical folder structure and output JSON data."
    )
    parser.add_argument(
        "folder",
        type=str,
        help="Path to the root folder (e.g., 'reports/')"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output.json",
        help="Output JSON file path (default: output.json)"
    )
    parser.add_argument(
        "--no-chunking",
        action="store_true",
        help="Disable semantic chunking"
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.5,
        help="Similarity threshold for semantic chunking (0-1, default: 0.5)"
    )
    parser.add_argument(
        "--min-chunk-size",
        type=int,
        default=1,
        help="Minimum sentences per chunk (default: 1)"
    )
    parser.add_argument(
        "--max-chunk-size",
        type=int,
        default=10,
        help="Maximum sentences per chunk (default: 10)"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty print JSON output"
    )
    parser.add_argument(
        "--skip-titles",
        action="store_true",
        help="Skip extraction of titles and subtitles"
    )
    parser.add_argument(
        "--ai-extraction",
        action="store_true",
        help="Run AI-based sustainability data extraction using Ollama"
    )
    parser.add_argument(
        "--ollama-model",
        type=str,
        default="llama3",
        help="Ollama model to use for AI extraction (default: llama3)"
    )
    parser.add_argument(
        "--model-type",
        type=str,
        default="ollama",
        choices=["ollama", "openai"],
        help="Model type for AI extraction: 'ollama' or 'openai' (default: ollama)"
    )
    parser.add_argument(
        "--openai-api-key",
        type=str,
        help="OpenAI API key (optional, can also be set via OPENAI_API_KEY env var)"
    )
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = DocumentProcessor(
        use_semantic_chunking=not args.no_chunking,
        similarity_threshold=args.similarity_threshold,
        min_chunk_size=args.min_chunk_size,
        max_chunk_size=args.max_chunk_size,
        include_titles=not args.skip_titles
    )
    
    # Process folder
    print(f"Processing folder: {args.folder}")
    
    # Check if output exists and we can skip processing
    skip_processing = False
    if os.path.exists(args.output) and args.ai_extraction:
        print(f"Found existing output file: {args.output}")
        try:
            with open(args.output, 'r', encoding='utf-8') as f:
                results = json.load(f)
            if results:
                print("Skipping PDF processing and semantic chunking as output file exists.")
                skip_processing = True
        except Exception as e:
            print(f"Warning: Could not load existing output file: {e}. Proceeding with processing.")

    if not skip_processing:
        if os.path.exists(args.folder):
            if os.path.isdir(args.folder):
                results = processor.process_folder(args.folder)
            elif os.path.isfile(args.folder) and args.folder.endswith('.json'):
                print(f"Loading existing data from JSON: {args.folder}")
                with open(args.folder, 'r', encoding='utf-8') as f:
                    results = json.load(f)
            else:
                 print(f"Error: {args.folder} is not a valid directory or JSON file.")
                 return
        else:
            print(f"Error: Folder or file not found: {args.folder}")
            return
        
    # Run AI Extraction if requested
    if args.ai_extraction:
        if SustainabilityExtractor is None:
            print("Error: Could not import SustainabilityExtractor. Please install langchain and langchain-ollama.")
        else:
            print(f"Starting AI extraction using {args.model_type} model: {args.ollama_model}...")
            if args.model_type == "ollama":
                print("Note: This process requires a running Ollama instance.")
            elif args.model_type == "openai":
                if not args.openai_api_key and not os.environ.get("OPENAI_API_KEY"):
                    print("❌ Error: OpenAI API key is missing. Please set OPENAI_API_KEY in .env or pass it via --openai-api-key.")
                    return
            
            try:
                extractor = SustainabilityExtractor(
                    model_type=args.model_type,
                    model_name=args.ollama_model,
                    api_key=args.openai_api_key
                )
                results = extractor.process_data(results)
                print("✓ AI extraction complete!")
            except Exception as e:
                print(f"❌ Error during AI extraction initialization: {e}")
    
    # Save to JSON
    with open(args.output, 'w', encoding='utf-8') as f:
        if args.pretty:
            json.dump(results, f, indent=2, ensure_ascii=False)
        else:
            json.dump(results, f, ensure_ascii=False)
    
    print(f"✓ Processing complete!")
    print(f"✓ Processed {len(results)} company-year combinations")
    print(f"✓ Output saved to: {args.output}")


if __name__ == "__main__":
    main()
