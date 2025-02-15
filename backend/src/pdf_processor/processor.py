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

    def store_embeddings(self, text, doc_id, chapter_id, mongo_db):
        try:
            # Generate embeddings for the text
            embedding = self.embeddings.encode(text).tolist()
            
            # Store in MongoDB vectors collection
            mongo_db.vectors.insert_one({
                "document_id": doc_id,
                "chapter_id": chapter_id,
                "embedding": {
                    "type": "Point",
                    "coordinates": embedding
                }
            })
            logger.info(f"Stored embeddings for doc {doc_id}, chapter {chapter_id}")
        except Exception as e:
            logger.error(f"Error storing embeddings: {str(e)}")
            raise

    def process_pdf(self, pdf_file, doc_id, mongo_db):
        """Process PDF file and store text and embeddings"""
        try:
            logger.info(f"Processing PDF for document {doc_id}")
            
            # Extract text from PDF
            text = self.extract_text(pdf_file)
            
            # Split text into chapters/sections
            doc = self.nlp(text)
            chapters = []
            current_chapter = ""
            chapter_id = 0
            
            for paragraph in doc.sents:
                current_chapter += paragraph.text + "\n"
                
                # Simple heuristic: split into chunks of roughly equal size
                if len(current_chapter) > 2000:  # Adjust size as needed
                    chapters.append({
                        "chapter_id": chapter_id,
                        "content": current_chapter.strip()
                    })
                    
                    # Store embeddings for this chapter
                    self.store_embeddings(
                        current_chapter.strip(),
                        doc_id,
                        chapter_id,
                        mongo_db
                    )
                    
                    current_chapter = ""
                    chapter_id += 1
            
            # Don't forget the last chapter
            if current_chapter.strip():
                chapters.append({
                    "chapter_id": chapter_id,
                    "content": current_chapter.strip()
                })
                self.store_embeddings(
                    current_chapter.strip(),
                    doc_id,
                    chapter_id,
                    mongo_db
                )
            
            logger.info(f"Processed {len(chapters)} chapters for document {doc_id}")
            return chapters
            
        except Exception as e:
            logger.error(f"PDF processing error: {str(e)}")
            raise

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