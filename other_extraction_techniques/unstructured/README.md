# Unstructured PDF Extraction Technique

A Python-based ESG data extraction pipeline that uses the **Unstructured** library for high-resolution PDF parsing combined with **GPT-4o** for intelligent data extraction.

## Overview

This technique extracts Environmental, Social, and Governance (ESG) data from annual reports by:

1. **Pre-filtering** relevant pages using keyword matching
2. **High-resolution extraction** of tables and text using the Unstructured library
3. **AI-powered analysis** using OpenAI's GPT-4o to extract structured ESG metrics

## How It Works

### Step 1: Keyword-Based Page Filtering

The pipeline first performs a fast scan of all PDF pages using **PyMuPDF (fitz)** to identify ESG-relevant content:

```python
BASELINE_KEYWORDS = {
    "scope_1": ["Scope 1", "Direct GHG emissions", "Gross direct emissions"],
    "scope_2_market": ["Scope 2", "Market-based", "Indirect emissions"],
    "assurance": ["Independent assurance report", "External verification"],
    "targets": ["GHG reduction target", "Net zero ambition", "SBTi approved"],
    "action_plans": ["Climate transition plan", "Decarbonization strategy"]
}
```

This reduces processing time by only extracting relevant pages rather than the entire document.

### Step 2: High-Resolution Table Extraction

The filtered pages are processed using **Unstructured's** `partition_pdf` function with:

- **Strategy**: `hi_res` (high-resolution AI model)
- **Table Inference**: Enabled for accurate table structure detection
- **Model**: YOLOX for document element detection

```python
elements = partition_pdf(
    filename=filtered_pdf_path,
    infer_table_structure=True,
    strategy="hi_res",
    hi_res_model_name="yolox"
)
```

Tables are preserved as HTML for better structure retention, while regular text is extracted as-is.

### Step 3: GPT-4o Analysis

The extracted content is sent to **OpenAI's GPT-4o** with a structured prompt to extract:

| Field | Description |
|-------|-------------|
| `reporting_year` | Year covered by the report |
| `scope_1` | Direct GHG emissions (value + unit) |
| `scope_2_market` | Market-based indirect emissions |
| `assurance_present` | Boolean for external assurance |
| `targets` | GHG reduction targets with years |
| `action_plan_summary` | Summary of sustainability strategies |

The AI normalizes values (e.g., "3.2 million tonnes" → `3200000`) and returns structured JSON.

## Data Processing Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   PDF Report    │────►│  Keyword Filter  │────►│ Filtered Pages  │
└─────────────────┘     │   (PyMuPDF)      │     └────────┬────────┘
                        └──────────────────┘              │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  JSON Output    │◄────│    GPT-4o        │◄────│  Unstructured   │
│ (ESG Metrics)   │     │   Analysis       │     │  Hi-Res Extract │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Output Format

The pipeline generates a JSON file with the following structure:

```json
{
    "reporting_year": 2022,
    "scope_1": { "value": 482123.0, "unit": "tCO2e" },
    "scope_2_market": { "value": 123456.0, "unit": "tCO2e" },
    "assurance_present": true,
    "targets": [
        {
            "target_reduction_percentage": "30%",
            "target_year": 2030,
            "base_year": 2019
        }
    ],
    "action_plan_summary": "Investing in renewable energy..."
}
```

## Dependencies

- **PyMuPDF (fitz)**: Fast PDF text scanning
- **Unstructured**: High-resolution document parsing
- **RapidFuzz**: Fuzzy string matching for keywords
- **OpenAI**: GPT-4o API for data extraction

## Usage

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key"

# Run the extraction
python main.py
```

## Advantages

- ✅ **High Table Accuracy**: YOLOX model excels at detecting tables
- ✅ **Smart Filtering**: Only processes ESG-relevant pages
- ✅ **Structured Output**: Returns well-formatted JSON data
- ✅ **Fuzzy Matching**: Handles OCR errors and variations in keywords

## Limitations

- ⚠️ Requires OpenAI API key (cloud-based)
- ⚠️ Unstructured hi-res model can be slow for large PDFs
- ⚠️ API costs scale with document size

## License

MIT License
