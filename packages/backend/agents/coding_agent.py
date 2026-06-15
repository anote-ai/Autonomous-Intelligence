"""LangChain coding agent with file system tools."""
from __future__ import annotations

import os
from pathlib import Path


def run_coding_agent(prompt: str, cwd: str = ".") -> str:
    """Run a coding agent on the given prompt."""
    try:
        from langchain.agents import AgentExecutor, create_tool_calling_agent
        from langchain.tools import tool
        from langchain_anthropic import ChatAnthropic
        from langchain_core.prompts import ChatPromptTemplate
        from pydantic import SecretStr

        @tool
        def read_file(path: str) -> str:
            """Read a file from the workspace."""
            full_path = Path(cwd) / path
            if not full_path.exists():
                return f"File not found: {path}"
            return full_path.read_text(encoding="utf-8", errors="ignore")[:10000]

        @tool
        def list_files(directory: str = ".") -> str:
            """List files in a directory."""
            full_path = Path(cwd) / directory
            if not full_path.is_dir():
                return f"Directory not found: {directory}"
            return "\n".join(str(f.relative_to(full_path)) for f in full_path.iterdir())[:2000]

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        llm = ChatAnthropic(model_name="claude-sonnet-4-6", api_key=SecretStr(api_key))  # type: ignore[call-arg]
        tools = [read_file, list_files]
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are an expert coding assistant."),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ])
        agent = create_tool_calling_agent(llm, tools, prompt_template)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=5)
        result = executor.invoke({"input": prompt})
        return result.get("output", "")
    except Exception as exc:
        return f"Agent error: {exc}"
