import os
import json
import fitz
from openai import OpenAI
from rapidfuzz import fuzz
from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Table


BASELINE_KEYWORDS = {
  "scope_1": ["Scope 1", "Direct GHG emissions", "Gross direct emissions", "tCO2e"],
  "scope_2_market": ["Scope 2", "Market-based", "Indirect emissions market-based"],
  "assurance": ["Independent assurance report", "External verification", "Limited assurance", "Independent Accountant"],
  "targets": ["GHG reduction target", "Net zero ambition", "SBTi approved"],
  "action_plans": ["Climate transition plan", "Decarbonization strategy", "Renewable energy investment"]
}

ALL_ESG_KEYWORDS = set()
for category, keys in BASELINE_KEYWORDS.items():
    for k in keys:
        ALL_ESG_KEYWORDS.add(k.lower())

ALL_ESG_KEYWORDS.add("data appendix")
ALL_ESG_KEYWORDS.add("environmental update")
ALL_ESG_KEYWORDS.add("performance data")

api_key = "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"
client = OpenAI(api_key=api_key)

pdf_path = r"data/annual_report_shell_2022.pdf" 

def make_dir(path):
    name = os.path.splitext(os.path.basename(path))[0]
    folder = f"output_{name}"
    if not os.path.exists(folder): os.makedirs(folder)
    return folder

output_folder = make_dir(pdf_path)

def filter_relevant_pages_fast(pdf_path):
    print(f"Scanning {pdf_path} using PyMuPDF (Fast Mode)...")
    
    doc = fitz.open(pdf_path)
    relevant_pages = set()
    
    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        text = page.get_text("text").lower() 
        
        if not text: 
            continue

        for keyword in ALL_ESG_KEYWORDS:
            if keyword in text:
                if fuzz.partial_ratio(keyword, text) > 85:
                    relevant_pages.add(page_index + 1)

                    if "data" in keyword or "appendix" in keyword:
                        relevant_pages.add(page_index + 2)
                    break
    
    doc.close()
    sorted_pages = sorted(list(relevant_pages))
    print(f"Found relevant pages: {sorted_pages}")
    return sorted_pages


def create_filtered_pdf(pdf_path, page_nums, output_folder):
    if not page_nums:
        print("No relevant pages found. Using full doc.")
        return pdf_path
        
    doc = fitz.open(pdf_path)
    nuovo_doc = fitz.open()
    
    output_file_path = os.path.join(output_folder, "filtered_report.pdf")
    if os.path.exists(output_file_path):
        try: os.remove(output_file_path)
        except: pass

    max_pages = doc.page_count
    valid_pages = [p for p in page_nums if 1 <= p <= max_pages]

    try:
        nuovo_doc.select([p-1 for p in valid_pages]) 
        nuovo_doc.save(output_file_path, garbage=4, deflate=True, clean=True)
    except Exception as e:
        print(f"Fallback to image conversion due to PDF error: {e}")
        nuovo_doc.close()
        nuovo_doc = fitz.open()
        for p_num in valid_pages:
            page = doc.load_page(p_num - 1)
            pix = page.get_pixmap(dpi=150)
            pdf_bytes = pix.pdfocr_tobytes() if hasattr(pix, "pdfocr_tobytes") else pix.pdf_bytes()
            img_doc = fitz.open("pdf", pdf_bytes)
            nuovo_doc.insert_pdf(img_doc)
        nuovo_doc.save(output_file_path)

    nuovo_doc.close()
    doc.close()
    
    return output_file_path

def extract_content_for_llm(filtered_pdf_path):
    print(f"Extracting tables from filtered PDF (High-Res AI Model)...")
    
    # Unstructured Hi-res extraction
    elements = partition_pdf(
        filename=filtered_pdf_path,
        infer_table_structure=True,
        strategy="hi_res", 
        hi_res_model_name="yolox",
        languages=["eng"]
    )
    
    content_list = []
    for el in elements:
        if isinstance(el, Table):
            if hasattr(el.metadata, "text_as_html"):
                content_list.append(f"[TABLE]\n{el.metadata.text_as_html}\n[/TABLE]")
            else:
                content_list.append(f"[TABLE]\n{el.text}\n[/TABLE]")
        else:
            content_list.append(el.text)
            
    return "\n\n".join(content_list)

def analyze_with_gpt(text_content):
    keywords_str = json.dumps(BASELINE_KEYWORDS, indent=2)
    system_prompt = f"""
    You are an expert ESG Data Analyst. Extract sustainability metrics from the annual report text provided.
    Use the following KEYWORD DICTIONARY: {keywords_str}

    TASK:
    Extract ONLY the following fields:
    1. Reporting Year: The year covered by the report (e.g. 2023).
    2. Scope 1 Emissions: Direct GHG emissions. Extract value and unit. (e.g. 482123, tCO2e).
    3. Scope 2 Emissions (Market-Based): Indirect GHG emissions. Extract value and unit. (e.g. 923832, tCO2e).
    4. Assurance: Boolean. True if "Limited" or "Reasonable" external assurance is explicitly stated. False otherwise.
    5. Targets: GHG reduction targets. Extract target value (e.g. "30% reduction") and year (e.g. 2030).
    6. Action Plans: A summary of planned actions/strategies (e.g. "Investing in renewable energy...").

    RULES:
    - Normalize values: If text says "3.2 million tonnes", value should be 3200000.
    - IGNORE Location-Based Scope 2.
    - IGNORE Scope 3.

    OUTPUT FORMAT:
    Return strictly valid JSON matching exactly this schema:
    {{
        "reporting_year": <int>,
        "scope_1": {{ "value": <float>, "unit": <str> }},
        "scope_2_market": {{ "value": <float>, "unit": <str> }},
        "assurance_present": <bool>,
        "targets": [
            {{ "target_reduction_percentage": <str>, "target_year": <int>, "base_year": <int> }}
        ],
        "action_plan_summary": <str>
    }}
        """
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Report Content:\n\n{text_content}"}
        ],
        temperature=0
    )
    return json.loads(response.choices[0].message.content)


relevant_pages = filter_relevant_pages_fast(pdf_path)

filtered_pdf = create_filtered_pdf(pdf_path, relevant_pages, output_folder)

raw_text = extract_content_for_llm(filtered_pdf)

esg_data = analyze_with_gpt(raw_text)

output_json = os.path.join(output_folder, "final_esg_data.json")
with open(output_json, "w") as f:
    json.dump(esg_data, f, indent=4)

print("\nEXTRACTED DATA:\n", json.dumps(esg_data, indent=4))