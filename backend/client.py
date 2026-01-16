"""
Complete MCP Client with support for multiple transports
Connects to remote MCP servers like MintMCP with authentication
"""

import json
from typing import Optional, List, Dict, Any, Literal
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.sse import sse_client
import asyncio
from pydantic import BaseModel, AnyUrl

class ToolFunction(BaseModel):
    name: str
    description: str | None = None
    parameters: Dict[str, Any]

class Tool(BaseModel):
    type: Literal["function"] = "function"
    function: ToolFunction


class Resource(BaseModel):
    uri: AnyUrl
    name: str
    description: str | None = None
    mimeType: str | None = None

class Prompt(BaseModel):
    name: str
    description: str | None


class Capabilities(BaseModel):
    tools: List[Tool]
    resources: List[Resource]
    prompts: List[Prompt]

class UniversalMCPClient:
    """
    Universal MCP client supporting both Streamable HTTP and SSE transports.
    Automatically detects and uses the appropriate transport.
    """
    
    def __init__(
        self,
        server_url: str,
        transport: Literal["streamable-http", "sse", "auto"] = "auto",
        headers: Optional[Dict[str, str]] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize the universal MCP client.
        
        Args:
            server_url: URL to the MCP server
                       For streamable-http: https://server.com/mcp
                       For SSE: https://server.com/sse
            transport: Transport type to use ("streamable-http", "sse", or "auto")
            headers: Additional headers for authentication
            api_key: API key for authentication (will be added to headers)
        """
        self.server_url = server_url
        self.transport = transport
        self.headers = headers or {}
        
        # Add API key to headers if provided
        if api_key:
            self.headers["authorization"] = f"Bearer {api_key}"
        
        self.session: Optional[ClientSession] = None
        self.tools: List[Tool] = []
        self.resources: List[Resource] = []
        self.prompts: List[Prompt] = []
        self.client_context = None
        self.session_context = None
        self.detected_transport = None
        
    def _detect_transport(self) -> str:
        """Auto-detect transport based on URL"""
        if self.transport != "auto":
            return self.transport
        
        # Simple URL-based detection
        if "/sse" in self.server_url:
            return "sse"
        elif "/mcp" in self.server_url:
            return "streamable-http"
        else:
            # Default to streamable-http for modern servers
            return "streamable-http"
    
    async def connect(self):
        """Establish connection using appropriate transport"""
        self.detected_transport = self._detect_transport()
        
        print(f"Connecting to MCP server...") 
        print(f"URL: {self.server_url}")
        print(f"Transport: {self.detected_transport}")
        
        try:
            if self.detected_transport == "streamable-http":
                await self._connect_streamable_http()
            else:
                await self._connect_sse()
            
            print("✓ Connected successfully")
            
            # Load server capabilities
            await self.refresh_capabilities()
            
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            raise

    
    async def _connect_streamable_http(self):
        """Connect using Streamable HTTP transport"""
        self.client_context = streamablehttp_client(
            self.server_url,
            headers=self.headers if self.headers else None
        )
        
        read_stream, write_stream, _ = await self.client_context.__aenter__()
        self.session_context = ClientSession(read_stream, write_stream)
        self.session = await self.session_context.__aenter__()
        await self.session.initialize()
    
    async def _connect_sse(self):
        """Connect using SSE transport"""
        self.client_context = sse_client(self.server_url, headers=self.headers)
        
        read_stream, write_stream = await self.client_context.__aenter__()
        self.session_context = ClientSession(read_stream, write_stream)
        self.session = await self.session_context.__aenter__()
        await self.session.initialize()
    
    async def refresh_capabilities(self):
        """Fetch all server capabilities (tools, resources, prompts)"""
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")
        
        print("\nFetching server capabilities...")
        
        # Fetch tools
        try:
            tools_response = await self.session.list_tools()
            self.tools = [
                Tool(
                    function=ToolFunction(
                    name=tool.name,
                    description=tool.description,
                    parameters=tool.inputSchema,
                    )   
                )
                for tool in tools_response.tools
            ]
            print(f"  ✓ Tools: {len(self.tools)}")
        except Exception as e:
            print(f"  ✗ Tools: {e}")
        
        # Fetch resources
        try:
            resources_response = await self.session.list_resources()
            self.resources = [
                Resource(
                    uri=resource.uri,
                    name=resource.name,
                    description=resource.description,
                    mimeType=resource.mimeType
                )
                for resource in resources_response.resources
            ]
            print(f"  ✓ Resources: {len(self.resources)}")
        except Exception as e:
            print(f"  ✗ Resources: {e}")
        
        # Fetch prompts
        try:
            prompts_response = await self.session.list_prompts()
            self.prompts = [
                Prompt(
                    name=prompt.name,
                    description=prompt.description,
                )
                for prompt in prompts_response.prompts
            ]
            print(f"  ✓ Prompts: {len(self.prompts)}")
        except Exception as e:
            print(f"  ✗ Prompts: {e}")
    
    def get_capabilities(self):
        """
        list in object of tools, resources, and prompts
        
        Returns: 
            object of tools, resources, and prompts
        """
        return Capabilities(
            tools=self.tools or [],
            resources=self.resources or [],
            prompts=self.prompts or []
        )
    

    def get_tool(self, tool_name: str) -> Optional[Tool]:
       """
       get a tool given a name

        Args:
            tool_name: Name of the tool
       
       Returns:
        Tool or None
       """
       return next(
        (tool for tool in self.tools if tool.function.name == tool_name),
        None
    )

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """
        Execute a tool with given arguments.
        
        Args:
            tool_name: Name of the tool
            arguments: Tool arguments as dictionary
            
        Returns:
            Tool execution result
        """
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")
        
        print(f"\n🔧 Calling tool: {tool_name}")
        print(f"   Arguments: {json.dumps(arguments, indent=2)}")
        
        result = await self.session.call_tool(tool_name, arguments)
        
        print("   ✓ Success")
        return result
    

    async def disconnect(self):
        """Close the connection"""
        if self.session_context:
            await self.session_context.__aexit__(None, None, None)
        if self.client_context:
            await self.client_context.__aexit__(None, None, None)
        print("\n✓ Disconnected")

# """
# MCP Client with proper tool calling loop
# Handles LLM tool requests while keeping MCP connection open
# """

# import json
# from typing import Optional, List, Dict, Any, Literal, cast
# from mcp import ClientSession
# from mcp.client.streamable_http import streamablehttp_client
# from mcp.client.sse import sse_client
# import asyncio
# from openai import OpenAI
# from openai.types.chat import ChatCompletionToolParam, ChatCompletionMessageParam, ChatCompletionAssistantMessageParam


# class UniversalMCPClient:
#     """
#     Universal MCP client supporting both Streamable HTTP and SSE transports.
#     Automatically detects and uses the appropriate transport.
#     """
    
#     def __init__(
#         self,
#         server_url: str,
#         transport: Literal["streamable-http", "sse", "auto"] = "auto",
#         headers: Optional[Dict[str, str]] = None,
#         api_key: Optional[str] = None
#     ):
#         """
#         Initialize the universal MCP client.
        
#         Args:
#             server_url: URL to the MCP server
#             transport: Transport type to use ("streamable-http", "sse", or "auto")
#             headers: Additional headers for authentication
#             api_key: API key for authentication (will be added to headers)
#         """
#         self.server_url = server_url
#         self.transport = transport
#         self.headers = headers or {}
        
#         # Add API key to headers if provided
#         if api_key:
#             self.headers["authorization"] = f"Bearer {api_key}"
        
#         self.session: Optional[ClientSession] = None
#         self.tools: List[Dict[str, Any]] = []
#         self.resources: List[Dict[str, Any]] = []
#         self.prompts: List[Dict[str, Any]] = []
#         self.client_context = None
#         self.session_context = None
#         self.detected_transport = None
        
#     def _detect_transport(self) -> str:
#         """Auto-detect transport based on URL"""
#         if self.transport != "auto":
#             return self.transport
        
#         if "/sse" in self.server_url:
#             return "sse"
#         elif "/mcp" in self.server_url:
#             return "streamable-http"
#         else:
#             return "streamable-http"
    
#     async def connect(self):
#         """Establish connection using appropriate transport"""
#         self.detected_transport = self._detect_transport()
        
#         print(f"🔌 Connecting to MCP server...") 
#         print(f"   URL: {self.server_url}")
#         print(f"   Transport: {self.detected_transport}")
        
#         try:
#             if self.detected_transport == "streamable-http":
#                 await self._connect_streamable_http()
#             else:
#                 await self._connect_sse()
            
#             print("   ✓ Connected successfully")
            
#             # Load server capabilities
#             await self.refresh_capabilities()
            
#         except Exception as e:
#             print(f"   ✗ Connection failed: {e}")
#             raise
    
#     async def _connect_streamable_http(self):
#         """Connect using Streamable HTTP transport"""
#         self.client_context = streamablehttp_client(
#             self.server_url,
#             headers=self.headers if self.headers else None
#         )
        
#         read_stream, write_stream, _ = await self.client_context.__aenter__()
#         self.session_context = ClientSession(read_stream, write_stream)
#         self.session = await self.session_context.__aenter__()
#         await self.session.initialize()
    
#     async def _connect_sse(self):
#         """Connect using SSE transport"""
#         self.client_context = sse_client(self.server_url, headers=self.headers)
        
#         read_stream, write_stream = await self.client_context.__aenter__()
#         self.session_context = ClientSession(read_stream, write_stream)
#         self.session = await self.session_context.__aenter__()
#         await self.session.initialize()
    
#     async def refresh_capabilities(self):
#         """Fetch all server capabilities (tools, resources, prompts)"""
#         if not self.session:
#             raise RuntimeError("Not connected. Call connect() first.")
        
#         print("\n📦 Fetching server capabilities...")
        
#         # Fetch tools
#         try:
#             tools_response = await self.session.list_tools()
#             self.tools = [
#                 {
#                     "type": "function",
#                     "function": {
#                         "name": tool.name,
#                         "description": tool.description,
#                         "parameters": tool.inputSchema
#                     }
#                 }
#                 for tool in tools_response.tools
#             ]
#             print(f"   ✓ Tools: {len(self.tools)}")
#         except Exception as e:
#             print(f"   ✗ Tools: {e}")
        
#         # Fetch resources
#         try:
#             resources_response = await self.session.list_resources()
#             self.resources = [
#                 {
#                     "uri": resource.uri,
#                     "name": resource.name,
#                     "description": resource.description,
#                     "mimeType": resource.mimeType
#                 }
#                 for resource in resources_response.resources
#             ]
#             print(f"   ✓ Resources: {len(self.resources)}")
#         except Exception as e:
#             print(f"   ✗ Resources: {e}")
        
#         # Fetch prompts
#         try:
#             prompts_response = await self.session.list_prompts()
#             self.prompts = [
#                 {
#                     "name": prompt.name,
#                     "description": prompt.description,
#                 }
#                 for prompt in prompts_response.prompts
#             ]
#             print(f"   ✓ Prompts: {len(self.prompts)}")
#         except Exception as e:
#             print(f"   ✗ Prompts: {e}")
    
#     def get_capabilities(self):
#         """
#         Get tools, resources, and prompts
        
#         Returns: 
#             Dict with tools, resources, and prompts
#         """
#         return {
#             "tools": self.tools or [],
#             "resources": self.resources or [],
#             "prompts": self.prompts or []
#         }

    
#     async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
#         """
#         Execute a tool with given arguments.
        
#         Args:
#             tool_name: Name of the tool
#             arguments: Tool arguments as dictionary
            
#         Returns:
#             Tool execution result as string
#         """
#         if not self.session:
#             raise RuntimeError("Not connected. Call connect() first.")
        
#         print(f"\n🔧 Calling tool: {tool_name}")
#         print(f"   Arguments: {json.dumps(arguments, indent=2)}")
        
#         result = await self.session.call_tool(tool_name, arguments)
        
#         # Extract text content from result
#         content_parts = []
#         for content in result.content:
#             if hasattr(content, 'text'):
#                 content_parts.append(content.text)
#             else:
#                 # Handle other content types (images, etc.)
#                 content_parts.append(str(content))
        
#         result_text = "\n".join(content_parts)
#         print(f"   ✓ Success ({len(result_text)} chars)")
        
#         return result_text
    
#     async def disconnect(self):
#         """Close the connection"""
#         if self.session_context:
#             await self.session_context.__aexit__(None, None, None)
#         if self.client_context:
#             await self.client_context.__aexit__(None, None, None)
#         print("\n✓ Disconnected from MCP server")


# async def chat_with_tools(mcp: UniversalMCPClient, llm_client: OpenAI, user_input: str):
#     """
#     Handle a chat conversation with tool calling
#     Keeps MCP connection open throughout the conversation
#     """
    
#     # Get available tools
#     capabilities = mcp.get_capabilities()
#     tools = cast(List[ChatCompletionToolParam], capabilities.get("tools", []))

#     print(f"\n💬 Starting chat with {len(tools)} tools available")
    
#     # Initialize conversation
#     messages: List[ChatCompletionMessageParam] = [{"role": "user", "content": user_input}]
    
#     # Tool calling loop - keep trying until LLM stops requesting tools
#     max_iterations = 10
#     iteration = 0
    
#     while iteration < max_iterations:
#         iteration += 1
#         print(f"\n{'='*70}")
#         print(f"ITERATION {iteration}")
#         print('='*70)
        
#         # Call LLM
#         print("\n🤖 Calling LLM...")
#         response = llm_client.chat.completions.create(
#             model="openai/gpt-oss-120b",  # Or your preferred model
#             tools=tools,
#             messages=messages,
#         )
        
#         message = response.choices[0].message
        
#         # Check if LLM wants to call tools
#         if message.tool_calls:
#             print(f"\n🔧 LLM requested {len(message.tool_calls)} tool call(s)")
            
#             # Add assistant message to conversation
#             assistant_message: ChatCompletionAssistantMessageParam = {
#                 "role": "assistant",
#                 "content": message.content or "",
#                 "tool_calls": [
#                     {
#                         "id": tc.id,
#                         "type": tc.type,
#                         "function": {
#                             "name": tc.function.name,
#                             "arguments": tc.function.arguments
#                         }
#                     }
#                     for tc in message.tool_calls
#                 ]
#             }
#             messages.append(assistant_message)
            
#             # Execute each tool call
#             for tool_call in message.tool_calls:
#                 tool_name = tool_call.function.name
                
#                 try:
#                     # Parse arguments
#                     arguments = json.loads(tool_call.function.arguments)
                    
#                     # Call the MCP tool (connection stays open!)
#                     tool_result = await mcp.call_tool(tool_name, arguments)
                    
#                     # Add tool result to conversation
#                     messages.append({
#                         "role": "tool",
#                         "tool_call_id": tool_call.id,
#                         "content": tool_result
#                     })
                    
#                 except Exception as e:
#                     print(f"   ✗ Tool call failed: {e}")
#                     # Add error to conversation
#                     messages.append({
#                         "role": "tool",
#                         "tool_call_id": tool_call.id,
#                         "content": f"Error: {str(e)}"
#                     })
            
#             # Continue loop to let LLM process tool results
#             continue
        
#         else:
#             # LLM finished - no more tool calls
#             print("\n✅ LLM finished (no more tool calls)")
#             print("\n" + "="*70)
#             print("FINAL RESPONSE")
#             print("="*70)
#             print(message.content)
#             break
    
#     if iteration >= max_iterations:
#         print("\n⚠️  Max iterations reached")


# async def interactive_loop(mcp: UniversalMCPClient):
#     """
#     Interactive chat loop - keeps MCP connection open for multiple queries
#     """
#     from dotenv import load_dotenv
#     import os
    
#     load_dotenv()
    
#     # Setup LLM client
#     llm_client = OpenAI(
#         base_url="https://openrouter.ai/api/v1",
#         api_key=os.getenv("OPENROUTER_TOKEN")
#     )
    
#     print("\n" + "="*70)
#     print("INTERACTIVE CHAT WITH MCP TOOLS")
#     print("="*70)
#     print("Type 'quit' or 'exit' to end the session")
#     print("Connection stays open between queries for better performance")
#     print("="*70)
    
#     while True:
#         try:
#             # Get user input
#             user_input = input("\n💭 You: ").strip()
            
#             if user_input.lower() in ['quit', 'exit', 'q']:
#                 print("\n👋 Goodbye!")
#                 break
            
#             if not user_input:
#                 continue
            
#             # Process with tools (MCP stays connected!)
#             await chat_with_tools(mcp, llm_client, user_input)
            
#         except KeyboardInterrupt:
#             print("\n\n👋 Interrupted. Goodbye!")
#             break
#         except Exception as e:
#             print(f"\n❌ Error: {e}")
#             import traceback
#             traceback.print_exc()


# async def single_query_example(mcp: UniversalMCPClient):
#     """
#     Example: Single query with tool calling
#     """
#     from dotenv import load_dotenv
#     import os
    
#     load_dotenv()
    
#     llm_client = OpenAI(
#         base_url="https://openrouter.ai/api/v1",
#         api_key=os.getenv("OPENROUTER_TOKEN")
#     )
    
#     # Single query
#     user_input = "What are my unread emails about?"
    
#     await chat_with_tools(mcp, llm_client, user_input)


# async def main():
#     from dotenv import load_dotenv
#     import os
    
#     load_dotenv()

#     mcp_server = os.getenv("MCP_SERVER")
#     mcp_key = os.getenv("MCP_API_KEY")

#     if not mcp_server:
#         raise Exception("Missing MCP_SERVER url in .env")
    
#     # Create MCP client
#     mcp = UniversalMCPClient(server_url=mcp_server, api_key=mcp_key)

#     try:
#         # Connect once
#         await mcp.connect()
        
#         # Option 1: Single query
#         # await single_query_example(mcp)
        
#         # Option 2: Interactive loop (RECOMMENDED)
#         # Connection stays open for multiple queries
#         await interactive_loop(mcp)
        
#     finally:
#         # Disconnect when done
#         await mcp.disconnect()