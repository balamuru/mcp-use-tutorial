"""
LangChain adapter for MCP tools.

This module provides utilities to convert MCP tools to LangChain tools.
"""

from typing import Any, NoReturn

from jsonschema_pydantic import jsonschema_to_pydantic
from langchain_core.tools import BaseTool, ToolException
from mcp.types import CallToolResult, EmbeddedResource, ImageContent, TextContent
from pydantic import BaseModel

from ..connectors.base import BaseConnector
from ..logging import logger


def _parse_mcp_tool_result(tool_result: CallToolResult) -> str:
    """Parse the content of a CallToolResult into a string.

    Args:
        tool_result: The result object from calling an MCP tool.

    Returns:
        A string representation of the tool result content.

    Raises:
        ToolException: If the tool execution failed, returned no content,
                       or contained unexpected content types.
    """
    if tool_result.isError:
        raise ToolException(f"Tool execution failed: {tool_result.content}")

    if not tool_result.content:
        raise ToolException("Tool execution returned no content")

    decoded_result = ""
    for item in tool_result.content:
        match item.type:
            case "text":
                item: TextContent
                decoded_result += item.text
            case "image":
                item: ImageContent
                decoded_result += item.data  # Assuming data is string-like or base64
            case "resource":
                resource: EmbeddedResource = item.resource
                if hasattr(resource, "text"):
                    decoded_result += resource.text
                elif hasattr(resource, "blob"):
                    # Assuming blob needs decoding or specific handling; adjust as needed
                    decoded_result += (
                        resource.blob.decode()
                        if isinstance(resource.blob, bytes)
                        else str(resource.blob)
                    )
                else:
                    raise ToolException(f"Unexpected resource type: {resource.type}")
            case _:
                raise ToolException(f"Unexpected content type: {item.type}")

    return decoded_result


class LangChainAdapter:
    """Adapter for converting MCP tools to LangChain tools."""

    def __init__(self, disallowed_tools: list[str] | None = None) -> None:
        """Initialize a new LangChain adapter.

        Args:
            disallowed_tools: List of tool names that should not be available.
        """
        self.disallowed_tools = disallowed_tools or []
        self._connector_tool_map: dict[BaseConnector, list[BaseTool]] = {}

    def fix_schema(self, schema: dict) -> dict:
        """Convert JSON Schema 'type': ['string', 'null'] to 'anyOf' format.

        Args:
            schema: The JSON schema to fix.

        Returns:
            The fixed JSON schema.
        """
        if isinstance(schema, dict):
            if "type" in schema and isinstance(schema["type"], list):
                schema["anyOf"] = [{"type": t} for t in schema["type"]]
                del schema["type"]  # Remove 'type' and standardize to 'anyOf'
            for key, value in schema.items():
                schema[key] = self.fix_schema(value)  # Apply recursively
        return schema

    async def load_tools_for_connector(self, connector: BaseConnector) -> list[BaseTool]:
        """Dynamically load tools for a specific connector.

        Args:
            connector: The connector to load tools for.

        Returns:
            The list of tools that were loaded.
        """
        # Check if we already have tools for this connector
        if connector in self._connector_tool_map:
            logger.debug(
                f"Returning {len(self._connector_tool_map[connector])} existing tools for connector"
            )
            return self._connector_tool_map[connector]

        # Create tools for this connector
        connector_tools = []

        # Make sure the connector is initialized and has tools
        if not hasattr(connector, "tools") or not connector.tools:
            logger.debug("Connector doesn't have tools, initializing it")
            try:
                await connector.initialize()
            except Exception as e:
                logger.error(f"Error initializing connector: {e}")
                return []

        # Now create tools for each MCP tool
        for tool in connector.tools:
            # Skip disallowed tools
            if tool.name in self.disallowed_tools:
                continue

            class McpToLangChainAdapter(BaseTool):
                name: str = tool.name or "NO NAME"
                description: str = tool.description or ""
                # Convert JSON schema to Pydantic model for argument validation
                args_schema: type[BaseModel] = jsonschema_to_pydantic(
                    self.fix_schema(tool.inputSchema)  # Apply schema conversion
                )
                tool_connector: BaseConnector = connector  # Renamed variable to avoid name conflict
                handle_tool_error: bool = True

                def _run(self, **kwargs: Any) -> NoReturn:
                    """Synchronous run method that always raises an error.

                    Raises:
                        NotImplementedError: Always raises this error because MCP tools
                            only support async operations.
                    """
                    raise NotImplementedError("MCP tools only support async operations")

                async def _arun(self, **kwargs: Any) -> Any:
                    """Asynchronously execute the tool with given arguments.

                    Args:
                        kwargs: The arguments to pass to the tool.

                    Returns:
                        The result of the tool execution.

                    Raises:
                        ToolException: If tool execution fails.
                    """
                    logger.debug(f'MCP tool: "{self.name}" received input: {kwargs}')

                    try:
                        tool_result: CallToolResult = await self.tool_connector.call_tool(
                            self.name, kwargs
                        )
                        try:
                            # Use the helper function to parse the result
                            return _parse_mcp_tool_result(tool_result)
                        except Exception as e:
                            # Log the exception for debugging
                            logger.error(f"Error parsing tool result: {e}")
                            # Shortened line:
                            return (
                                f"Error parsing result: {e!s};"
                                f" Raw content: {tool_result.content!r}"
                            )

                    except Exception as e:
                        if self.handle_tool_error:
                            return f"Error executing MCP tool: {str(e)}"
                        raise

            connector_tools.append(McpToLangChainAdapter())

        # Store the tools for this connector
        self._connector_tool_map[connector] = connector_tools

        # Log available tools for debugging
        logger.debug(
            f"Loaded {len(connector_tools)} new tools for"
            f" connector: {[tool.name for tool in connector_tools]}"
        )

        return connector_tools

    async def create_langchain_tools(self, connectors: list[BaseConnector]) -> list[BaseTool]:
        """Create LangChain tools from MCP tools.

        Args:
            connectors: List of MCP connectors to create tools from.

        Returns:
            A list of LangChain tools that wrap MCP tools.
        """
        tools = []
        for connector in connectors:
            # Create tools for this connector
            connector_tools = await self.load_tools_for_connector(connector)
            tools.extend(connector_tools)

        # Log available tools for debugging
        logger.debug(f"Available tools: {[tool.name for tool in tools]}")
        return tools
