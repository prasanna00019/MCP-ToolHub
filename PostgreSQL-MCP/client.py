import asyncio
import json
import os
import re
from contextlib import AsyncExitStack
from pathlib import Path

import httpx
import ollama
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()  # load environment variables from .env

# Ollama model constant
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-v3.2:cloud")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Logging setup
LOG_FILE = "mcp_client_debug.log"

def log_message(message: str, log_type: str = "INFO"):
    """Write message to both console and log file"""
    timestamp = __import__('datetime').datetime.now().isoformat()
    formatted_msg = f"[{timestamp}] [{log_type}] {message}"
    try:
        print(formatted_msg)
    except UnicodeEncodeError:
        print(formatted_msg.encode('utf-8', errors='replace').decode('utf-8'))
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted_msg + "\n")


class MCPClient:
    def __init__(self, use_tools: bool = True):
        # Initialize session and client objects
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()
        # Initialize Ollama client with custom host
        self.ollama_client = ollama.Client(host=OLLAMA_BASE_URL)
        self.use_tools = use_tools

    async def get_available_models(self) -> list[str]:
        """Fetch available models from Ollama server"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
                response.raise_for_status()
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                return models
        except Exception as e:
            print(f"Error fetching models: {e}")
            return []

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        if is_python:
            path = Path(server_script_path).resolve()
            server_params = StdioServerParameters(
                command="uv",
                args=["--directory", str(path.parent), "run", path.name],
                env=None,
            )
        else:
            server_params = StdioServerParameters(command="node", args=[server_script_path], env=None)

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Ollama and MCP tools"""
        log_message(f"Processing query: {query}", "QUERY")
        log_message(f"Use tools: {self.use_tools}", "CONFIG")
        
        # Get available tools
        response = await self.session.list_tools()
        available_tools = response.tools
        log_message(f"Available tools: {[t.name for t in available_tools]}", "TOOLS")
        
        if not self.use_tools:
            log_message("Tools are disabled - LLM will answer without using tools", "CONFIG")
            # Single turn without tools
            messages = [
                {"role": "user", "content": query}
            ]
            
            response = self.ollama_client.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                stream=False
            )
            
            if response.get("message"):
                response_text = response["message"]["content"]
                log_message(f"LLM response (no tools): {response_text[:500]}...", "LLM_RESPONSE")
                return response_text
            return "No response from model"
        
        # Build tool descriptions for the system prompt (with tools enabled)
        tools_description = "\n".join([
            f"- {tool.name}: {tool.description}\n  Input schema: {json.dumps(tool.inputSchema)}"
            for tool in available_tools
        ])
        
        # System prompt that instructs model to use tools
        system_prompt = f"""You are a helpful assistant with access to the following tools:

{tools_description}

When you need to use a tool, format it as: [TOOL: tool_name with args: {{json_args}}]
After using a tool, you will receive the result and can continue your response.
Always try to use the appropriate tools to answer user questions accurately."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
        
        final_text = []
        max_iterations = 15  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            log_message(f"Iteration {iteration}/{max_iterations}", "ITERATION")
            
            # Call Ollama
            log_message(f"Calling Ollama API with model: {OLLAMA_MODEL}", "API_CALL")
            response = self.ollama_client.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                stream=False
            )
            log_message(f"Ollama response received", "API_RESPONSE")
            
            if not response.get("message"):
                log_message("No message in response", "ERROR")
                break
                
            response_text = response["message"]["content"]
            log_message(f"Model response: {response_text[:200]}...", "MODEL_RESPONSE")
            
            # Look for tool calls in format [TOOL: name with args: {...}]
            tool_pattern = r'\[TOOL:\s*([\w_]+)\s+with\s+args:\s*({.*?})\]'
            matches = re.findall(tool_pattern, response_text, re.DOTALL)
            log_message(f"Found {len(matches)} tool calls", "TOOL_DETECT")
            
            if matches:
                # Remove tool call patterns from display text
                display_text = re.sub(tool_pattern, '', response_text).strip()
                if display_text:
                    final_text.append(display_text)
                
                # Execute tool calls
                tool_results = []
                for tool_name, args_json in matches:
                    try:
                        args = json.loads(args_json)
                        log_message(f"Calling tool: {tool_name} with args: {json.dumps(args)}", "TOOL_CALL")
                        result = await self.session.call_tool(tool_name, args)
                        tool_output = str(result.content)
                        log_message(f"Tool '{tool_name}' returned: {tool_output[:500]}...", "TOOL_RESULT")
                        tool_results.append(f"Tool '{tool_name}' result: {result.content}")
                    except json.JSONDecodeError as e:
                        log_message(f"Error parsing args for {tool_name}: {e}", "ERROR")
                    except Exception as e:
                        log_message(f"Error calling tool {tool_name}: {e}", "ERROR")
                
                # Add tool results to messages and continue conversation
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "user", "content": "\n".join(tool_results) if tool_results else "Tool execution failed"})
            else:
                # No tool calls, just return the response
                log_message("No tool calls detected, returning response", "COMPLETION")
                final_text.append(response_text)
                break
        
        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script> [--no-tools]")
        print("  --no-tools: Disable MCP tools, LLM answers without tools")
        sys.exit(1)

    # Check for --no-tools flag
    use_tools = True
    if "--no-tools" in sys.argv:
        use_tools = False
        sys.argv.remove("--no-tools")

    # Clear log file at start
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")
    
    log_message("MCP Client started", "START")
    log_message(f"Ollama Base URL: {OLLAMA_BASE_URL}", "CONFIG")
    log_message(f"Model: {OLLAMA_MODEL}", "CONFIG")
    log_message(f"Tools enabled: {use_tools}", "CONFIG")
    
    client = MCPClient(use_tools=use_tools)
    try:
        # Show available models
        print(f"Connecting to Ollama at {OLLAMA_BASE_URL}...")
        log_message(f"Fetching available models from {OLLAMA_BASE_URL}", "MODELS")
        models = await client.get_available_models()
        if models:
            log_message(f"Available models: {models}", "MODELS")
            print(f"Available models: {', '.join(models)}")
            if OLLAMA_MODEL not in models:
                log_message(f"WARNING: Model '{OLLAMA_MODEL}' not found!", "WARNING")
                print(f"⚠️  WARNING: Model '{OLLAMA_MODEL}' not found!")
                print(f"Using first available model instead: {models[0]}")
                globals()['OLLAMA_MODEL'] = models[0]
        else:
            log_message("Could not fetch available models", "ERROR")
            print("Could not fetch available models")
        
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        log_message("MCP Client cleanup", "SHUTDOWN")
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())