from PyPDF2 import PdfReader
import spacy
from sentence_transformers import SentenceTransformer
import re
import logging
import os
import json
from bson import ObjectId
import datetime

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_lg")
        self.embeddings = SentenceTransformer('all-MiniLM-L6-v2')
        self.chunk_size = 1500  # characters
        self.overlap_size = 300  # characters
        
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
            

    def chunk_text(self, text):
        """Split text into overlapping chunks while preserving sentence boundaries"""
        doc = self.nlp(text)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sent in doc.sents:
            sent_text = sent.text.strip()
            sent_length = len(sent_text)
            
            if current_length + sent_length > self.chunk_size and current_chunk:
                # Store current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(chunk_text)
                
                # Keep overlap sentences for next chunk
                overlap_length = 0
                overlap_sentences = []
                
                for sent in reversed(current_chunk):
                    if overlap_length + len(sent) <= self.overlap_size:
                        overlap_sentences.insert(0, sent)
                        overlap_length += len(sent)
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_length = overlap_length
            
            current_chunk.append(sent_text)
            current_length += sent_length
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks

    def process_pdf(self, pdf_file, doc_id, mongo_db):
        try:
            # Extract text from PDF
            text = self.extract_text(pdf_file)
            
            # Store the complete text in documents collection
            mongo_db.documents.update_one(
                {"_id": ObjectId(doc_id)},
                {"$set": {
                    "content": text,
                    "status": "completed"
                }}
            )
            
            # Process chunks for vector embeddings
            chunks = self.chunk_text(text)
            for chunk_id, chunk_text in enumerate(chunks):
                embedding = self.embeddings.encode(chunk_text).tolist()
                
                # Store chunk and embedding in vectors collection
                mongo_db.vectors.insert_one({
                    "document_id": ObjectId(doc_id),
                    "chunk_id": chunk_id,
                    "content": chunk_text,
                    "embedding_vector": embedding,
                    "metadata": {
                        "total_chunks": len(chunks),
                        "char_length": len(chunk_text),
                        "created_at": datetime.datetime.utcnow()
                    }
                })
            
            return True
            
        except Exception as e:
            logger.error(f"PDF processing error: {str(e)}")
            mongo_db.documents.update_one(
                {"_id": ObjectId(doc_id)},
                {"$set": {"status": "failed"}}
            )
            raise