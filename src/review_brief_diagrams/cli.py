from __future__ import annotations

import argparse
import json
import sys

from pathlib import Path

from .renderer import RenderError, render_request


def _direct_request(args: argparse.Namespace) -> Path:
    source = Path(args.source)
    request_path = source.parent / f".diagram-render-request-{source.stem}.json"
    request_path.write_text(json.dumps({
        "contract_version": args.contract_version,
        "source": {"path": str(source)},
        "diagram": {"family": args.family},
        "output": {"bundle_dir": args.output},
        "rendering": {"style_profile": args.style_profile},
    }))
    return request_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="diagram-render")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--request", metavar="PATH", help="path to a JSON render request")
    group.add_argument("--source", metavar="PATH", help="Mermaid source path for direct command-line mode")
    parser.add_argument("--family", choices=("logical", "deployment", "interaction"), help="diagram family in direct mode")
    parser.add_argument("--output", metavar="DIR", help="artifact bundle directory in direct mode")
    parser.add_argument("--contract-version", default="1", help="contract version (default: latest supported, 1)")
    parser.add_argument("--style-profile", default="review-brief-default", help="named style profile")
    args = parser.parse_args(argv)
    if args.source and (not args.family or not args.output):
        parser.error("--source requires --family and --output")
    if args.request and any(value is not None for value in (args.source, args.family, args.output)):
        parser.error("--request cannot be combined with direct command-line parameters")
    request = Path(args.request) if args.request else _direct_request(args)
    try:
        bundle = render_request(request)
    except RenderError as exc:
        print(json.dumps({"error": exc.diagnostic}), file=sys.stderr)
        return exc.exit_code
    print(json.dumps({"status": "succeeded", "bundle": str(bundle.path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
