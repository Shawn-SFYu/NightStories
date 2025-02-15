from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging
import numpy as np
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

class ChatProcessor:
    def __init__(self, mongo_db):
        self.llm = ChatOpenAI(
            temperature=0.7,
            model_name="gpt-3.5-turbo"
        )
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.db = mongo_db
        
    def process_chat(self, message, documents_content):
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(message)
            
            # Find similar content from vectors collection
            similar_vectors = self.db.vectors.find(
                {
                    "$near": {
                        "$geometry": {
                            "type": "Point",
                            "coordinates": query_embedding
                        },
                        "$maxDistance": 0.8
                    }
                }
            ).limit(5)
            
            # Get relevant document content
            context = []
            for vector in similar_vectors:
                doc = self.db.documents.find_one(
                    {"_id": ObjectId(vector["document_id"])}
                )
                if doc:
                    context.append(doc["chapters"][vector["chapter_id"]]["content"])
            
            # Prepare messages for ChatGPT
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that answers questions based on the provided document context."
                },
                {
                    "role": "user",
                    "content": f"Context: {' '.join(context)}\n\nQuestion: {message}"
                }
            ]
            
            completion = self.llm.predict_messages(messages)
            return completion.content
            
        except Exception as e:
            logger.error(f"Chat processing error: {str(e)}")
            raise 