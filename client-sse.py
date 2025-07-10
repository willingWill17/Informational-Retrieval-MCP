import asyncio
import json
import base64
from pathlib import Path
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional
import os
import nest_asyncio
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import AsyncOpenAI

# Load environment variables
load_dotenv(".env")

base_url = {
    "gemini-2.5-flash": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "gpt-4o": "https://api.openai.com/v1/",
}

class MCPOpenAIClient:
    """Client for interacting with OpenAI models using MCP tools."""

    def __init__(self, model: str = "gpt-4o"):
        """Initialize the OpenAI MCP client.

        Args:
            model: The OpenAI model to use.
        """
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai_client = AsyncOpenAI(base_url=base_url[os.getenv("LLM_MODEL")], api_key=os.getenv("LLM_API_KEY"))
        self.model = model
        self.stdio: Optional[Any] = None
        self.write: Optional[Any] = None

    async def connect_to_server(self, server_url: str):
        """Connect to an MCP server over SSE.

        Args:
            server_url: The URL of the SSE server.
        """
        try:
            # SSE Client configuration
            (read_stream, write_stream) = await self.exit_stack.enter_async_context(sse_client(url=server_url))

            # Connect to the server
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            # Initialize the connection
            await self.session.initialize()

            # List available tools
            tools_result = await self.session.list_tools()
            print("\nConnected to server with tools:")
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description}")
        except Exception as e:
            print(f"Error connecting to server: {e}")
            raise

    async def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get available tools from the MCP server in OpenAI format.

        Returns:
            A list of tools in OpenAI format.
        """
        try:
            tools_result = await self.session.list_tools()
            tools = []
            
            for tool in tools_result.tools:
                # Fix the parameters schema for OpenAI compatibility
                parameters = tool.inputSchema
                
                # Ensure parameters has the correct structure for OpenAI
                if not parameters or parameters.get('properties') == {}:
                    # For functions with no parameters, use this specific format
                    parameters = {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                else:
                    # Ensure required field exists
                    if 'required' not in parameters:
                        parameters['required'] = []
                
                tool_def = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": parameters,
                    },
                }
                tools.append(tool_def)

            return tools
        except Exception as e:
            print(f"Error getting MCP tools: {e}")
            return []

    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI and available MCP tools.

        Args:
            query: The user query.

        Returns:
            The response from OpenAI.
        """
        try:
            # Get available tools
            tools = await self.get_mcp_tools()
            
            print(f"\nUsing model: {self.model}")
            print(f"Available tools: {len(tools)}")

            # Initial OpenAI API call
            print("Making initial API call...")
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": query}],
                tools=tools,
                tool_choice="auto",
            )

            # Get assistant's response
            assistant_message = response.choices[0].message
            print(f"Assistant response received. Tool calls: {len(assistant_message.tool_calls) if assistant_message.tool_calls else 0}")

            # Initialize conversation with user query and assistant response
            messages = [
                {"role": "user", "content": query},
                assistant_message,
            ]

            # Handle tool calls if present
            if assistant_message.tool_calls:
                # Flag to check if images were processed
                images_processed = False

                # Process each tool call
                for tool_call in assistant_message.tool_calls:
                    print(f"Executing tool: {tool_call.function.name}")
                    result = await self.session.call_tool(
                        tool_call.function.name,
                        arguments=json.loads(tool_call.function.arguments),
                    )
                    
                    tool_output = result.content[0].text
                    
                    # Handle image output from get_knowledge_base
                    if tool_call.function.name == "get_knowledge_base":
                        try:
                            data = json.loads(tool_output)
                            if "relevant_images" in data:
                                image_content = []
                                for img_data in data["relevant_images"]:
                                    img_path = Path(img_data["path"])
                                    if img_path.exists():
                                        with open(img_path, "rb") as image_file:
                                            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                                        image_content.append({
                                            "type": "image_url",
                                            "image_url": {"url": f"data:image/png;base64,{encoded_string}"}
                                        })
                                
                                if image_content:
                                    # Create a new message list for the vision call
                                    messages = [
                                        {
                                            "role": "user",
                                            "content": [
                                                {"type": "text", "text": "Based on these document pages, please answer the following query: " + query},
                                                *image_content
                                            ]
                                        }
                                    ]
                                    images_processed = True
                                    # Since we have images, we will make a special call below and exit the tool loop
                                    break 
                                    
                        except (json.JSONDecodeError, KeyError) as e:
                            print(f"Could not parse image data from tool: {e}")
                            # Fallback to appending raw tool output if parsing fails
                            messages.append({
                                "role": "tool", "tool_call_id": tool_call.id, "content": tool_output
                            })
                            
                    else:
                        # Append standard tool response for other tools
                        messages.append({
                            "role": "tool", "tool_call_id": tool_call.id, "content": tool_output
                        })
                
                # Make the final API call
                if images_processed:
                    print("Making final API call with image data...")
                    # No tool choice for the vision call
                    final_response = await self.openai_client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                    )
                else:
                    print("Making final API call with standard tool results...")
                    final_response = await self.openai_client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=tools,
                        tool_choice="none",
                    )

                return final_response.choices[0].message.content

            # No tool calls, just return the direct response
            print("No tool calls made by the model")
            return assistant_message.content

        except Exception as e:
            print(f"Error in process_query: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            return f"Error processing query: {str(e)}"

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


async def main():
    """Main entry point for the client."""
    client = MCPOpenAIClient(model=os.getenv("LLM_MODEL"))
    
    try:
        await client.connect_to_server("http://0.0.0.0:8050/sse")
        query = "What is policy optimization?"
        print(f"\nQuery: {query}")
        response = await client.process_query(query)
        print(f"\nResponse: {response}")
                
    except Exception as e:
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Properly cleanup async resources
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())