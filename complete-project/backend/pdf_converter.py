"""
ING ESG Data Extraction - PDF Converter Class
==============================================
Reusable class for converting PDF reports to CSV with ESG data extraction.
"""

import os
import json
import base64
import asyncio
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

import fitz  # PyMuPDF
import pandas as pd
from pydantic import BaseModel, Field, ValidationError
from openai import AsyncOpenAI
from tqdm.asyncio import tqdm

# ============================================================================
# DATA SCHEMA (PYDANTIC)
# ============================================================================

class EmissionValue(BaseModel):
    value: Optional[float] = Field(None, description="Numerical value (e.g. 482123). If 'million', convert to full number.")
    unit: Optional[str] = Field(None, description="e.g. tCO2e, tonnes, million tonnes")

class Target(BaseModel):
    target_reduction_percentage: Optional[str] = Field(None, description="e.g. '30%' or 'Net Zero'")
    target_year: int = Field(..., description="Year the target applies to (e.g. 2030)")
    base_year: Optional[int] = Field(None, description="Base year for reduction (e.g. 2019)")

class ESGData(BaseModel):
    company_name: Optional[str] = Field(None, description="Name of the company that published this report")
    reporting_year: int = Field(..., description="The year covered by the report (e.g. 2023)")
    scope_1: EmissionValue = Field(default_factory=EmissionValue, description="Direct GHG emissions")
    scope_2_market: EmissionValue = Field(default_factory=EmissionValue, description="Indirect GHG emissions (Market-Based)")
    assurance_present: bool = Field(..., description="Is external assurance present? (True/False)")
    targets: List[Target] = Field(default_factory=list, description="List of GHG reduction targets")
    action_plan_summary: Optional[str] = Field(None, description="Free-text summary of planned actions/strategies.")

# ============================================================================
# PDF ENGINE
# ============================================================================

class PDFProcessor:
    KEYWORDS = ["scope 1", "scope 2", "market-based", "tco2e", "ghg emissions", 
                "assurance", "independent", "target", "2030", "net zero", "action plan", "strategy"]
    
    @staticmethod
    def extract_metadata(pdf_path: Path) -> tuple:
        """
        Extracts Company and Year based on strict folder structure:
        .../reports/{Company}/{Year}/{file.pdf}
        """
        parts = pdf_path.parts
        
        # Default fallback
        year = 2023
        company = pdf_path.stem.split('_')[0]

        try:
            # Look for the 'reports' folder and grab the next two levels
            if 'reports' in parts:
                idx = parts.index('reports')
                # Ensure structure exists: reports/Company/Year/File
                if len(parts) > idx + 2:
                    company = parts[idx + 1]  # Folder after 'reports'
                    year_str = parts[idx + 2] # Folder after 'Company'
                    
                    if re.match(r"202[0-9]", year_str):
                        year = int(year_str)
                    
                    return company, year
        except Exception as e:
            logging.warning(f"Metadata extraction fallback for {pdf_path}: {e}")

        # Fallback Logic if folder structure is messy
        filename = pdf_path.name
        year_match = re.search(r"202[0-9]", filename)
        if year_match:
            year = int(year_match.group(0))
        
        return company, year

    @staticmethod
    def rank_pages(pdf_path: Path) -> List[int]:
        """Scans PDF and returns ALL page indices sorted by relevance."""
        try:
            doc = fitz.open(pdf_path)
            scores = []
            
            for i, page in enumerate(doc):
                text = page.get_text().lower()
                score = sum(1 for kw in PDFProcessor.KEYWORDS if kw in text)
                # Boost if table-like keywords found
                if "performance data" in text or "sustainability table" in text or "esg data" in text:
                    score += 5
                scores.append((i, score))
            
            doc.close()
            # Sort by score descending
            scores.sort(key=lambda x: x[1], reverse=True)
            return [x[0] for x in scores]
        except Exception as e:
            logging.error(f"PDF Ranking Error {pdf_path.name}: {e}")
            return []

    @staticmethod
    def get_images_for_indices(pdf_path: Path, indices: List[int]) -> List[dict]:
        """Fetches base64 images for specific page indices."""
        try:
            doc = fitz.open(pdf_path)
            images = []
            for idx in indices:
                # Check valid index
                if idx >= len(doc): continue
                
                pix = doc[idx].get_pixmap(dpi=150)
                b64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
                
                # STRICT OPENAI FORMAT
                images.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{b64}",
                        "detail": "high"
                    }
                })
            doc.close()
            return images
        except Exception as e:
            logging.error(f"Image Fetch Error {pdf_path.name}: {e}")
            return []

# ============================================================================
# SYSTEM PROMPT
# ============================================================================

SYSTEM_PROMPT = """
You are an expert ESG Data Analyst. Extract specific sustainability metrics from the annual report.

TASK:
Extract ONLY the following fields:
1. **Company Name**: The name of the company that published this report.
2. **Reporting Year**: The year covered by the report (e.g. 2023).
3. **Scope 1 Emissions**: Direct GHG emissions. Extract value and unit. (e.g. 482123, tCO2e).
4. **Scope 2 Emissions (Market-Based)**: Indirect GHG emissions. Extract value and unit. (e.g. 923832, tCO2e).
5. **Assurance**: Boolean. True if "Limited" or "Reasonable" external assurance is explicitly stated. False otherwise.
6. **Targets**: GHG reduction targets. Extract target value (e.g. "30% reduction") and year (e.g. 2030).
7. **Action Plans**: A summary of planned actions/strategies (e.g. "Investing in renewable energy...").

RULES:
- Normalize values: If text says "3.2 million tonnes", value should be 3200000.
- IGNORE Location-Based Scope 2.
- IGNORE Scope 3.
- For company name, extract the actual company/organization name from the report cover or header.

OUTPUT FORMAT:
Return strictly valid JSON matching exactly this schema:
{
  "company_name": <str>,
  "reporting_year": <int>,
  "scope_1": { "value": <float>, "unit": <str> },
  "scope_2_market": { "value": <float>, "unit": <str> },
  "assurance_present": <bool>,
  "targets": [ 
      { "target_reduction_percentage": <str>, "target_year": <int>, "base_year": <int> } 
  ],
  "action_plan_summary": <str>
}
"""

# ============================================================================
# ESG PDF CONVERTER CLASS
# ============================================================================

class ESGPDFConverter:
    """
    Class for converting PDF reports to CSV with ESG data extraction.
    
    Usage:
        converter = ESGPDFConverter(api_key="your-openai-key")
        csv_path = await converter.process_pdf("/path/to/report.pdf")
    """
    
    def __init__(self, api_key: str, output_dir: str = None, 
                 max_concurrent: int = 4, max_pages_per_scan: int = 10, max_retries: int = 3):
        """
        Initialize the PDF converter.
        
        Args:
            api_key: OpenAI API key
            output_dir: Directory for output files (default: ./output)
            max_concurrent: Maximum concurrent OpenAI requests
            max_pages_per_scan: Pages to scan per attempt
            max_retries: Maximum retry attempts for missing data
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.output_dir = Path(output_dir) if output_dir else Path("./output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_concurrent = max_concurrent
        self.max_pages_per_scan = max_pages_per_scan
        self.max_retries = max_retries
        
        self.sem = asyncio.Semaphore(max_concurrent)
        self.results = []
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%H:%M:%S",
            handlers=[
                logging.FileHandler(self.output_dir / "pipeline.log", mode='a'),
                logging.StreamHandler()
            ]
        )
        logging.getLogger("httpx").setLevel(logging.WARNING)
        self.logger = logging.getLogger("ESGConverter")
    
    def merge_results(self, existing: Dict, new: Dict) -> Dict:
        """Smart merge: keep existing non-null values, overwrite nulls with new non-nulls."""
        merged = existing.copy()
        for k, v in new.items():
            if k not in merged or not merged[k]:
                merged[k] = v
            elif isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                # Nested merge (e.g. scope_1: {value, unit})
                merged[k] = self.merge_results(merged[k], v)
            elif isinstance(v, list) and k in merged and isinstance(merged[k], list):
                 # Append lists (targets) if unique? or just extend
                 # For simplicity, if existing targets is empty, take new.
                 if not merged[k]:
                     merged[k] = v
        return merged

    def check_missing(self, data: Dict) -> List[str]:
        """Returns list of critical missing fields."""
        missing = []
        if not data.get('company_name'): missing.append("Company Name")
        if not data.get('scope_1', {}).get('value'): missing.append("Scope 1")
        if not data.get('scope_2_market', {}).get('value'): missing.append("Scope 2")
        if not data.get('targets'): missing.append("Targets")
        return missing

    async def _extract_from_pdf(self, pdf_path: Path) -> Dict:
        """Extract ESG data from a single PDF."""
        async with self.sem:
            # Fallback metadata from folder (may be overwritten by AI extraction)
            fallback_company, fallback_year = PDFProcessor.extract_metadata(pdf_path)
            
            # Rank all pages once
            ranked_indices = PDFProcessor.rank_pages(pdf_path)
            
            final_data = {}
            current_missing = ["Company Name", "Scope 1", "Scope 2", "Targets"] 
            
            for attempt in range(self.max_retries):
                # Pagination logic
                start = attempt * self.max_pages_per_scan
                end = start + self.max_pages_per_scan
                batch_indices = ranked_indices[start:end]
                
                if not batch_indices:
                    break # No more pages
                
                # Fetch Images
                images = PDFProcessor.get_images_for_indices(pdf_path, batch_indices)
                if not images: continue
                
                # Interactive log for Deep Search
                if attempt > 0:
                    tqdm.write(f"🔍 Deep Search {company} {year} (Attempt {attempt+1}): Found {list(final_data.keys())}. Missing {current_missing}. Scanning next {len(batch_indices)} pages...")
                
                try:
                    # Construct Prompt
                    user_content = [{"type": "text", "text": f"Analyze this sustainability/annual report and extract ESG data."}]
                    if attempt > 0:
                         user_content[0]["text"] += f" We previously found some data but are MISSING: {current_missing}. Please check these new pages specifically for these missing fields."
                    
                    user_content.extend(images)

                    # OpenAI Call
                    response = await self.client.chat.completions.create(
                        model="gpt-4o-2024-08-06",
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_content}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.0
                    )
                    
                    # Parse
                    raw_content = response.choices[0].message.content
                    new_data = json.loads(raw_content)
                    
                    # Merge
                    if not final_data:
                        final_data = new_data
                    else:
                        final_data = self.merge_results(final_data, new_data)
                    
                    # Check what's still missing
                    current_missing = self.check_missing(final_data)
                    
                    # Use AI-extracted company name, fallback to folder-based
                    company = final_data.get('company_name') or fallback_company
                    year = final_data.get('reporting_year') or fallback_year
                    
                    if not current_missing:
                        if attempt > 0:
                             tqdm.write(f"✅ Deep Search {company} {year}: All fields found!")
                        break # Success
                
                except Exception as e:
                    company = final_data.get('company_name') or fallback_company
                    year = final_data.get('reporting_year') or fallback_year
                    self.logger.error(f"Attempt {attempt+1} failed for {company} {year}: {e}")
            
            # Final Validation
            try:
                # Add Metadata
                final_data['meta_data'] = {
                    "company_name": company, 
                    "reporting_year": year, 
                    "filename": pdf_path.name,
                    "timestamp": datetime.now().isoformat()
                }

                # Validate with Pydantic
                report = ESGData(**final_data)
                
                # Save
                report_dict = report.model_dump()
                report_dict['company_name'] = company
                
                company_out_dir = self.output_dir / company
                company_out_dir.mkdir(exist_ok=True)
                out_path = company_out_dir / f"{company}_{year}.json"
                
                with open(out_path, "w") as f:
                    json.dump(report_dict, f, indent=2)
                
                return report_dict

            except ValidationError as ve:
                self.logger.error(f"Validation Error {company} {year}: {ve}")
                return None
            except Exception as e:
                self.logger.error(f"Pipeline Error {company} {year}: {e}")
                return None

    def normalize_value(self, val, unit):
        """Helper to normalize to tonnes (tCO2e)."""
        if not val or not unit: return val
        
        try:
            clean_val = float(str(val).replace(",", ""))
            unit_str = str(unit).lower().strip()
            
            if any(x in unit_str for x in ['million', 'mmt', 'megatonnes']):
                return clean_val * 1_000_000
            
            if re.search(r'\bmt\b', unit_str):
                 return clean_val * 1_000_000

            if any(x in unit_str for x in ['thousand', 'kt']):
                return clean_val * 1_000
                
            return clean_val
        except:
            return val

    def _generate_csv(self, results: List[Dict]) -> Path:
        """Generate CSV from extraction results."""
        rows = []
        for r in results:
            # Format data for CSV
            t2030 = next((t for t in r.get('targets', []) if t['target_year'] == 2030), None)
            
            # Determine flags
            flags = []
            s1 = r.get('scope_1', {}).get('value')
            if s1 and s1 > 50_000_000:
                flags.append("Warning: High S1")

            # Normalization
            s1_val = r.get('scope_1', {}).get('value')
            s1_unit = r.get('scope_1', {}).get('unit')
            s2_val = r.get('scope_2_market', {}).get('value')
            s2_unit = r.get('scope_2_market', {}).get('unit')
            
            s1_calc = self.normalize_value(s1_val, s1_unit)
            s2_calc = self.normalize_value(s2_val, s2_unit)

            rows.append({
                "Company": r.get('company_name'),
                "Reporting_Year": r.get('reporting_year'),
                "Scope_1_Value": s1_val,
                "Scope_1_Unit": s1_unit,
                "Scope_1_Calculated": s1_calc,
                "Scope_2_Market_Value": s2_val,
                "Scope_2_Market_Unit": s2_unit,
                "Scope_2_Calculated": s2_calc,
                "Assurance_Present": r.get('assurance_present'),
                "Target_2030_Pct": t2030.get('target_reduction_percentage') if t2030 else None,
                "Target_Base_Year": t2030.get('base_year') if t2030 else None,
                "Action_Plan_Summary": r.get('action_plan_summary'),
                "Flags": "; ".join(flags)
            })
        
        df = pd.DataFrame(rows)
        # Sort by Company and Year
        df = df.sort_values(by=["Company", "Reporting_Year"])
        
        # Write to the data/csv_data folder that the API reads from
        data_csv_dir = Path(__file__).parent.parent / "data" / "csv_data"
        data_csv_dir.mkdir(parents=True, exist_ok=True)
        csv_path = data_csv_dir / "data.csv"
        df.to_csv(csv_path, index=False)
        self.logger.info(f"CSV exported to: {csv_path}")
        return csv_path
    
    async def process_pdf(self, pdf_path: str) -> str:
        """
        Process a single PDF and return the CSV path.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            str: Path to the generated CSV file
        """
        pdf_file = Path(pdf_path)
        
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        # Extract data
        result = await self._extract_from_pdf(pdf_file)
        
        if result:
            self.results = [result]
            csv_path = self._generate_csv(self.results)
            return str(csv_path)
        else:
            raise Exception(f"Failed to extract data from {pdf_path}")
    
    async def process_batch(self, pdf_paths: List[str]) -> str:
        """
        Process multiple PDFs and return the CSV path.
        
        Args:
            pdf_paths: List of PDF file paths
            
        Returns:
            str: Path to the generated CSV file
        """
        pdf_files = [Path(p) for p in pdf_paths]
        
        # Validate all files exist
        for pdf_file in pdf_files:
            if not pdf_file.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_file}")
        
        # Process all PDFs
        tasks = [self._extract_from_pdf(p) for p in pdf_files]
        
        self.results = []
        for f in tqdm.as_completed(tasks, total=len(tasks), desc="Processing Reports"):
            res = await f
            if res:
                self.results.append(res)
        
        # Generate CSV
        if self.results:
            csv_path = self._generate_csv(self.results)
            return str(csv_path)
        else:
            raise Exception("Failed to extract data from any PDFs")
