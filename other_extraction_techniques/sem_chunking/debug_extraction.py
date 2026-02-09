
import os
import logging
from dotenv import load_dotenv
from ai_extractor import SustainabilityExtractor

# Load environment variables
load_dotenv()

# Configure logging to see all details
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("ai_extractor")
logger.setLevel(logging.DEBUG)

def test_extraction():
    print("Testing extraction...")
    
    # Check API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not found in environment!")
        return
    else:
        print(f"OPENAI_API_KEY found (length: {len(api_key)})")

    try:
        extractor = SustainabilityExtractor(
            model_type="openai", 
            model_name="gpt-3.5-turbo",
            api_key=api_key
        )
    except Exception as e:
        print(f"Error initializing extractor: {e}")
        return

    text = """
    In 2023, Amazon reported a total of 71.27 million metric tons of CO2 equivalent (MMT CO2e) emissions.
    Scope 1 emissions were 14.2 MMT CO2e from fossil fuels.
    We have obtained independent assurance for these figures.
    """
    
    print(f"Input text: {text.strip()}")
    
    try:
        result = extractor.extract_from_text(text)
        print("Result:", result)
    except Exception as e:
        print(f"Error during extraction: {e}")

if __name__ == "__main__":
    test_extraction()
