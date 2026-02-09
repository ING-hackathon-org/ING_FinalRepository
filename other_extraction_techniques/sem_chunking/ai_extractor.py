from typing import List, Optional, Set, Dict, Any
from pydantic import BaseModel, Field
try:
    from langchain_ollama import ChatOllama
except ImportError:
    ChatOllama = None
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException
import json
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SustainabilityData(BaseModel):
    emission_value: Optional[float] = Field(None, description="The quantity of emissions in a specific unit of measurement")
    emission_unit: Optional[str] = Field(None, description="The unit of measurement")
    emission_sources: List[str] = Field(default_factory=list, description="List of sources that generated the emissions. Just one or two words for each emission source.")
    assurance: Optional[bool] = Field(None, description="Indicates if an external party has provided assurance")
    relevant_info: Optional[str] = Field(None, description="Other relevant information necessary for conducting data analysis on company sustainability, such as specific targets, initiatives, or qualitative assessments.")

class SustainabilityExtractor:
    def __init__(self, model_type: str = "ollama", model_name: str = "llama3", api_key: str = None):
        self.model_type = model_type
        
        if model_type == "ollama":
            if ChatOllama is None:
                raise ImportError("langchain-ollama is required for Ollama support use: pip install langchain-ollama")
            self.llm = ChatOllama(model=model_name, temperature=0)
            
        elif model_type == "openai":
            if ChatOpenAI is None:
                raise ImportError("langchain-openai is required for OpenAI support use: pip install langchain-openai")
                
            # API Key handling: argument > env var
            final_api_key = api_key or os.environ.get("OPENAI_API_KEY")
            if not final_api_key:
                raise ValueError("OpenAI API key is required. Please provide it via argument or OPENAI_API_KEY environment variable.")
                
            self.llm = ChatOpenAI(model=model_name, temperature=0, api_key=final_api_key)
            
        else:
            raise ValueError(f"Unsupported model type: {model_type}. Supported types: 'ollama', 'openai'")

        self.parser = PydanticOutputParser(pydantic_object=SustainabilityData)
        self.seen_sources: Set[str] = set()

    def extract_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        if not text or len(text.strip()) < 50:
            return None

        # Convert set to sorted list for consistent prompt
        seen_sources_list = sorted(list(self.seen_sources))
        
        # Dynamically generate the field description string
        fields_desc = []
        for name, field in SustainabilityData.model_fields.items():
            field_type = str(field.annotation).replace("typing.", "").replace("Optional[", "").replace("]", "")
            # Clean up type string for better LLM understanding
            if "float" in field_type: field_type = "float"
            elif "bool" in field_type: field_type = "bool"
            elif "str" in field_type: field_type = "str"
            elif "List" in field_type or "list" in field_type: field_type = "list[str]"
            
            desc = field.description
            fields_desc.append(f"- {name}: {field_type} ({desc})")
            
        fields_prompt_str = "\n".join(fields_desc)

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert in sustainability data extraction. Extract the required information from the text. If a piece of information is not present, leave it null or empty."),
            ("user", """Extract the following information from the text:
{fields_list}

When identifying emission sources, try to reuse categories from this list if applicable: {seen_sources}.
If a new source is identified, keep it to 1-2 words.

Text: {text}

{format_instructions}
""")
        ])

        chain = prompt | self.llm | self.parser

        try:
            # Check context length roughly if using OpenAI (approx assumption: 1 token ~= 4 chars)
            # This is a heuristic logging, not a hard check
            if len(text) > 60000: 
                logger.warning(f"Text chunk is very large ({len(text)} chars). This might exceed token limits or degrade performance.")

            result = chain.invoke({
                "text": text,
                "seen_sources": ", ".join(seen_sources_list) if seen_sources_list else "None",
                "fields_list": fields_prompt_str,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Update seen sources
            if result.emission_sources:
                for source in result.emission_sources:
                    self.seen_sources.add(source)
            
            # Check if basically empty (all None or empty list)
            # Dynamic check using model fields
            all_empty = True
            for field_name in SustainabilityData.model_fields.keys():
                value = getattr(result, field_name)
                if value is not None and value != [] and value != "":
                    all_empty = False
                    break
            
            if all_empty:
                return None
                
            return result.dict()
            
        except OutputParserException as e:
            logger.warning(f"Failed to parse output: {e}")
            return None
        except Exception as e:
            # Enhanced error logging
            error_msg = str(e)
            if "context_length_exceeded" in error_msg:
                logger.error(f"Context length exceeded! Text length: {len(text)}. Error: {e}")
            elif "AuthenticationError" in error_msg or "api_key" in error_msg.lower():
                logger.error(f"Authentication error. Check your API KEY. Error: {e}")
            else:
                logger.error(f"Error during extraction: {e}")
            return None

    def process_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process the structured data and enrich it with AI-extracted information.
        Aggregates data per document and stops early when all fields are filled.
        Saves the AI extraction results to 'ai_output.json' incrementally.
        """
        enriched_data = []
        ai_output_data = []
        
        # Load existing ai_output.json if it exists to append or resume? 
        # For now, we'll just overwrite as per request "make it save... hard-coded".
        # But to be safe against crashes, we'll write after each doc.
        
        total_docs = sum(len(item.get("content", [])) for item in data)
        processed_count = 0
        
        for item in data:
            company = item.get("company", "Unknown")
            year = item.get("year", "Unknown")
            new_item = item.copy()
            new_content_list = []
            
            content_list = item.get("content", [])
            for doc in content_list:
                doc_copy = doc.copy()
                doc_name = doc.get("document_name", "Unknown")
                doc_path = doc.get("document_path", "Unknown")
                doc_content = doc.get("content", {})
                
                # Check for semantic chunks
                chunks = doc_content.get("semantic_chunks", [])
                if not chunks and doc_content.get("body_text"):
                    chunks = [{"chunk_content": doc_content["body_text"]}]
                
                # Convert chunks to list of strings if they are not already (for context window estimation)
                
                # Initialize aggregated data for this document dynamically
                doc_extracted_data = {
                    field: None for field in SustainabilityData.model_fields.keys()
                }
                # Ensure list fields are initialized to empty lists
                for field_name, field_info in SustainabilityData.model_fields.items():
                    if "List" in str(field_info.annotation) or field_info.annotation == list or getattr(field_info, 'default_factory', None) == list:
                         doc_extracted_data[field_name] = []


                
                # Track if we found any data to save
                found_data = False
                
                logger.info(f"Processing {company} {year} - {doc_name} ({len(chunks)} chunks)")
                
                for i, chunk in enumerate(chunks):
                    # Check if we have all necessary info
                    all_filled = True
                    for field_name in doc_extracted_data:
                         value = doc_extracted_data[field_name]
                         # We consider filled if not None. For lists, it's debatable, but let's say if we have some sources that's good.
                         # The user prompt implied "check them if not filled yet".
                         # If we want to be strict:
                         if value is None:
                             all_filled = False
                             break
                         if isinstance(value, list) and not value:
                              # For lists, maybe we want at least one item? Or maybe empty list is valid "not found".
                              # Let's assume we want to keep looking if list is empty.
                              all_filled = False
                              break

                    if all_filled:
                        logger.info(f"All data found for {doc_name}, skipping remaining chunks.")
                        break
                        
                    # Prepare context for what is missing (optional optimization for prompt)
                    # For now, we'll extract everything and merge to keep it simple and robust
                    
                    if isinstance(chunk, dict):
                        text = chunk.get("chunk_content") or chunk.get("text") or ""
                    else:
                        text = str(chunk)
                        
                    if not text:
                        continue
                        
                    # Log progress
                    # logger.info(f"  - Chunk {i}/{len(chunks)}")
                    
                    result = self.extract_from_text(text)
                    if result:
                        # Merge results: loop over keys and check if not filled yet
                        for field_name, new_value in result.items():
                            current_value = doc_extracted_data.get(field_name)
                            
                            # If current is None, take new value if it exists
                            if current_value is None and new_value is not None:
                                doc_extracted_data[field_name] = new_value
                                found_data = True
                            
                            # If current is empty list, take new value if it has items
                            elif isinstance(current_value, list) and not current_value and isinstance(new_value, list) and new_value:
                                doc_extracted_data[field_name] = new_value
                                found_data = True
                                
                            # Special case: maybe we want to extend lists? 
                            # "Make the extraction dynamic ... check them if not filled yet"
                            # If it's already filled (e.g. found sources in chunk 1), we generally keep it.
                            # But if the user wants to accumulate, we could extend. 
                            # Given "check them if not filled yet", I'll stick to "fill if empty".
                            
                            # If it's a string and we want to maybe append? (e.g. relevant_info)
                            # For now, "fill if empty" seems to be the request.

                # Save the aggregated result if we found anything (or even if we didn't, to show we processed it?)
                # User said "Make it be not empty". Storing even partial/empty results helps debug.
                
                ai_output_entry = {
                    "company": company,
                    "year": year,
                    "document_name": doc_name,
                    "document_path": doc_path,
                    "extracted_data": doc_extracted_data
                }
                ai_output_data.append(ai_output_entry)
                
                # Update the doc object with the aggregated data
                doc_copy["ai_extracted_data"] = doc_extracted_data
                new_content_list.append(doc_copy)
                
                processed_count += 1
                
                # Incremental save
                try:
                    with open("ai_output.json", "w", encoding="utf-8") as f:
                        json.dump(ai_output_data, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    logger.error(f"Failed to save ai_output.json: {e}")

            new_item["content"] = new_content_list
            enriched_data.append(new_item)
            
        return enriched_data