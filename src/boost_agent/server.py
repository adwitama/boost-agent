"""Dependency-free MCP JSON-RPC server over stdio; it never contacts ad platforms."""
from __future__ import annotations
import json
import inspect
import sys
from typing import Any, Callable, get_args, get_origin, get_type_hints
from .errors import PolicyError
from .service import BoostService


class ProtocolMCPServer:
    protocol_version = "2024-11-05"

    def __init__(self, state_path: str = "boost_demo.sqlite"):
        self.service = BoostService(state_path)
        self.tools: dict[str, Callable[..., dict[str, Any]]] = {
            "ads.list_managed_hotels": self.service.list_managed_hotels,
            "ads.get_portfolio_campaign_summary": self.service.get_portfolio_campaign_summary,
            "ads.get_campaign_performance": self.service.get_campaign_performance,
            "ads.get_campaign_budget": self.service.get_campaign_budget,
            "book.get_reservations": self.service.get_reservations,
            "book.get_portfolio_retained_outcomes": self.service.get_portfolio_retained_outcomes,
            "growth.calculate_campaign_economics": self.service.calculate_campaign_economics,
            "growth.audit_portfolio": self.service.audit_portfolio,
            "growth.generate_monthly_report": self.service.generate_monthly_report,
            "growth.propose_reallocation": self.service.propose_reallocation,
            "growth.approve_proposal": self.service.approve_proposal,
            "ads.execute_mock_reallocation": self.service.execute_mock_reallocation,
            "growth.get_audit_log": self.service.get_audit_log,
            "growth.reset_demo": self.service.reset_demo,
        }

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method, request_id = request.get("method"), request.get("id")
        if method == "notifications/initialized": return None
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": self.protocol_version, "capabilities": {"tools": {}}, "serverInfo": {"name": "tripla-boost-demo", "version": "0.1.0"}}}
        if method == "tools/list":
            tools = [{"name": name, "description": "Fixture-only tripla Boost DEMO DATA tool.", "inputSchema": self._input_schema(operation)} for name, operation in self.tools.items()]
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
        if method == "tools/call":
            params = request.get("params", {}); name = params.get("name")
            if name not in self.tools: return self._error(request_id, -32602, f"unknown tool: {name}")
            try:
                result = self.tools[name](**params.get("arguments", {}))
                return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}], "structuredContent": result, "isError": False}}
            except (PolicyError, TypeError, ValueError) as exc:
                return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": str(exc)}], "isError": True}}
        return self._error(request_id, -32601, f"method not found: {method}")

    @staticmethod
    def _schema_type(annotation: Any) -> dict[str, Any]:
        origin = get_origin(annotation)
        args = get_args(annotation)
        if origin is list:
            return {"type": "array", "items": ProtocolMCPServer._schema_type(args[0])}
        if origin is not None and type(None) in args:
            non_null = next(arg for arg in args if arg is not type(None))
            return {"anyOf": [ProtocolMCPServer._schema_type(non_null), {"type": "null"}]}
        if annotation is str: return {"type": "string"}
        if annotation is int: return {"type": "integer"}
        if annotation is float: return {"type": "number"}
        if annotation is bool: return {"type": "boolean"}
        return {}

    @classmethod
    def _input_schema(cls, operation: Callable[..., Any]) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        required: list[str] = []
        annotations = get_type_hints(operation)
        for name, parameter in inspect.signature(operation).parameters.items():
            properties[name] = cls._schema_type(annotations.get(name, parameter.annotation))
            if parameter.default is inspect.Parameter.empty:
                required.append(name)
        return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    @staticmethod
    def _read(stream) -> dict[str, Any] | None:
        line = stream.readline()
        if not line: return None
        return json.loads(line.decode("utf-8"))

    @staticmethod
    def _write(stream, response: dict[str, Any]) -> None:
        body = json.dumps(response, ensure_ascii=False).encode("utf-8")
        stream.write(body + b"\n"); stream.flush()

    def run(self) -> None:
        while request := self._read(sys.stdin.buffer):
            response = self.handle(request)
            if response is not None: self._write(sys.stdout.buffer, response)


def create_server(state_path: str = "boost_demo.sqlite"):
    """Build the official SDK server when installed, with local protocol fallback."""
    try:
        from mcp.server import MCPServer as OfficialMCPServer
    except ImportError:
        return ProtocolMCPServer(state_path)

    service = BoostService(state_path)
    app = OfficialMCPServer("tripla-boost-demo", instructions="Fixture-only DEMO DATA. All ad execution is mock-only.")
    operations = {
        "ads.list_managed_hotels": service.list_managed_hotels,
        "ads.get_portfolio_campaign_summary": service.get_portfolio_campaign_summary,
        "ads.get_campaign_performance": service.get_campaign_performance,
        "ads.get_campaign_budget": service.get_campaign_budget,
        "book.get_reservations": service.get_reservations,
        "book.get_portfolio_retained_outcomes": service.get_portfolio_retained_outcomes,
        "growth.calculate_campaign_economics": service.calculate_campaign_economics,
        "growth.audit_portfolio": service.audit_portfolio,
        "growth.generate_monthly_report": service.generate_monthly_report,
        "growth.propose_reallocation": service.propose_reallocation,
        "growth.approve_proposal": service.approve_proposal,
        "ads.execute_mock_reallocation": service.execute_mock_reallocation,
        "growth.get_audit_log": service.get_audit_log,
        "growth.reset_demo": service.reset_demo,
    }
    for tool_name, operation in operations.items():
        app.tool(name=tool_name, description="Fixture-only tripla Boost DEMO DATA tool.")(operation)
    return app


def main() -> None:
    create_server().run()
if __name__ == "__main__": main()
