import os
from typing import Dict, Any

class AgentConfig:
    """Configuration settings for the reactive agent system"""
    
    # Agent behavior settings
    ENABLE_AGENTS = os.getenv("ENABLE_AGENTS", "true").lower() == "true"
    AGENT_FALLBACK_ENABLED = os.getenv("AGENT_FALLBACK_ENABLED", "true").lower() == "true"
    ENABLE_GENERAL_KNOWLEDGE = os.getenv("ENABLE_GENERAL_KNOWLEDGE", "true").lower() == "true"
    ENABLE_MULTI_AGENT_SYSTEM = os.getenv("ENABLE_MULTI_AGENT_SYSTEM", "true").lower() == "true"
    
    # MCP Server settings
    MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
    MCP_SERVER_TIMEOUT = int(os.getenv("MCP_SERVER_TIMEOUT", "30"))
    
    # Agent model settings
    DEFAULT_AGENT_MODEL_TYPE = int(os.getenv("DEFAULT_AGENT_MODEL_TYPE", "0"))  # 0=OpenAI, 1=Anthropic
    AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.1"))
    AGENT_MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "5"))
    
    # Document retrieval settings
    DEFAULT_CHUNK_RETRIEVAL_COUNT = int(os.getenv("DEFAULT_CHUNK_RETRIEVAL_COUNT", "6"))
    MAX_CHUNK_RETRIEVAL_COUNT = int(os.getenv("MAX_CHUNK_RETRIEVAL_COUNT", "10"))
    
    # Logging and debugging
    ENABLE_AGENT_VERBOSE = os.getenv("ENABLE_AGENT_VERBOSE", "true").lower() == "true"
    LOG_AGENT_REASONING = os.getenv("LOG_AGENT_REASONING", "false").lower() == "true"
    
    @classmethod
    def get_agent_config(cls) -> Dict[str, Any]:
        """Get all agent configuration as a dictionary"""
        return {
            "enable_agents": cls.ENABLE_AGENTS,
            "fallback_enabled": cls.AGENT_FALLBACK_ENABLED,
            "enable_general_knowledge": cls.ENABLE_GENERAL_KNOWLEDGE,
            "enable_multi_agent": cls.ENABLE_MULTI_AGENT_SYSTEM,
            "mcp_server_url": cls.MCP_SERVER_URL,
            "mcp_timeout": cls.MCP_SERVER_TIMEOUT,
            "default_model_type": cls.DEFAULT_AGENT_MODEL_TYPE,
            "temperature": cls.AGENT_TEMPERATURE,
            "max_iterations": cls.AGENT_MAX_ITERATIONS,
            "default_chunk_count": cls.DEFAULT_CHUNK_RETRIEVAL_COUNT,
            "max_chunk_count": cls.MAX_CHUNK_RETRIEVAL_COUNT,
            "verbose": cls.ENABLE_AGENT_VERBOSE,
            "log_reasoning": cls.LOG_AGENT_REASONING
        }
    
    @classmethod
    def is_agent_enabled(cls) -> bool:
        """Check if agents are enabled"""
        return cls.ENABLE_AGENTS
    
    @classmethod
    def should_use_fallback(cls) -> bool:
        """Check if fallback to original implementation is enabled"""
        return cls.AGENT_FALLBACK_ENABLED
    
    @classmethod
    def is_general_knowledge_enabled(cls) -> bool:
        """Check if general knowledge fallback is enabled"""
        return cls.ENABLE_GENERAL_KNOWLEDGE
    
    @classmethod
    def is_multi_agent_enabled(cls) -> bool:
        """Check if multi-agent system is enabled"""
        return cls.ENABLE_MULTI_AGENT_SYSTEM