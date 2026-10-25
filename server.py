"""MCP Inspector entry point."""
from boost_agent.server import create_server

mcp = create_server()

if __name__ == "__main__":
    mcp.run()
