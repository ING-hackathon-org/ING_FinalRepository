# Vision-AI PDF Extraction (Main Technique)

The primary ESG data extraction engine used in the ING platform. This technique uses **GPT-4o Vision** to analyze PDF pages as images, enabling accurate extraction of complex layouts, tables, and charts.

## Overview

This is the **production-ready extraction method** that processes PDF reports by:

1. **Ranking pages** by ESG relevance using keyword scoring
2. **Converting pages to images** for vision-based analysis
3. **Multi-pass extraction** with intelligent retry logic for missing fields
4. **Structured output** with Pydantic validation and CSV generation

## How It Works

### Step 1: Page Ranking Algorithm

Pages are scored based on ESG-relevant keywords:

```python
KEYWORDS = [
    "scope 1", "scope 2", "market-based", "tco2e", "ghg emissions",
    "assurance", "independent", "target", "2030", "net zero", "action plan"
]
```

Pages with higher keyword density are processed first, boosted by:
- "performance data" mentions (+5 score)
- "sustainability table" mentions (+5 score)
- "esg data" mentions (+5 score)

### Step 2: Vision-Based Extraction

PDF pages are converted to **high-resolution PNG images** (150 DPI) and sent to GPT-4o Vision:

```python
pix = doc[idx].get_pixmap(dpi=150)
b64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
```

This approach handles:
- Complex table layouts
- Multi-column text
- Charts and infographics
- Scanned documents

### Step 3: Multi-Pass Retry Logic

The system performs up to 3 extraction attempts, each scanning new pages:

| Attempt | Pages Scanned | Purpose |
|---------|---------------|---------|
| 1 | Top 10 ranked | Initial extraction |
| 2 | Pages 11-20 | Fill missing Scope 1/2 |
| 3 | Pages 21-30 | Fill missing targets |

Results from each pass are **merged intelligently**, keeping existing non-null values.

### Step 4: Data Validation & Export

Extracted data is validated using **Pydantic** schemas:

```python
class ESGData(BaseModel):
    company_name: Optional[str]
    reporting_year: int
    scope_1: EmissionValue
    scope_2_market: EmissionValue
    assurance_present: bool
    targets: List[Target]
    action_plan_summary: Optional[str]
```

Final output includes:
- Per-company JSON files
- Aggregated CSV with normalized values

## Data Processing Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   PDF Report    │────►│   Page Ranker    │────►│ Ranked Page IDs │
└─────────────────┘     │ (Keyword Scorer) │     └────────┬────────┘
                        └──────────────────┘              │
                                                          ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │  Image Renderer  │◄────│  Top N Pages    │
                        │  (150 DPI PNG)   │     └─────────────────┘
                        └────────┬─────────┘
                                 │
                                 ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Validated JSON │◄────│   GPT-4o Vision  │◄────│ Base64 Images   │
│  + CSV Output   │     │  (Multi-Pass)    │     └─────────────────┘
└─────────────────┘     └──────────────────┘
```

## Output Formats

### JSON (Per Company)
```json
{
  "company_name": "Shell",
  "reporting_year": 2022,
  "scope_1": { "value": 68000000, "unit": "tCO2e" },
  "scope_2_market": { "value": 5000000, "unit": "tCO2e" },
  "assurance_present": true,
  "targets": [
    { "target_reduction_percentage": "30%", "target_year": 2030, "base_year": 2016 }
  ],
  "action_plan_summary": "Investing $10B in renewable energy by 2030..."
}
```

### CSV (Aggregated)
| Company | Reporting_Year | Scope_1_Value | Scope_1_Unit | Scope_1_Calculated | Scope_2_Market_Value | Assurance_Present | Target_2030_Pct |
|---------|----------------|---------------|--------------|-------------------|---------------------|-------------------|-----------------|
| Shell   | 2022           | 68000000      | tCO2e        | 68000000          | 5000000             | True              | 30%             |

## Value Normalization

The system automatically converts units to base tonnes (tCO2e):

| Input | Multiplier | Example |
|-------|------------|---------|
| `million tonnes` | ×1,000,000 | 3.2 → 3,200,000 |
| `thousand tonnes` | ×1,000 | 500 → 500,000 |
| `kt` | ×1,000 | 150 → 150,000 |
| `Mt` | ×1,000,000 | 2.5 → 2,500,000 |

## Usage

### As a Class (Programmatic)
```python
from pdf_converter import ESGPDFConverter

converter = ESGPDFConverter(api_key="your-openai-key")

# Single PDF
csv_path = await converter.process_pdf("/path/to/report.pdf")

# Batch processing
csv_path = await converter.process_batch([
    "/path/to/report1.pdf",
    "/path/to/report2.pdf"
])
```

### Via FastAPI Server
```bash
# Start the server
python server.py

# Upload a PDF
curl -X POST -F "file=@report.pdf" http://localhost:8000/upload
```

## Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `api_key` | Required | OpenAI API key |
| `output_dir` | `./output` | Directory for JSON outputs |
| `max_concurrent` | 4 | Parallel API requests |
| `max_pages_per_scan` | 10 | Pages per extraction attempt |
| `max_retries` | 3 | Retry attempts for missing fields |

## Dependencies

- **PyMuPDF (fitz)**: PDF rendering and text extraction
- **OpenAI**: GPT-4o Vision API
- **Pydantic**: Data validation
- **Pandas**: CSV generation
- **tqdm**: Progress tracking

## Advantages

- ✅ **Vision Understanding**: Handles complex layouts and charts
- ✅ **Multi-Pass Extraction**: Maximizes data completeness
- ✅ **Pydantic Validation**: Ensures data integrity
- ✅ **Async Processing**: Efficient batch handling
- ✅ **Deep Search Logging**: Transparent extraction progress

## Limitations

- ⚠️ Requires OpenAI API key (cloud-based, costs apply)
- ⚠️ Image-based approach uses more tokens than text
- ⚠️ DPI setting affects accuracy vs. cost tradeoff

## License

MIT License
