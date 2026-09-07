from __future__ import annotations

import argparse
import json
import sys

from .renderer import RenderError, render_request


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="diagram-render")
    parser.add_argument("request", help="path to a JSON render request")
    args = parser.parse_args(argv)
    try:
        bundle = render_request(args.request)
    except RenderError as exc:
        print(json.dumps({"error": exc.diagnostic}), file=sys.stderr)
        return exc.exit_code
    print(json.dumps({"status": "succeeded", "bundle": str(bundle.path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
