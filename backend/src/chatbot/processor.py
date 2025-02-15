from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import HumanMessage, SystemMessage
import logging
import numpy as np
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ChatProcessor:
    def __init__(self, mongo_db):
        self.llm = ChatOpenAI(
            temperature=0.7,
            model_name="gpt-3.5-turbo"
        )
        self.embeddings = OpenAIEmbeddings()
        self.db = mongo_db
        
    def process_chat(self, message, doc_ids):
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(message)
            logger.info(f"Query embedding generated")
            
            # Find similar content using aggregation pipeline
            pipeline = [
                {
                    "$geoNear": {
                        "near": {
                            "type": "Point",
                            "coordinates": query_embedding
                        },
                        "distanceField": "distance",
                        "spherical": True,
                        "query": {
                            "document_id": {"$in": [ObjectId(doc_id) for doc_id in doc_ids]}
                        }
                    }
                },
                {"$limit": 5}
            ]
            
            similar_vectors = list(self.db.vectors.aggregate(pipeline))
            logger.info(f"Found {len(similar_vectors)} similar vectors")
            
            # Get relevant content
            context = [vector["content"] for vector in similar_vectors]
            
            # Prepare messages for ChatGPT
            messages = [
                SystemMessage(content="You are a helpful assistant that answers questions based on the provided document context."),
                HumanMessage(content=f"Context: {' '.join(context)}\n\nQuestion: {message}")
            ]
            
            completion = self.llm.predict_messages(messages)
            return completion.content
            
        except Exception as e:
            logger.error(f"Chat processing error: {str(e)}")
            raise 