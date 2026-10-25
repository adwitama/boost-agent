"""Dependency-free MCP JSON-RPC server over stdio; it never contacts ad platforms."""
from __future__ import annotations

import inspect
import json
import sys
from collections.abc import Callable
from typing import Any, get_args, get_origin, get_type_hints

from .errors import PolicyError
from .service import BoostService


def review_managed_portfolio(period: str = "last_30_days") -> str:
    """Build a read-only portfolio review prompt using the selected audit period."""
    return (
        "Review the tripla Boost managed hotel portfolio for DEMO DATA only. "
        f"Use audit period {period}. Call ads.list_managed_hotels, "
        "ads.get_portfolio_campaign_summary, book.get_portfolio_retained_outcomes, "
        "and growth.audit_portfolio. Summarize performance, retained outcomes, "
        "data quality, and the evidence behind each alert. Clearly separate "
        "historical attribution from causal lift; label unmeasured incremental "
        "outcomes NOT YET MEASURED. Do not propose or execute budget changes."
    )


def plan_kyoto_budget_test(
    amount_jpy: str = "30000", variable_cost_ratio: str = "0.30"
) -> str:
    """Build a Kyoto campaign comparison and bounded test planning prompt."""
    return (
        "Evaluate a possible tripla Boost DEMO DATA budget test for hotel "
        "JP-KYO-001. Call growth.calculate_campaign_economics with "
        f"variable_cost_ratio {variable_cost_ratio}, then compare campaigns "
        "KYO-A and KYO-B using the returned evidence. Discuss a proposed "
        f"monthly transfer of ¥{amount_jpy} from KYO-A to KYO-B, including "
        "uncertainty and policy limits. Historical performance is not causal "
        "uplift; incremental outcomes are NOT YET MEASURED. Do not approve or "
        "execute a change. Ask for explicit user authorization before creating "
        "a proposal, and require a separate explicit approval before execution."
    )


PROMPTS: dict[str, dict[str, Any]] = {
    "review_managed_portfolio": {
        "title": "Review managed hotel portfolio",
        "description": "Read-only review of portfolio performance, outcomes, and alerts.",
        "arguments": [
            {"name": "period", "description": "Audit period, such as last_30_days.", "required": False}
        ],
        "render": review_managed_portfolio,
    },
    "plan_kyoto_budget_test": {
        "title": "Plan a Kyoto campaign budget test",
        "description": "Compare Kyoto campaigns and frame a bounded test without changing budgets.",
        "arguments": [
            {"name": "amount_jpy", "description": "Proposed monthly transfer amount in yen.", "required": False},
            {"name": "variable_cost_ratio", "description": "Variable cost ratio used for economics.", "required": False},
        ],
        "render": plan_kyoto_budget_test,
    },
}


RESOURCE_INFO: dict[str, dict[str, str]] = {
    "boost://demo/overview": {
        "name": "demo_overview",
        "title": "Demo overview and safety notes",
        "description": "Scope, data limitations, and safety rules for this fixture-only demo.",
    },
    "boost://demo/managed-hotels": {
        "name": "managed_hotels",
        "title": "Managed hotel fixture",
        "description": "DEMO DATA list of hotels assigned to the current specialist.",
    },
    "boost://demo/campaign-summary": {
        "name": "campaign_summary",
        "title": "Portfolio campaign summary",
        "description": "DEMO DATA campaign rows for the default reporting window.",
    },
}

RESOURCE_TEMPLATE_INFO: dict[str, dict[str, Any]] = {
    "boost://demo/hotels/{hotel_id}/campaign-performance": {
        "name": "hotel_campaign_performance",
        "title": "Campaign performance for a managed hotel",
        "description": "DEMO DATA campaign performance for one managed hotel. Replace {hotel_id} with a hotel ID, for example JP-KYO-001.",
        "mimeType": "application/json",
    },
}


def _resource_contents(service: BoostService, uri: str) -> str:
    if uri == "boost://demo/overview":
        content: Any = {
            "source_system": "tripla_boost_mock",
            "data_mode": "demo",
            "demo_marker": "DEMO DATA",
            "contains_pii": False,
            "scope": "Fixture-only demonstration; no live booking or advertising integrations.",
            "safety": [
                "Historical performance is not causal uplift.",
                "Incremental outcomes are NOT YET MEASURED unless returned otherwise.",
                "Budget execution is mock-only and requires proposal approval.",
            ],
        }
    elif uri == "boost://demo/managed-hotels":
        content = service.list_managed_hotels()
    elif uri == "boost://demo/campaign-summary":
        content = service.get_portfolio_campaign_summary()
    else:
        raise KeyError(uri)
    return json.dumps(content, ensure_ascii=False, indent=2)


def _template_resource_contents(service: BoostService, uri: str) -> str:
    prefix = "boost://demo/hotels/"
    suffix = "/campaign-performance"
    if not uri.startswith(prefix) or not uri.endswith(suffix):
        raise KeyError(uri)
    hotel_id = uri[len(prefix) : -len(suffix)]
    if not hotel_id or "/" in hotel_id:
        raise KeyError(uri)
    content = service.get_campaign_performance(hotel_id)
    return json.dumps(content, ensure_ascii=False, indent=2)


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
            return {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": self.protocol_version, "capabilities": {"tools": {}, "prompts": {}, "resources": {"listChanged": False}}, "serverInfo": {"name": "tripla-boost-demo", "version": "0.1.0"}}}
        if method == "tools/list":
            tools = [{"name": name, "description": "Fixture-only tripla Boost DEMO DATA tool.", "inputSchema": self._input_schema(operation)} for name, operation in self.tools.items()]
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
        if method == "prompts/list":
            prompts = [
                {"name": name, **{key: value for key, value in prompt.items() if key != "render"}}
                for name, prompt in PROMPTS.items()
            ]
            return {"jsonrpc": "2.0", "id": request_id, "result": {"prompts": prompts}}
        if method == "prompts/get":
            params = request.get("params", {})
            name = params.get("name")
            prompt = PROMPTS.get(name)
            if prompt is None:
                return self._error(request_id, -32602, f"unknown prompt: {name}")
            arguments = params.get("arguments", {})
            try:
                rendered = prompt["render"](**arguments)
            except (TypeError, ValueError) as exc:
                return self._error(request_id, -32602, str(exc))
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"description": prompt["description"], "messages": [{"role": "user", "content": {"type": "text", "text": rendered}}]},
            }
        if method == "resources/list":
            resources = [
                {"uri": uri, "mimeType": "application/json", **metadata}
                for uri, metadata in RESOURCE_INFO.items()
            ]
            return {"jsonrpc": "2.0", "id": request_id, "result": {"resources": resources}}
        if method == "resources/templates/list":
            templates = [
                {"uriTemplate": uri_template, **metadata}
                for uri_template, metadata in RESOURCE_TEMPLATE_INFO.items()
            ]
            return {"jsonrpc": "2.0", "id": request_id, "result": {"resourceTemplates": templates}}
        if method == "resources/read":
            uri = request.get("params", {}).get("uri", "")
            try:
                if uri in RESOURCE_INFO:
                    contents = _resource_contents(self.service, uri)
                else:
                    contents = _template_resource_contents(self.service, uri)
            except KeyError:
                return self._error(request_id, -32602, f"unknown resource: {uri}")
            except PolicyError as exc:
                return self._error(request_id, -32602, str(exc))
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"contents": [{"uri": uri, "mimeType": "application/json", "text": contents}]},
            }
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
    app.prompt(
        name="review_managed_portfolio",
        title=PROMPTS["review_managed_portfolio"]["title"],
        description=PROMPTS["review_managed_portfolio"]["description"],
    )(review_managed_portfolio)
    app.prompt(
        name="plan_kyoto_budget_test",
        title=PROMPTS["plan_kyoto_budget_test"]["title"],
        description=PROMPTS["plan_kyoto_budget_test"]["description"],
    )(plan_kyoto_budget_test)

    @app.resource(
        "boost://demo/overview",
        name=RESOURCE_INFO["boost://demo/overview"]["name"],
        title=RESOURCE_INFO["boost://demo/overview"]["title"],
        description=RESOURCE_INFO["boost://demo/overview"]["description"],
        mime_type="application/json",
    )
    def demo_overview() -> str:
        return _resource_contents(service, "boost://demo/overview")

    @app.resource(
        "boost://demo/managed-hotels",
        name=RESOURCE_INFO["boost://demo/managed-hotels"]["name"],
        title=RESOURCE_INFO["boost://demo/managed-hotels"]["title"],
        description=RESOURCE_INFO["boost://demo/managed-hotels"]["description"],
        mime_type="application/json",
    )
    def managed_hotels_resource() -> str:
        return _resource_contents(service, "boost://demo/managed-hotels")

    @app.resource(
        "boost://demo/campaign-summary",
        name=RESOURCE_INFO["boost://demo/campaign-summary"]["name"],
        title=RESOURCE_INFO["boost://demo/campaign-summary"]["title"],
        description=RESOURCE_INFO["boost://demo/campaign-summary"]["description"],
        mime_type="application/json",
    )
    def campaign_summary_resource() -> str:
        return _resource_contents(service, "boost://demo/campaign-summary")

    @app.resource(
        "boost://demo/hotels/{hotel_id}/campaign-performance",
        name=RESOURCE_TEMPLATE_INFO[
            "boost://demo/hotels/{hotel_id}/campaign-performance"
        ]["name"],
        title=RESOURCE_TEMPLATE_INFO[
            "boost://demo/hotels/{hotel_id}/campaign-performance"
        ]["title"],
        description=RESOURCE_TEMPLATE_INFO[
            "boost://demo/hotels/{hotel_id}/campaign-performance"
        ]["description"],
        mime_type="application/json",
    )
    def hotel_campaign_performance_resource(hotel_id: str) -> str:
        return _template_resource_contents(
            service,
            f"boost://demo/hotels/{hotel_id}/campaign-performance",
        )
    return app


def main() -> None:
    create_server().run()
if __name__ == "__main__": main()
