import httpx
from fastmcp.server.openapi import FastMCPOpenAPI
import yaml 


client = httpx.AsyncClient(base_url="http://localhost:8000")

# Load your OpenAPI spec 

with open("todo.yaml") as file:
    openapi_spec :dict= yaml.safe_load(file)

# Create the MCP server
mcp= FastMCPOpenAPI(
    openapi_spec=openapi_spec,
    client=client,
    name="todo mcp"
)


if __name__=="__main__":
    mcp.run(transport="http",port=8001)

