#!/usr/bin/env python3
"""Generate bounded public and agent roadmap views from a complete graph."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .common import INDEX_PATH, SEED_PATH, SNAPSHOT_PATH, graph_from_seed, index_from_graph, iso_now, load_json, load_seed, snapshot_from_graph, write_json
except ImportError:  # direct script execution from Makefile/CI
    from common import INDEX_PATH, SEED_PATH, SNAPSHOT_PATH, graph_from_seed, index_from_graph, iso_now, load_json, load_seed, snapshot_from_graph, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=SEED_PATH)
    parser.add_argument("--graph", type=Path, help="complete normalized graph fixture; defaults to seed")
    parser.add_argument("--generated-at", default=None, help="explicit UTC timestamp for deterministic generation")
    parser.add_argument("--source-kind", choices=["seed", "fixture", "live", "fallback"], default="seed")
    parser.add_argument("--fallback-reason", default=None)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT_PATH)
    parser.add_argument("--index", type=Path, default=INDEX_PATH)
    parser.add_argument("--print", action="store_true", dest="print_output")
    args = parser.parse_args()
    generated_at = args.generated_at or iso_now()
    if args.graph:
        graph = load_json(args.graph)
        # A fixture must carry its own source identity but gets the current
        # generation metadata from the command line.
        graph["generatedAt"] = generated_at
        graph["sourceKind"] = args.source_kind
        graph["fallbackUsed"] = args.source_kind == "fallback"
        graph["fallbackReason"] = args.fallback_reason
    else:
        seed = load_seed(args.seed)
        graph = graph_from_seed(seed, generated_at=generated_at, source_kind=args.source_kind, fallback_used=args.source_kind == "fallback", fallback_reason=args.fallback_reason)
    snapshot = snapshot_from_graph(graph)
    index = index_from_graph(graph)
    write_json(args.snapshot, snapshot)
    write_json(args.index, index)
    if args.print_output:
        print(json.dumps({"snapshot": str(args.snapshot), "index": str(args.index), "sourceHash": graph["sourceHash"], "generatedAt": generated_at}, sort_keys=True))
    else:
        print(f"generated snapshot={args.snapshot} index={args.index} sourceHash={graph['sourceHash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
