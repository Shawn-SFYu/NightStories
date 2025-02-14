from PyPDF2 import PdfReader
import spacy
from sentence_transformers import SentenceTransformer
import re
import logging
import os
import json

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_lg")
        self.embeddings = SentenceTransformer('all-MiniLM-L6-v2')
        
    def extract_text(self, pdf_file):
        """Extract text from PDF file object"""
        try:
            logger.info("Extracting text from PDF file")
            reader = PdfReader(pdf_file)
            logger.info(f"PDF file has {len(reader.pages)} pages")
            text = ""
            for page in reader.pages:
                # logger.info(f"Extracting text from page {page.page_number}")
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            raise
            
    def segment_chapters(self, text):
        """Segment text into chapters using NLP"""
        doc = self.nlp(text)
        
        # Simple chapter detection using common patterns
        chapter_patterns = [
            r'Chapter \d+',
            r'CHAPTER \d+',
            r'\d+\.',
            r'Section \d+'
        ]
        
        pattern = '|'.join(chapter_patterns)
        chapters = []
        current_chapter = ""
        current_title = "Introduction"
        
        for paragraph in text.split('\n\n'):
            if re.match(pattern, paragraph.strip()):
                if current_chapter:
                    chapters.append({
                        "title": current_title,
                        "content": current_chapter.strip()
                    })
                current_title = paragraph.strip()
                current_chapter = ""
            else:
                current_chapter += paragraph + "\n\n"
                
        # Add the last chapter
        if current_chapter:
            chapters.append({
                "title": current_title,
                "content": current_chapter.strip()
            })
            
        return chapters

def test_pdf_processor():
    try:
        # Initialize processor
        processor = PDFProcessor()
        logger.info("Initialized PDF processor")
        
        # Test with a sample PDF
        test_pdf_path = "test_files/sample.pdf"
        
        # Ensure test directory exists
        if not os.path.exists("test_files"):
            os.makedirs("test_files")
            logger.info("Created test_files directory")
        
        # Test PDF extraction
        logger.info(f"Processing PDF: {test_pdf_path}")
        with open(test_pdf_path, 'rb') as pdf_file:
            text = processor.extract_text(pdf_file)
            logger.info(f"Extracted {len(text)} characters of text")
            
            # Save extracted text for inspection
            with open("test_files/extracted_text.txt", 'w', encoding='utf-8') as f:
                f.write(text)
            logger.info("Saved extracted text to test_files/extracted_text.txt")
        
        # Test chapter segmentation
        chapters = processor.segment_chapters(text)
        logger.info(f"Segmented into {len(chapters)} chapters")
        
        # Save chapters for inspection
        with open("test_files/chapters.json", 'w', encoding='utf-8') as f:
            json.dump(chapters, f, indent=2)
        logger.info("Saved chapters to test_files/chapters.json")
        
        # Print chapter titles
        logger.info("\nChapter titles:")
        for i, chapter in enumerate(chapters):
            logger.info(f"{i+1}. {chapter['title']}")
            logger.info(f"   Content length: {len(chapter['content'])} characters")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    test_pdf_processor()