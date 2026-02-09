import fitz
from typing import List, Tuple
from enum import Enum

class TextType(Enum):
    """
    Type of the text extracted.
    """
    TEXT = 0
    SUBTITLE = 1
    TITLE = 2


class Extractor:    
    """
    Class of a document extractor for PDFs using fitz
    """
    def __init__(self, include_titles: bool = True) -> None:
        """
        Initialize the document extractor
        """
        self.title_threshold = 1.3  # Font size ratio for titles
        self.subtitle_threshold = 1.15  # Font size ratio for subtitles
        self.include_titles = include_titles
        
    def extract_text(self, pdf_path: str) -> List[Tuple[TextType, str]]:
        """
        Extract titles and text and return it as a list of tuples.
        The type is defined in TextType.
        """
        result = []
        
        # Open the PDF document
        doc = fitz.open(pdf_path)
        
        # Calculate average font size across the document
        font_sizes = []
        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            font_sizes.append(span["size"])
        
        # Calculate average font size
        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 12
        
        # Extract text with classification
        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    line_text = ""
                    max_font_size = 0
                    is_bold = False
                    
                    # Collect text and metadata from spans
                    for span in line["spans"]:
                        line_text += span["text"]
                        max_font_size = max(max_font_size, span["size"])
                        # Check if font is bold
                        if "bold" in span["font"].lower():
                            is_bold = True
                    
                    # Clean the extracted text
                    line_text = self.__clean_data(line_text)
                    
                    if not line_text:
                        continue

                    # Skip page numbers and very short noise
                    if line_text.isdigit() or (len(line_text) < 4 and not line_text.isalpha()):
                        continue
                    
                    # Classify text based on font size and formatting
                    font_ratio = max_font_size / avg_font_size
                    
                    if font_ratio >= self.title_threshold or (is_bold and font_ratio >= self.subtitle_threshold):
                        if not self.include_titles:
                            continue
                        text_type = TextType.TITLE
                    elif font_ratio >= self.subtitle_threshold or is_bold:
                        if not self.include_titles:
                            continue
                        text_type = TextType.SUBTITLE
                    else:
                        text_type = TextType.TEXT
                    
                    result.append((text_type, line_text))
        
        doc.close()
        return result

    def __clean_data(self, text: str) -> str:
        """
        It takes a text and cleans it according to some common cleaning steps.
        """
        import re
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading and trailing whitespace
        text = text.strip()
        
        # Remove special characters that are artifacts from PDF extraction
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Remove multiple consecutive punctuation marks
        text = re.sub(r'([.,!?;:]){2,}', r'\1', text)
        
        # Fix common OCR errors (optional - can be expanded)
        text = text.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
        
        return text
