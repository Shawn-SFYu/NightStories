from langchain.chat_models import ChatOpenAI
from sentence_transformers import SentenceTransformer
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
        self.embeddings = SentenceTransformer('all-MiniLM-L6-v2')
        self.db = mongo_db
        
    def process_chat(self, message, doc_ids):
        try:
            # Generate query embedding
            query_embedding = self.embeddings.encode(message).tolist()
            logger.info(f"Query embedding generated")
            
            # Before the query
            logger.info(f"Searching for documents: {doc_ids}")
            logger.info(f"Query embedding length: {len(query_embedding)}")
            
            # Add before the aggregation
            #sample_doc = self.db.vectors.find_one()
            #logger.info(f"Random vector sample: {sample_doc}")
            logger.info(f"Document IDs being searched: {[ObjectId(doc_id) for doc_id in doc_ids]}")
            
            # Find similar content using aggregation pipeline
            pipeline = [
                {
                    "$match": {
                        "document_id": {"$in": [ObjectId(doc_id) for doc_id in doc_ids]}
                    }
                },
                {
                    "$addFields": {
                        "similarity": {
                            "$reduce": {
                                "input": {"$range": [0, {"$size": "$embedding_vector"}]},
                                "initialValue": 0,
                                "in": {
                                    "$add": [
                                        "$$value",
                                        {"$multiply": [
                                            {"$arrayElemAt": ["$embedding_vector", "$$this"]},
                                            {"$arrayElemAt": [query_embedding, "$$this"]}
                                        ]}
                                    ]
                                }
                            }
                        }
                    }
                },
                {"$sort": {"similarity": -1}},
                {"$limit": 5}
            ]
            
            # Add debug logging before the query
            #logger.info(f"Checking vectors collection...")
            #sample_vector = self.db.vectors.find_one({"document_id": ObjectId(doc_ids[0])})
            # logger.info(f"Sample vector structure: {sample_vector}")
            
            similar_vectors = list(self.db.vectors.aggregate(pipeline))
            
            # After the query
            #logger.info(f"Pipeline: {pipeline}")
            # logger.info(f"Similar vectors raw: {similar_vectors}")
            
            # Get relevant content
            context = [vector["content"] for vector in similar_vectors]
            logger.info(f"Context: {context}")
            
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