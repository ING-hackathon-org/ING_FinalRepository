"""
FastAPI Server for ESG PDF Processing
=====================================
HTTP API for processing PDF reports and extracting ESG data.
"""

import os
import csv
import asyncio
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn

from pdf_converter import ESGPDFConverter

# ============================================================================
# CONFIGURATION
# ============================================================================

UPLOAD_DIR = Path("./uploads")
OUTPUT_DIR = Path("./output")
DATA_DIR = Path("../data/csv_data")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Get OpenAI API Key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ProcessResponse(BaseModel):
    """Response model for PDF processing."""
    success: bool
    csv_path: Optional[str] = None
    message: str
    processed_at: str

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="ESG PDF Processor API",
    description="API for extracting ESG data from PDF reports",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this based on your frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def cleanup_temp_file(file_path: Path):
    """Clean up temporary uploaded file."""
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        print(f"Error cleaning up {file_path}: {e}")

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat()
    )

@app.post("/process-pdf", response_model=ProcessResponse)
async def process_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to process")
):
    """
    Process a single PDF file and extract ESG data.
    
    Args:
        file: Uploaded PDF file
        
    Returns:
        ProcessResponse with CSV path and status
    """
    # Validate API key
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
        )
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )
    
    # Save uploaded file temporarily
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_filename = f"{timestamp}_{file.filename}"
    temp_path = UPLOAD_DIR / temp_filename
    
    try:
        # Write uploaded file to disk
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Initialize converter
        converter = ESGPDFConverter(
            api_key=OPENAI_API_KEY,
            output_dir=str(OUTPUT_DIR)
        )
        
        # Process PDF
        csv_path = await converter.process_pdf(str(temp_path))
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_temp_file, temp_path)
        
        return ProcessResponse(
            success=True,
            csv_path=csv_path,
            message=f"Successfully processed {file.filename}",
            processed_at=datetime.now().isoformat()
        )
        
    except FileNotFoundError as e:
        background_tasks.add_task(cleanup_temp_file, temp_path)
        raise HTTPException(status_code=404, detail=str(e))
    
    except Exception as e:
        background_tasks.add_task(cleanup_temp_file, temp_path)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(e)}"
        )

@app.post("/process-batch", response_model=ProcessResponse)
async def process_batch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="Multiple PDF files to process")
):
    """
    Process multiple PDF files and extract ESG data.
    
    Args:
        files: List of uploaded PDF files
        
    Returns:
        ProcessResponse with CSV path and status
    """
    # Validate API key
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
        )
    
    # Validate all files
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF files are allowed. Invalid file: {file.filename}"
            )
    
    temp_paths = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        # Save all uploaded files
        for idx, file in enumerate(files):
            temp_filename = f"{timestamp}_{idx}_{file.filename}"
            temp_path = UPLOAD_DIR / temp_filename
            
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            temp_paths.append(temp_path)
        
        # Initialize converter
        converter = ESGPDFConverter(
            api_key=OPENAI_API_KEY,
            output_dir=str(OUTPUT_DIR)
        )
        
        # Process all PDFs
        csv_path = await converter.process_batch([str(p) for p in temp_paths])
        
        # Schedule cleanup for all temp files
        for temp_path in temp_paths:
            background_tasks.add_task(cleanup_temp_file, temp_path)
        
        return ProcessResponse(
            success=True,
            csv_path=csv_path,
            message=f"Successfully processed {len(files)} PDF files",
            processed_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        # Clean up all temp files on error
        for temp_path in temp_paths:
            background_tasks.add_task(cleanup_temp_file, temp_path)
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDFs: {str(e)}"
        )

@app.get("/download-csv/{filename}")
async def download_csv(filename: str):
    """
    Download a generated CSV file.
    
    Args:
        filename: Name of the CSV file
        
    Returns:
        FileResponse with the CSV file
    """
    csv_path = OUTPUT_DIR / filename
    
    if not csv_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"CSV file not found: {filename}"
        )
    
    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename=filename
    )

# ============================================================================
# DATA API ENDPOINTS (For Frontend)
# ============================================================================

# In-memory storage for decisions (would use database in production)
company_decisions: Dict[str, str] = {}

def load_csv_data() -> List[Dict[str, Any]]:
    """Load CSV data from file and return as list of dictionaries."""
    csv_path = DATA_DIR / "data.csv"
    
    if not csv_path.exists():
        return []
    
    data = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert numeric fields
            processed_row = {}
            for key, value in row.items():
                if key in ['Scope_1_Value', 'Scope_2_Market_Value', 'Target_Base_Year']:
                    try:
                        processed_row[key] = float(value) if value else None
                    except ValueError:
                        processed_row[key] = None
                elif key == 'Reporting_Year':
                    try:
                        processed_row[key] = int(value) if value else None
                    except ValueError:
                        processed_row[key] = None
                elif key == 'Assurance_Present':
                    processed_row[key] = value.lower() == 'true' if value else False
                else:
                    processed_row[key] = value if value else None
            data.append(processed_row)
    
    return data

def calculate_risk(company_data: List[Dict]) -> str:
    """
    Calculate risk level for a company based on emissions trend.
    Returns: 'high' (red), 'medium' (yellow), 'low' (green), 'insufficient' (grey)
    """
    if len(company_data) < 3:
        return 'insufficient'
    
    # Sort by year
    sorted_data = sorted(company_data, key=lambda x: x.get('Reporting_Year', 0))
    
    # Check for missing data
    scope_1_values = [d.get('Scope_1_Value') for d in sorted_data if d.get('Scope_1_Value') is not None]
    
    if len(scope_1_values) < 2:
        return 'insufficient'
    
    # Calculate trend (simple: compare first and last)
    first_value = scope_1_values[0]
    last_value = scope_1_values[-1]
    
    if first_value == 0:
        return 'insufficient'
    
    change_pct = ((last_value - first_value) / first_value) * 100
    
    if change_pct > 10:
        return 'high'  # Emissions increasing significantly
    elif change_pct > 0:
        return 'medium'  # Emissions slightly increasing
    else:
        return 'low'  # Emissions decreasing

@app.get("/api/data")
async def get_all_data():
    """Return all ESG data as JSON."""
    try:
        data = load_csv_data()
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading data: {str(e)}")

@app.get("/api/companies")
async def get_companies():
    """Return list of unique companies with aggregated metrics."""
    try:
        data = load_csv_data()
        
        # Group by company
        companies_dict: Dict[str, List[Dict]] = {}
        for row in data:
            company = row.get('Company')
            if company:
                if company not in companies_dict:
                    companies_dict[company] = []
                companies_dict[company].append(row)
        
        # Build company summaries
        companies = []
        for name, company_data in companies_dict.items():
            years = [d.get('Reporting_Year') for d in company_data if d.get('Reporting_Year')]
            
            # Get latest data
            sorted_data = sorted(company_data, key=lambda x: x.get('Reporting_Year', 0), reverse=True)
            latest = sorted_data[0] if sorted_data else {}
            
            companies.append({
                "name": name,
                "years_available": sorted(years),
                "years_count": len(years),
                "risk_level": calculate_risk(company_data),
                "decision": company_decisions.get(name),
                "latest_scope_1": latest.get('Scope_1_Value'),
                "latest_scope_1_unit": latest.get('Scope_1_Unit'),
                "latest_scope_2": latest.get('Scope_2_Market_Value'),
                "latest_scope_2_unit": latest.get('Scope_2_Market_Unit'),
                "has_assurance": latest.get('Assurance_Present', False),
                "target_2030": latest.get('Target_2030_Pct'),
                "action_plan": latest.get('Action_Plan_Summary'),
                "data": company_data  # Include all yearly data
            })
        
        return {"success": True, "companies": companies, "count": len(companies)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading companies: {str(e)}")

@app.get("/api/company/{company_name}")
async def get_company(company_name: str):
    """Return data for a specific company."""
    try:
        data = load_csv_data()
        company_data = [row for row in data if row.get('Company') == company_name]
        
        if not company_data:
            raise HTTPException(status_code=404, detail=f"Company not found: {company_name}")
        
        return {
            "success": True,
            "company": company_name,
            "risk_level": calculate_risk(company_data),
            "decision": company_decisions.get(company_name),
            "data": company_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading company: {str(e)}")

@app.post("/api/decisions")
async def save_decision(company: str, decision: str):
    """Save a decision for a company."""
    if decision not in ['cooperate', 'suspend', None, '']:
        raise HTTPException(status_code=400, detail="Decision must be 'cooperate', 'suspend', or empty")
    
    if decision:
        company_decisions[company] = decision
    elif company in company_decisions:
        del company_decisions[company]
    
    return {"success": True, "company": company, "decision": decision}

@app.get("/api/decisions")
async def get_decisions():
    """Get all company decisions."""
    return {"success": True, "decisions": company_decisions}

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Check for API key
    if not OPENAI_API_KEY:
        print("⚠️  WARNING: OPENAI_API_KEY environment variable not set!")
        print("   Set it in your .env file or export it before running the server.")
    
    # Run server
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
