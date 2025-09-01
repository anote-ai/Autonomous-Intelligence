from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing import Dict, List, Any, Optional, Generator, TypedDict, Annotated
import json
import time
import re
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.callbacks import BaseCallbackHandler
from pydantic import BaseModel, Field
import os

from database.db import get_db_connection
from api_endpoints.financeGPT.chatbot_endpoints import (
    get_relevant_chunks, add_message_to_db, add_sources_to_db,
    retrieve_message_from_db, retrieve_docs_from_db
)
from .config import AgentConfig

class AgentState(TypedDict):
    """Shared state between all agents in the network"""
    query: str
    chat_id: int
    user_email: str
    messages: List[Dict[str, Any]]
    current_step: str
    document_sources: List[tuple]
    chat_history: List[Dict[str, str]]
    available_documents: List[Dict[str, Any]]
    general_knowledge_used: bool
    final_answer: str
    confidence_score: float
    reasoning_steps: List[Dict[str, Any]]
    next_agent: str
    completed_agents: List[str]
    stream_callback: Any


class MultiAgentCallbackHandler(BaseCallbackHandler):
    """Enhanced callback handler for multi-agent streaming"""
    
    def __init__(self, stream_callback, agent_name: str = "unknown"):
        super().__init__()
        self.stream_callback = stream_callback
        self.agent_name = agent_name
        self.step_counter = 0
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> None:
        """Called when LLM starts generating"""
        try:
            self.stream_callback({
                "type": "agent_start",
                "agent_name": self.agent_name,
                "message": f"{self.agent_name} is processing...",
                "timestamp": self._get_timestamp()
            })
        except Exception as e:
            print(f"Error in agent_start callback: {e}")
    
    def on_llm_end(self, response, **kwargs: Any) -> None:
        """Called when LLM finishes generating"""
        try:
            if response.generations and len(response.generations) > 0:
                generation = response.generations[0][0]
                self.stream_callback({
                    "type": "agent_reasoning",
                    "agent_name": self.agent_name,
                    "reasoning": generation.text[:300] + "..." if len(generation.text) > 300 else generation.text,
                    "timestamp": self._get_timestamp()
                })
        except Exception as e:
            print(f"Error in agent_reasoning callback: {e}")
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        """Called when agent uses a tool"""
        try:
            self.stream_callback({
                "type": "agent_tool_use",
                "agent_name": self.agent_name,
                "tool_name": serialized.get("name", "unknown_tool"),
                "input": input_str[:200] + "..." if len(input_str) > 200 else input_str,
                "message": f"{self.agent_name} using {serialized.get('name', 'tool')}",
                "timestamp": self._get_timestamp()
            })
        except Exception as e:
            print(f"Error in agent_tool_use callback: {e}")
    
    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called when tool finishes"""
        try:
            self.stream_callback({
                "type": "agent_tool_complete",
                "agent_name": self.agent_name,
                "output": str(output)[:200] + "..." if len(str(output)) > 200 else str(output),
                "message": f"{self.agent_name} completed tool execution",
                "timestamp": self._get_timestamp()
            })
        except Exception as e:
            print(f"Error in agent_tool_complete callback: {e}")
    
    @staticmethod
    def _get_timestamp():
        return time.time()


class BaseSpecializedAgent:
    """Base class for all specialized agents"""
    
    def __init__(self, name: str, model_type: int = 0, model_key: Optional[str] = None):
        self.name = name
        self.model_type = model_type
        self.model_key = model_key
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self):
        if self.model_type == 0:  # OpenAI/GPT
            model_name = self.model_key if self.model_key else "gpt-4"
            return ChatOpenAI(
                model=model_name,
                temperature=AgentConfig.AGENT_TEMPERATURE,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                streaming=True
            )
        else:  # Anthropic/Claude
            return ChatAnthropic(
                model="claude-3-sonnet-20240229",
                temperature=AgentConfig.AGENT_TEMPERATURE,
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
                streaming=True
            )
    
    def process(self, state: AgentState) -> Dict[str, Any]:
        """Override this method in specialized agents"""
        raise NotImplementedError("Each agent must implement the process method")


class DocumentRetrievalAgent(BaseSpecializedAgent):
    """Specialized agent for document retrieval and analysis"""
    
    def __init__(self, model_type: int = 0, model_key: Optional[str] = None):
        super().__init__("DocumentRetrieval", model_type, model_key)
    
    def process(self, state: AgentState) -> Dict[str, Any]:
        """Process document retrieval requests"""
        callback_handler = MultiAgentCallbackHandler(state["stream_callback"], self.name)
        
        try:
            # Extract query and context
            query = state["query"]
            chat_id = state["chat_id"]
            user_email = state["user_email"]
            
            # Retrieve relevant documents
            sources = get_relevant_chunks(6, query, chat_id, user_email)
            
            if not sources or sources == ["No text found"]:
                reasoning = "No relevant documents found for this query."
                confidence = 0.2
                next_agent = "GeneralKnowledgeAgent"
            else:
                # Analyze retrieved documents with LLM
                document_texts = []
                for i, (chunk_text, document_name) in enumerate(sources):
                    document_texts.append(f"Document {i+1} ({document_name}): {chunk_text.strip()}")
                
                combined_docs = "\n\n".join(document_texts)
                
                # Use LLM to analyze relevance and extract key information
                analysis_prompt = f"""
                As a document analysis specialist, analyze these retrieved documents for relevance to the query: "{query}"
                
                Documents:
                {combined_docs}
                
                Provide:
                1. Relevance score (0-1)
                2. Key information that answers the query
                3. Source attribution
                4. Confidence in the answer
                
                Please format your response as JSON with keys: relevance_score, key_info, sources, confidence
                """
                
                response = self.llm.invoke(
                    [SystemMessage(content="You are a document analysis specialist."), 
                     HumanMessage(content=analysis_prompt)],
                    config={"callbacks": [callback_handler]}
                )
                
                try:
                    analysis = json.loads(response.content)
                    confidence = analysis.get("confidence", 0.7)
                    reasoning = analysis.get("key_info", "Found relevant information in documents.")
                except:
                    confidence = 0.7
                    reasoning = "Successfully retrieved and analyzed relevant documents."
                
                next_agent = "OrchestratorAgent"
            
            # Add reasoning step
            reasoning_step = {
                'id': f'step-{int(time.time() * 1000)}',
                'type': 'agent_completion',
                'agent_name': self.name,
                'message': f'{self.name} completed document analysis',
                'reasoning': reasoning,
                'confidence': confidence,
                'timestamp': int(time.time() * 1000)
            }
            
            return {
                "document_sources": sources if sources else [],
                "confidence_score": confidence,
                "reasoning_steps": state["reasoning_steps"] + [reasoning_step],
                "completed_agents": state["completed_agents"] + [self.name],
                "next_agent": next_agent
            }
            
        except Exception as e:
            error_step = {
                'id': f'step-{int(time.time() * 1000)}',
                'type': 'agent_error',
                'agent_name': self.name,
                'message': f'{self.name} encountered an error',
                'error': str(e),
                'timestamp': int(time.time() * 1000)
            }
            
            return {
                "document_sources": [],
                "confidence_score": 0.1,
                "reasoning_steps": state["reasoning_steps"] + [error_step],
                "completed_agents": state["completed_agents"] + [self.name],
                "next_agent": "GeneralKnowledgeAgent"
            }


class ChatHistoryAgent(BaseSpecializedAgent):
    """Specialized agent for chat history analysis and context understanding"""
    
    def __init__(self, model_type: int = 0, model_key: Optional[str] = None):
        super().__init__("ChatHistory", model_type, model_key)
    
    def process(self, state: AgentState) -> Dict[str, Any]:
        """Process chat history and context analysis"""
        callback_handler = MultiAgentCallbackHandler(state["stream_callback"], self.name)
        
        try:
            query = state["query"]
            chat_id = state["chat_id"]
            user_email = state["user_email"]
            
            # Check if query needs historical context
            context_keywords = ["it", "that", "the one", "shorter", "longer", "what I said", "previous", "before", "earlier", "last", "prior", "context", "history", "refer to", "mentioned"]
            needs_context = any(keyword in query.lower() for keyword in context_keywords)
            
            if not needs_context:
                reasoning_step = {
                    'id': f'step-{int(time.time() * 1000)}',
                    'type': 'agent_completion',
                    'agent_name': self.name,
                    'message': f'{self.name} determined no historical context needed',
                    'reasoning': 'Query does not reference previous conversation elements',
                    'timestamp': int(time.time() * 1000)
                }
                
                return {
                    "chat_history": [],
                    "reasoning_steps": state["reasoning_steps"] + [reasoning_step],
                    "completed_agents": state["completed_agents"] + [self.name],
                    "next_agent": "DocumentRetrievalAgent"
                }
            
            # Retrieve chat history
            messages = retrieve_message_from_db(user_email, chat_id, 0)
            if not messages:
                chat_history = []
                reasoning = "No chat history found"
            else:
                recent_messages = messages[-10:]  # Get last 10 messages for context
                chat_history = []
                for msg in recent_messages:
                    role = "User" if msg['sent_from_user'] == 1 else "Assistant"
                    chat_history.append({"role": role, "content": msg['message_text']})
                
                # Analyze context relevance with LLM
                history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
                
                context_prompt = f"""
                As a conversation context specialist, analyze this chat history to understand references in the current query.
                
                Current Query: "{query}"
                
                Chat History:
                {history_text}
                
                Identify what the user is referring to and provide context. Format as JSON with keys: context_found, referent, explanation
                """
                
                response = self.llm.invoke(
                    [SystemMessage(content="You are a conversation context analysis specialist."), 
                     HumanMessage(content=context_prompt)],
                    config={"callbacks": [callback_handler]}
                )
                
                try:
                    context_analysis = json.loads(response.content)
                    reasoning = context_analysis.get("explanation", "Analyzed conversation context")
                except:
                    reasoning = "Retrieved and analyzed conversation history for context"
            
            reasoning_step = {
                'id': f'step-{int(time.time() * 1000)}',
                'type': 'agent_completion',
                'agent_name': self.name,
                'message': f'{self.name} completed context analysis',
                'reasoning': reasoning,
                'timestamp': int(time.time() * 1000)
            }
            
            return {
                "chat_history": chat_history,
                "reasoning_steps": state["reasoning_steps"] + [reasoning_step],
                "completed_agents": state["completed_agents"] + [self.name],
                "next_agent": "DocumentRetrievalAgent"
            }
            
        except Exception as e:
            error_step = {
                'id': f'step-{int(time.time() * 1000)}',
                'type': 'agent_error',
                'agent_name': self.name,
                'message': f'{self.name} encountered an error',
                'error': str(e),
                'timestamp': int(time.time() * 1000)
            }
            
            return {
                "chat_history": [],
                "reasoning_steps": state["reasoning_steps"] + [error_step],
                "completed_agents": state["completed_agents"] + [self.name],
                "next_agent": "DocumentRetrievalAgent"
            }


class DocumentListAgent(BaseSpecializedAgent):
    """Specialized agent for document listing and management queries"""
    
    def __init__(self, model_type: int = 0, model_key: Optional[str] = None):
        super().__init__("DocumentList", model_type, model_key)
    
    def process(self, state: AgentState) -> Dict[str, Any]:
        """Process document listing requests"""
        callback_handler = MultiAgentCallbackHandler(state["stream_callback"], self.name)
        
        try:
            query = state["query"]
            chat_id = state["chat_id"]
            user_email = state["user_email"]
            
            # Check if query is asking about available documents
            list_keywords = ["list", "documents", "files", "available", "what documents", "show me", "which documents"]
            is_list_query = any(keyword in query.lower() for keyword in list_keywords)
            
            if not is_list_query:
                reasoning_step = {
                    'id': f'step-{int(time.time() * 1000)}',
                    'type': 'agent_completion',
                    'agent_name': self.name,
                    'message': f'{self.name} determined query does not require document listing',
                    'reasoning': 'Query is not asking for document list information',
                    'timestamp': int(time.time() * 1000)
                }
                
                return {
                    "available_documents": [],
                    "reasoning_steps": state["reasoning_steps"] + [reasoning_step],
                    "completed_agents": state["completed_agents"] + [self.name],
                    "next_agent": "ChatHistoryAgent"
                }
            
            # Retrieve document list
            docs = retrieve_docs_from_db(chat_id, user_email)
            
            if not docs:
                available_documents = []
                reasoning = "No documents found in this chat"
                
                # This might be the final answer for this type of query
                final_answer = "No documents are currently available in this chat."
                
                reasoning_step = {
                    'id': f'step-{int(time.time() * 1000)}',
                    'type': 'agent_completion',
                    'agent_name': self.name,
                    'message': f'{self.name} completed document listing',
                    'reasoning': reasoning,
                    'can_provide_final_answer': True,
                    'suggested_answer': final_answer,
                    'timestamp': int(time.time() * 1000)
                }
                
                return {
                    "available_documents": available_documents,
                    "final_answer": final_answer,
                    "confidence_score": 1.0,  # High confidence for definitive document list
                    "reasoning_steps": state["reasoning_steps"] + [reasoning_step],
                    "completed_agents": state["completed_agents"] + [self.name],
                    "next_agent": "OrchestratorAgent"
                }
            else:
                # Format document list
                available_documents = []
                doc_list = []
                for doc in docs:
                    doc_info = {"name": doc['document_name'], "id": doc['id']}
                    available_documents.append(doc_info)
                    doc_list.append(f"- {doc['document_name']} (ID: {doc['id']})")
                
                final_answer = "Available documents:\n" + "\n".join(doc_list)
                reasoning = f"Successfully retrieved list of {len(docs)} documents"
                
                reasoning_step = {
                    'id': f'step-{int(time.time() * 1000)}',
                    'type': 'agent_completion',
                    'agent_name': self.name,
                    'message': f'{self.name} completed document listing',
                    'reasoning': reasoning,
                    'can_provide_final_answer': True,
                    'suggested_answer': final_answer,
                    'timestamp': int(time.time() * 1000)
                }
                
                return {
                    "available_documents": available_documents,
                    "final_answer": final_answer,
                    "confidence_score": 1.0,  # High confidence for definitive document list
                    "reasoning_steps": state["reasoning_steps"] + [reasoning_step],
                    "completed_agents": state["completed_agents"] + [self.name],
                    "next_agent": "OrchestratorAgent"
                }
            
        except Exception as e:
            error_step = {
                'id': f'step-{int(time.time() * 1000)}',
                'type': 'agent_error',
                'agent_name': self.name,
                'message': f'{self.name} encountered an error',
                'error': str(e),
                'timestamp': int(time.time() * 1000)
            }
            
            return {
                "available_documents": [],
                "reasoning_steps": state["reasoning_steps"] + [error_step],
                "completed_agents": state["completed_agents"] + [self.name],
                "next_agent": "ChatHistoryAgent"
            }


class GeneralKnowledgeAgent(BaseSpecializedAgent):
    """Specialized agent for general knowledge when documents don't have answers"""
    
    def __init__(self, model_type: int = 0, model_key: Optional[str] = None):
        super().__init__("GeneralKnowledge", model_type, model_key)
    
    def process(self, state: AgentState) -> Dict[str, Any]:
        """Process general knowledge requests"""
        callback_handler = MultiAgentCallbackHandler(state["stream_callback"], self.name)
        
        try:
            query = state["query"]
            
            # Check if general knowledge is enabled in config
            if not AgentConfig.is_general_knowledge_enabled():
                reasoning_step = {
                    'id': f'step-{int(time.time() * 1000)}',
                    'type': 'agent_completion',
                    'agent_name': self.name,
                    'message': f'{self.name} is disabled',
                    'reasoning': 'General knowledge is disabled in configuration',
                    'timestamp': int(time.time() * 1000)
                }
                
                return {
                    "general_knowledge_used": False,
                    "final_answer": "I can only answer questions based on the uploaded documents, and I couldn't find relevant information for your query.",
                    "confidence_score": 0.3,
                    "reasoning_steps": state["reasoning_steps"] + [reasoning_step],
                    "completed_agents": state["completed_agents"] + [self.name],
                    "next_agent": "OrchestratorAgent"
                }
            
            # Use LLM to provide general knowledge answer
            knowledge_prompt = f"""
            As a general knowledge specialist, provide a helpful and accurate answer to this question: "{query}"
            
            Important: Be clear that this answer is based on general knowledge rather than the user's uploaded documents.
            Provide a concise but comprehensive answer.
            """
            
            response = self.llm.invoke(
                [SystemMessage(content="You are a helpful general knowledge assistant."), 
                 HumanMessage(content=knowledge_prompt)],
                config={"callbacks": [callback_handler]}
            )
            
            general_answer = f"Based on general knowledge: {response.content}"
            reasoning = "Provided general knowledge answer since documents didn't contain relevant information"
            
            reasoning_step = {
                'id': f'step-{int(time.time() * 1000)}',
                'type': 'agent_completion',
                'agent_name': self.name,
                'message': f'{self.name} provided general knowledge answer',
                'reasoning': reasoning,
                'timestamp': int(time.time() * 1000)
            }
            
            return {
                "general_knowledge_used": True,
                "final_answer": general_answer,
                "confidence_score": 0.6,  # Moderate confidence for general knowledge
                "reasoning_steps": state["reasoning_steps"] + [reasoning_step],
                "completed_agents": state["completed_agents"] + [self.name],
                "next_agent": "OrchestratorAgent"
            }
            
        except Exception as e:
            error_step = {
                'id': f'step-{int(time.time() * 1000)}',
                'type': 'agent_error',
                'agent_name': self.name,
                'message': f'{self.name} encountered an error',
                'error': str(e),
                'timestamp': int(time.time() * 1000)
            }
            
            return {
                "general_knowledge_used": False,
                "final_answer": "I encountered an error while trying to provide a general knowledge answer.",
                "confidence_score": 0.1,
                "reasoning_steps": state["reasoning_steps"] + [error_step],
                "completed_agents": state["completed_agents"] + [self.name],
                "next_agent": "OrchestratorAgent"
            }


class OrchestratorAgent(BaseSpecializedAgent):
    """Orchestrator agent that coordinates the overall workflow and the other agents to provide a final answer"""
    
    def __init__(self, model_type: int = 0, model_key: Optional[str] = None):
        super().__init__("Orchestrator", model_type, model_key)
    
    def process(self, state: AgentState) -> Dict[str, Any]:
        """Coordinate agents and provide final answer"""
        callback_handler = MultiAgentCallbackHandler(state["stream_callback"], self.name)
        
        try:
            query = state["query"]
            document_sources = state.get("document_sources", [])
            chat_history = state.get("chat_history", [])
            available_documents = state.get("available_documents", [])
            general_knowledge_used = state.get("general_knowledge_used", False)
            confidence_score = state.get("confidence_score", 0.5)
            
            # If we already have a final answer from a specialized agent, use it
            if state.get("final_answer") and confidence_score > 0.8:
                reasoning_step = {
                    'id': f'step-{int(time.time() * 1000)}',
                    'type': 'orchestrator_decision',
                    'agent_name': self.name,
                    'message': f'{self.name} accepted specialized agent answer',
                    'reasoning': f'High confidence answer from specialized agent (confidence: {confidence_score})',
                    'timestamp': int(time.time() * 1000)
                }
                
                return {
                    "final_answer": state["final_answer"],
                    "confidence_score": confidence_score,
                    "reasoning_steps": state["reasoning_steps"] + [reasoning_step],
                    "completed_agents": state["completed_agents"] + [self.name],
                    "next_agent": "END"
                }
            
            # Otherwise, synthesize information from all agents
            context_info = []
            
            if chat_history:
                context_info.append(f"Conversation context: {len(chat_history)} previous messages analyzed")
            
            if available_documents:
                doc_names = [doc["name"] for doc in available_documents]
                context_info.append(f"Available documents: {', '.join(doc_names[:3])}" + 
                                   (f" and {len(doc_names) - 3} more" if len(doc_names) > 3 else ""))
            
            if document_sources:
                context_info.append(f"Retrieved {len(document_sources)} relevant document chunks")
            
            if general_knowledge_used:
                context_info.append("Used general knowledge as fallback")
            
            # Create comprehensive prompt for final answer
            synthesis_prompt = f"""
            As the orchestrator agent, synthesize information from specialized agents to provide a final answer.
            
            Query: "{query}"
            
            Information gathered:
            {' | '.join(context_info)}
            
            Chat History Context: {len(chat_history)} messages available
            Document Sources: {len(document_sources)} chunks retrieved
            Available Documents: {len(available_documents)} documents
            General Knowledge Used: {general_knowledge_used}
            
            {f'Document Content: {str(document_sources)[:1000]}...' if document_sources else 'No document content available'}
            
            Provide a comprehensive, accurate answer based on the available information.
            Be clear about your sources and confidence level.
            """
            
            response = self.llm.invoke(
                [SystemMessage(content="You are an orchestrator agent responsible for providing final, comprehensive answers."), 
                 HumanMessage(content=synthesis_prompt)],
                config={"callbacks": [callback_handler]}
            )
            
            final_answer = response.content
            
            # Calculate final confidence based on available information
            final_confidence = 0.4  # Base confidence
            if document_sources:
                final_confidence += 0.3
            if chat_history and any(keyword in query.lower() for keyword in ["it", "that", "the one"]):
                final_confidence += 0.1
            if available_documents and "document" in query.lower():
                final_confidence += 0.2
            
            final_confidence = min(final_confidence, 1.0)
            
            reasoning_step = {
                'id': f'step-{int(time.time() * 1000)}',
                'type': 'orchestrator_synthesis',
                'agent_name': self.name,
                'message': f'{self.name} synthesized final answer',
                'reasoning': f'Coordinated {len(state["completed_agents"])} agents to provide comprehensive answer',
                'final_confidence': final_confidence,
                'timestamp': int(time.time() * 1000)
            }
            
            return {
                "final_answer": final_answer,
                "confidence_score": final_confidence,
                "reasoning_steps": state["reasoning_steps"] + [reasoning_step],
                "completed_agents": state["completed_agents"] + [self.name],
                "next_agent": "END"
            }
            
        except Exception as e:
            error_step = {
                'id': f'step-{int(time.time() * 1000)}',
                'type': 'orchestrator_error',
                'agent_name': self.name,
                'message': f'{self.name} encountered an error',
                'error': str(e),
                'timestamp': int(time.time() * 1000)
            }
            
            return {
                "final_answer": "I encountered an error while coordinating the response. Please try again.",
                "confidence_score": 0.1,
                "reasoning_steps": state["reasoning_steps"] + [error_step],
                "completed_agents": state["completed_agents"] + [self.name],
                "next_agent": "END"
            }


class MultiAgentDocumentSystem:
    """Main multi-agent system using LangGraph"""
    
    def __init__(self, model_type: int = 0, model_key: Optional[str] = None):
        self.model_type = model_type
        self.model_key = model_key
        
        #initialize agents
        self.agents = {"DocumentListAgent": DocumentListAgent(model_type, model_key), "ChatHistoryAgent": ChatHistoryAgent(model_type, model_key),
            "DocumentRetrievalAgent": DocumentRetrievalAgent(model_type, model_key),
            "GeneralKnowledgeAgent": GeneralKnowledgeAgent(model_type, model_key),
            "OrchestratorAgent": OrchestratorAgent(model_type, model_key)
        }
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add agent nodes
        workflow.add_node("DocumentListAgent", self._run_document_list_agent)
        workflow.add_node("ChatHistoryAgent", self._run_chat_history_agent)
        workflow.add_node("DocumentRetrievalAgent", self._run_document_retrieval_agent)
        workflow.add_node("GeneralKnowledgeAgent", self._run_general_knowledge_agent)
        workflow.add_node("OrchestratorAgent", self._run_orchestrator_agent)
        
        # Define workflow edges - start with document list to check for document-specific queries
        workflow.set_entry_point("DocumentListAgent")
        
        # Add conditional edges based on next_agent field
        workflow.add_conditional_edges(
            "DocumentListAgent",
            self._route_next_agent,
            {
                "ChatHistoryAgent": "ChatHistoryAgent",
                "DocumentRetrievalAgent": "DocumentRetrievalAgent",
                "OrchestratorAgent": "OrchestratorAgent",
                "END": END
            }
        )
        
        workflow.add_conditional_edges(
            "ChatHistoryAgent",
            self._route_next_agent,
            {
                "DocumentRetrievalAgent": "DocumentRetrievalAgent",
                "GeneralKnowledgeAgent": "GeneralKnowledgeAgent",
                "OrchestratorAgent": "OrchestratorAgent",
                "END": END
            }
        )
        
        workflow.add_conditional_edges(
            "DocumentRetrievalAgent",
            self._route_next_agent,
            {
                "GeneralKnowledgeAgent": "GeneralKnowledgeAgent",
                "OrchestratorAgent": "OrchestratorAgent",
                "END": END
            }
        )
        
        workflow.add_conditional_edges(
            "GeneralKnowledgeAgent",
            self._route_next_agent,
            {
                "OrchestratorAgent": "OrchestratorAgent",
                "END": END
            }
        )
        
        workflow.add_conditional_edges(
            "OrchestratorAgent",
            self._route_next_agent,
            {
                "END": END
            }
        )
        
        return workflow.compile()
    
    def _route_next_agent(self, state: AgentState) -> str:
        """Determine the next agent based on the state"""
        return state.get("next_agent", "END")
    
    # Agent runner methods
    def _run_document_list_agent(self, state: AgentState) -> AgentState:
        result = self.agents["DocumentListAgent"].process(state)
        return {**state, **result}
    
    def _run_chat_history_agent(self, state: AgentState) -> AgentState:
        result = self.agents["ChatHistoryAgent"].process(state)
        return {**state, **result}
    
    def _run_document_retrieval_agent(self, state: AgentState) -> AgentState:
        result = self.agents["DocumentRetrievalAgent"].process(state)
        return {**state, **result}
    
    def _run_general_knowledge_agent(self, state: AgentState) -> AgentState:
        result = self.agents["GeneralKnowledgeAgent"].process(state)
        return {**state, **result}
    
    def _run_orchestrator_agent(self, state: AgentState) -> AgentState:
        result = self.agents["OrchestratorAgent"].process(state)
        return {**state, **result}
    
    def process_query_stream(self, query: str, chat_id: int, user_email: str) -> Generator[Dict[str, Any], None, None]:
        """
        Process query using the multi-agent system with streaming
        """
        try:
            # Add user message to database
            add_message_to_db(query, chat_id, 1)
            
            # Yield initial status
            yield {
                "type": "start",
                "message": "Multi-agent system processing your query...",
                "timestamp": self._get_timestamp()
            }
            
            # Create stream callback
            def stream_callback(event):
                return event
            
            # Initialize state
            initial_state = AgentState(
                query=query,
                chat_id=chat_id,
                user_email=user_email,
                messages=[],
                current_step="starting",
                document_sources=[],
                chat_history=[],
                available_documents=[],
                general_knowledge_used=False,
                final_answer="",
                confidence_score=0.5,
                reasoning_steps=[],
                next_agent="DocumentListAgent",
                completed_agents=[],
                stream_callback=stream_callback
            )
            
            # Process through the workflow
            streaming_events = []
            
            # Execute the workflow
            try:
                final_state = None
                for state_update in self.workflow.stream(initial_state):
                    # Each state_update is a dict with node_name -> new_state
                    for node_name, new_state in state_update.items():
                        final_state = new_state
                        
                        # Yield progress update
                        yield {
                            "type": "agent_progress",
                            "current_agent": node_name,
                            "completed_agents": new_state.get("completed_agents", []),
                            "message": f"{node_name} completed processing",
                            "timestamp": self._get_timestamp()
                        }
                        
                        # Yield any reasoning steps that were added
                        reasoning_steps = new_state.get("reasoning_steps", [])
                        for step in reasoning_steps[-1:]:  # Only yield the latest step
                            yield {
                                "type": "reasoning_step",
                                "step": step,
                                "timestamp": self._get_timestamp()
                            }
                
                if not final_state:
                    raise Exception("Workflow execution failed - no final state returned")
                
                # Extract final results
                final_answer = final_state.get("final_answer", "I couldn't process your query.")
                document_sources = final_state.get("document_sources", [])
                confidence_score = final_state.get("confidence_score", 0.5)
                reasoning_steps = final_state.get("reasoning_steps", [])
                
                # Yield completion event
                yield {
                    "type": "complete",
                    "answer": final_answer,
                    "sources": document_sources,
                    "confidence": confidence_score,
                    "total_agents_used": len(final_state.get("completed_agents", [])),
                    "timestamp": self._get_timestamp()
                }
                
                # Yield step-complete event for frontend
                yield {
                    "type": "step-complete",
                    "answer": final_answer,
                    "sources": document_sources,
                    "thought": f"Multi-agent system coordinated {len(final_state.get('completed_agents', []))} agents",
                    "timestamp": self._get_timestamp()
                }
                
                # Save to database
                reasoning_json = json.dumps(reasoning_steps) if reasoning_steps else None
                message_id = add_message_to_db(final_answer, chat_id, 0, reasoning_json)
                
                if document_sources and message_id:
                    try:
                        add_sources_to_db(message_id, document_sources)
                    except Exception as e:
                        print(f"Error adding sources to db: {e}")
                
                # Yield final result
                yield {
                    "type": "response-complete",
                    "answer": final_answer,
                    "message_id": message_id,
                    "sources": document_sources,
                    "message": "Multi-agent processing completed successfully",
                    "total_agents": len(final_state.get("completed_agents", [])),
                    "confidence_score": confidence_score,
                    "timestamp": self._get_timestamp()
                }
                
            except Exception as e:
                error_msg = f"Multi-agent system error: {str(e)}"
                print(f"Workflow error: {e}")
                yield {
                    "type": "error",
                    "error": error_msg,
                    "timestamp": self._get_timestamp()
                }
                
        except Exception as e:
            error_msg = f"Multi-agent initialization error: {str(e)}"
            message_id = add_message_to_db(error_msg, chat_id, 0)
            print(f"Initialization error: {e}")
            yield {
                "type": "error",
                "error": error_msg,
                "message_id": message_id,
                "timestamp": self._get_timestamp()
            }
    
    @staticmethod
    def _get_timestamp():
        return time.time()