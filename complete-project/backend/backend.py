"""
ING ESG Data Extraction Pipeline
================================
CLI wrapper for the ESGPDFConverter class.
Usage: python backend.py
"""

import os
import asyncio
import getpass
from pathlib import Path
from dotenv import load_dotenv

from pdf_converter import ESGPDFConverter

# Load environment variables
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
INPUT_DIR = Path("./data/reports")  # Adjust to your folder structure
OUTPUT_DIR = Path("./output")

async def main():
    """Main CLI execution."""
    # Get API Key
    api_key = OPENAI_API_KEY
    if not api_key:
        print("Secure Input: OpenAI API Key not found in environment.")
        try:
            api_key = getpass.getpass("Please paste your key (starts with sk-): ").strip()
        except:
            pass
        
        if not api_key:
            print("Hidden input failed. Trying visible input...")
            try:
                api_key = input("Enter Key (visible): ").strip()
            except:
                pass
    
    if not api_key:
        print("❌ No API key provided. Exiting.")
        return

    # Find all PDF files
    pdf_files = list(INPUT_DIR.rglob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDFs found in {INPUT_DIR}")
        print(f"   Please place your PDF files in the reports directory.")
        return

    print(f"✅ Found {len(pdf_files)} PDF files")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print("-" * 60)
    
    # Initialize converter
    converter = ESGPDFConverter(
        api_key=api_key,
        output_dir=str(OUTPUT_DIR),
        max_concurrent=4,
        max_pages_per_scan=10,
        max_retries=3
    )
    
    # Process batch
    try:
        csv_path = await converter.process_batch([str(p) for p in pdf_files])
        print("-" * 60)
        print(f"✅ Pipeline Complete!")
        print(f"📊 CSV exported to: {csv_path}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())