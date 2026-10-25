from __future__ import annotations

import argparse
import json

from .server import main as server_main
from .service import BoostService


def main() -> None:
    parser = argparse.ArgumentParser(description="tripla Boost fixture-only demo")
    parser.add_argument("command", choices=["server", "reset", "audit", "economics"])
    parser.add_argument("--state", default="boost_demo.sqlite")
    args = parser.parse_args()
    if args.command == "server": server_main(); return
    service = BoostService(args.state)
    if args.command == "reset": result = service.reset_demo("RESET DEMO")
    elif args.command == "audit": result = service.audit_portfolio()
    else: result = service.calculate_campaign_economics("JP-KYO-001")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
