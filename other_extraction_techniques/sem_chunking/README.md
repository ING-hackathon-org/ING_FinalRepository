# PDF Document Extraction and Semantic Chunking

A Python tool for extracting and semantically chunking text from PDF documents organized in a hierarchical folder structure.

## Features

- **PDF Text Extraction**: Extracts text from PDFs with classification (titles, subtitles, body text)
- **Semantic Chunking**: Intelligently splits text into coherent chunks based on semantic similarity
- **AI-Powered Data Extraction**: **(New)** Uses LLMs (via Ollama) to extract structured sustainability data
- **Hierarchical Processing**: Processes folder structures organized by company and year
- **JSON Output**: Generates structured JSON data with all extracted information

## How It Works

This technique uses **semantic similarity** to intelligently split documents into coherent chunks, rather than using fixed-size or page-based splitting.

### Step 1: PDF Text Extraction (`extractor.py`)

Text is extracted from PDFs using **PyMuPDF** with classification based on font properties:

| Category | Detection Method |
|----------|------------------|
| **Titles** | Font size ≥ 1.3× average or bold + large |
| **Subtitles** | Font size ≥ 1.15× average or bold |
| **Body Text** | Regular font size |

### Step 2: Sentence Splitting (`semantic_chunker.py`)

Text is split into sentences using regex patterns:
```python
sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\n+'
```

### Step 3: Semantic Embedding (`all-MiniLM-L6-v2`)

Each sentence is converted to a 384-dimensional vector using **Sentence Transformers**:
```python
embeddings = model.encode(sentences, convert_to_numpy=True)
```

### Step 4: Boundary Detection

Chunk boundaries are created where **cosine similarity** between consecutive sentences drops below a threshold:

```
Sim(S₁, S₂) = cos(embed(S₁), embed(S₂))
```

If `Sim(Sᵢ, Sᵢ₊₁) < threshold` → Create new chunk boundary

### Step 5: AI Data Extraction (Optional)

Each semantic chunk is processed by an LLM (Ollama or OpenAI) to extract:
- Emission values and units
- Emission sources (Scope 1, 2)
- Assurance status
- Relevant sustainability information

## Data Processing Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   PDF Report    │────►│  Text Extractor  │────►│  Titles + Body  │
└─────────────────┘     │   (PyMuPDF)      │     └────────┬────────┘
                        └──────────────────┘              │
                                                          ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │   Sentence       │◄────│  Raw Body Text  │
                        │   Tokenizer      │     └─────────────────┘
                        └────────┬─────────┘
                                 │
                                 ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Semantic Chunks │◄────│  Embedding +     │◄────│   Sentence      │
│ (with metadata) │     │  Boundary Detect │     │   Embeddings    │
└────────┬────────┘     └──────────────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  AI Extracted   │◄────│  LLM Analysis    │
│  ESG Metrics    │     │  (Ollama/OpenAI) │
└─────────────────┘     └──────────────────┘
```

## Advantages

- ✅ **Context-Aware**: Chunks maintain semantic coherence
- ✅ **Flexible LLM Support**: Works with local (Ollama) or cloud (OpenAI) models
- ✅ **Configurable**: Tunable similarity thresholds and chunk sizes
- ✅ **Local-First**: Can run entirely offline with Ollama

## Limitations

- ⚠️ Embedding model requires GPU for faster processing
- ⚠️ Small chunks may lose document-wide context
- ⚠️ Threshold tuning required per document type

## Installation

### Option 1: Using Conda (Recommended)

```bash
# Create and activate the conda environment
conda env create -f environment.yml
conda activate pdf-semantic-chunking
```

### Option 2: Using pip

```bash
pip install -r requirements.txt
```

## Folder Structure

The script expects the following folder structure:

```
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
```

## Usage

### Basic Usage

```bash
python main.py reports/
```

This will process all PDFs in the `reports/` folder and save the output to `output.json`.

### Advanced Options

```bash
# Specify custom output file
python main.py reports/ -o results.json

# Pretty print JSON output
python main.py reports/ --pretty

# Disable semantic chunking
python main.py reports/ --no-chunking

# Adjust semantic chunking parameters
python main.py reports/ --similarity-threshold 0.6 --min-chunk-size 2 --max-chunk-size 8

# Run AI-based sustainability data extraction (requires Ollama running)
python main.py reports/ --ai-extraction --ollama-model llama3

# Skip title/subtitle extraction (useful for cleaner AI input)
python main.py reports/ --skip-titles

# Note: If output.json already exists, the script will skip PDF processing/chunking 
# and load existing data to run AI extraction. This is useful for re-running 
# AI extraction with different models or prompts without re-parsing PDFs.
```

### Command Line Arguments

- `folder`: Path to the root folder containing company/year subfolders (required)
- `-o, --output`: Output JSON file path (default: `output.json`)
- `--no-chunking`: Disable semantic chunking
- `--similarity-threshold`: Similarity threshold for chunking (0-1, default: 0.5)
- `--min-chunk-size`: Minimum sentences per chunk (default: 1)
- `--max-chunk-size`: Maximum sentences per chunk (default: 10)
- `--pretty`: Pretty print JSON output with indentation
- `--ai-extraction`: Enable AI-based data extraction using Ollama
- `--ollama-model`: Specify the Ollama model to use (default: `llama3`)
- `--skip-titles`: Skip extraction of titles and subtitles

### AI Extraction (Optional)
To enable AI-based sustainability data extraction:

#### Option 1: Using Ollama (Local)
1. Install [Ollama](https://ollama.com/)
2. Pull the Llama 3 model: `ollama pull llama3`
3. Ensure Ollama is running (`ollama serve`)
4. In `run.sh`, set:
   ```bash
   AI_EXTRACTION="--ai-extraction"
   MODEL_TYPE="ollama"
   OLLAMA_MODEL="llama3"
   ```

#### Option 2: Using OpenAI (Cloud)
1. Obtain an OpenAI API key.
2. Create a `.env` file in the project root:
   ```bash
   OPENAI_API_KEY=your_api_key_here
   ```
3. In `run.sh`, set:
   ```bash
   AI_EXTRACTION="--ai-extraction"
   MODEL_TYPE="openai"
   OLLAMA_MODEL="gpt-4o" # or gpt-3.5-turbo, etc.
   ```
   Note: `OLLAMA_MODEL` variable is used for both Ollama and OpenAI model names.

## Output Format

The script generates JSON data in the following format:

```json
[
  {
    "company": "company_name_1",
    "year": "2023",
    "content": [
      {
        "document_name": "document1.pdf",
        "document_path": "company_name_1/2023/document1.pdf",
        "content": {
          "titles": ["Main Title", "Chapter 1"],
          "subtitles": ["Section 1.1", "Section 1.2"],
          "body_text": "Full body text as a single string...",
          "raw_body_sentences": ["Sentence 1.", "Sentence 2."],
          "semantic_chunks": [
            {
              "text": "Chunk 1 text...",
              "start_sentence": 0,
              "end_sentence": 3,
              "num_sentences": 3
            }
          ],
          "ai_extracted_data": [
            {
              "chunk_index": 0,
              "extraction": {
                "emission_value": 100.5,
                "emission_unit": "metric tons CO2e",
                "emission_sources": ["Scope 1", "Natural Gas"],
                "assurance": true,
                "relevant_info": "Emissions increased due to production growth."
              }
            }
          ]
        }
      }
    ]
  }
]
```

## Components

### 1. Extractor (`extractor.py`)

Extracts text from PDFs and classifies it into:
- **Titles**: Large font size or bold headings
- **Subtitles**: Medium font size or bold text
- **Body Text**: Regular text content

### 2. SemanticChunker (`semantic_chunker.py`)

Uses sentence embeddings to split text into semantically coherent chunks:
- Encodes sentences using transformer models
- Calculates cosine similarity between consecutive sentences
- Creates chunk boundaries where similarity drops
- Respects min/max chunk size constraints

### 3. DocumentProcessor (`main.py`)

Orchestrates the entire pipeline:
- Traverses folder structure
- Processes all PDFs
- Applies extraction and chunking
- Generates structured JSON output

### 4. SustainabilityExtractor (`ai_extractor.py`)

Uses LangChain and Ollama to extract structured sustainability metrics from text chunks:
- **Emission Data**: Values, units, and sources
- **Assurance**: Checks for external verification
- **Category Optimization**: Reuses previously identified emission source categories to maintain consistency across the dataset.


## Example

```python
from main import DocumentProcessor

# Initialize processor
processor = DocumentProcessor(
    use_semantic_chunking=True,
    similarity_threshold=0.5,
    min_chunk_size=2,
    max_chunk_size=8
)

# Process folder
results = processor.process_folder("reports/")

# Save to JSON
import json
with open("output.json", "w") as f:
    json.dump(results, f, indent=2)
```

## Dependencies

- **PyMuPDF**: PDF text extraction
- **sentence-transformers**: Semantic embeddings
- **numpy**: Numerical operations

## License

MIT License
