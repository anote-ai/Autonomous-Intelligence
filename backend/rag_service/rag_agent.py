"""
RAG Agent:
Integrates the RAG system as an agent in the AI framework
"""

import os
import json
from typing import List, Dict, Optional
from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document


class AnoteRAGAgent:
    """
    RAG Agent for answering questions about Anote using embedded knowledge base.
    """
    
    def __init__(
        self,
        chroma_db_path: str = "./rag_service/embeddings/chroma_anote_db",
        ollama_model: str = "llama3.2:3b",
        temperature: float = 0.0,
        max_tokens: int = 512,
        top_k_results: int = 5
    ):
        """
        Initialize the Anote RAG Agent.
        
        Args:
            chroma_db_path: Path to ChromaDB vector store
            ollama_model: Ollama model name
            temperature: LLM temperature (0 = deterministic)
            max_tokens: Maximum response length
            top_k_results: Number of chunks to retrieve
        """
        self.chroma_db_path = chroma_db_path
        self.ollama_model = ollama_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_k_results = top_k_results
        
        self.embeddings = None
        self.vectorstore = None
        self.qa_chain = None
        
        self._initialize()
    
    def _initialize(self):
        """Set up embeddings, vector store, and QA chain."""
        
        # Load embeddings model
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Load vector store
        if not os.path.exists(self.chroma_db_path):
            raise FileNotFoundError(
                f"Vector database not found at {self.chroma_db_path}. "
                "Run make_rag_embeddings.py first to create it."
            )
        
        self.vectorstore = Chroma(
            persist_directory=self.chroma_db_path,
            embedding_function=self.embeddings
        )
        
        print(f"[AnoteRAGAgent] Loaded {self.vectorstore._collection.count()} embeddings")
        
        # Initialize Ollama LLM
        self.llm = ChatOllama(
            model=self.ollama_model,
            temperature=self.temperature,
            num_predict=self.max_tokens
        )
        
        # Test Ollama connection
        try:
            test_response = self.llm.invoke("test")
            print("[AnoteRAGAgent] Ollama connection verified")
        except Exception as e:
            raise ConnectionError(f"Cannot connect to Ollama: {e}")
        
        # Create prompt template
        prompt_template = """Use the following context to answer the question about Anote. 
Be specific, detailed, and accurate. If the context contains the answer, provide it clearly.
If you're unsure, say so, but try to provide helpful related information from the context.

Context: {context}

Question: {question}

Answer:"""
        
        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # Create retriever
        retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": self.top_k_results}
        )
        
        # Create QA chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT},
            verbose=False
        )
        
    
    def query(self, question: str) -> Dict:
        """
        Query the RAG system.
        
        Args:
            question: User question about Anote
            
        Returns:
            Dictionary with answer and sources
        """
        try:
            response = self.qa_chain.invoke({"query": question})
            
            answer = response['result']
            source_docs = response['source_documents']
            
            # Format sources
            sources = []
            for doc in source_docs:
                sources.append({
                    'title': doc.metadata.get('title', 'Unknown'),
                    'source': doc.metadata.get('source', 'Unknown'),
                    'chunk_index': doc.metadata.get('chunk_index', 0),
                    'text_preview': doc.page_content[:200] + "..."
                })
            
            return {
                'success': True,
                'question': question,
                'answer': answer,
                'sources': sources,
                'num_sources': len(sources)
            }
            
        except Exception as e:
            return {
                'success': False,
                'question': question,
                'answer': f"Error processing query: {str(e)}",
                'sources': [],
                'num_sources': 0
            }
    
    def batch_query(self, questions: List[str]) -> List[Dict]:
        """
        Process multiple questions.
        
        Args:
            questions: List of questions
            
        Returns:
            List of response dictionaries
        """
        results = []
        for i, question in enumerate(questions, 1):
            result = self.query(question)
            results.append(result)
        return results
    
    def get_agent_info(self) -> Dict:
        """Return agent metadata."""
        return {
            'name': 'AnoteRAGAgent',
            'description': 'RAG-based agent for answering questions about Anote',
            'model': self.ollama_model,
            'vector_db': self.chroma_db_path,
            'num_embeddings': self.vectorstore._collection.count(),
            'capabilities': [
                'Answer questions about Anote products',
                'Provide information about Anote features',
                'Explain Anote use cases',
                'Cite sources for answers'
            ]
        }


# Create AnoteRAGAgent instances
def create_anote_agent(**kwargs) -> AnoteRAGAgent:
    """
    Create and return an initialized Anote RAG Agent.
    
    Args:
        **kwargs: Optional parameters for AnoteRAGAgent
        
    Returns:
        Initialized AnoteRAGAgent instance
    """
    return AnoteRAGAgent(**kwargs)
