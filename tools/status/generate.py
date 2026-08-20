#!/usr/bin/env python3
"""Generate human-facing MVP status from the acceptance ledger."""
from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROW = re.compile(r"^\|\s*(?P<id>[BU]\d{2})\s*\|\s*(?P<criterion>.*?)\s*\|\s*(?P<status>[A-Z-]+)\s*\|\s*(?P<evidence>.*?)\s*\|$")
README_BEGIN = "<!-- MVP-STATUS-BEGIN -->"
README_END = "<!-- MVP-STATUS-END -->"

@dataclass(frozen=True)
class Gate:
    id: str
    criterion: str
    status: str
    evidence: str


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_ledger(path: Path) -> list[Gate]:
    gates: list[Gate] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match:
            gates.append(Gate(**match.groupdict()))
    base = [gate for gate in gates if gate.id.startswith("B")]
    plus = [gate for gate in gates if gate.id.startswith("U")]
    if len(base) != 20 or len(plus) != 4:
        raise SystemExit(f"unexpected acceptance ledger shape: {len(base)} base, {len(plus)} MVP+")
    return gates


def summary_block(gates: list[Gate]) -> str:
    base = [gate for gate in gates if gate.id.startswith("B")]
    passed = sum(gate.status == "PASS" for gate in base)
    blocked = len(base) - passed
    return (
        f"{README_BEGIN}\n"
        f"**Acceptance:** {passed}/{len(base)} base gates passed; {blocked} are blocked on physical-device validation. "
        "USB networking remains deferred until every base gate passes.\n"
        f"{README_END}"
    )


def status_evidence(evidence: str) -> str:
    # Ledger links are relative to docs/roadmap; STATUS.md lives one level higher.
    return evidence.replace("../../evidence/", "../evidence/")


def status_document(gates: list[Gate]) -> str:
    base = [gate for gate in gates if gate.id.startswith("B")]
    plus = [gate for gate in gates if gate.id.startswith("U")]
    counts = Counter(gate.status for gate in base)
    remaining = [gate for gate in base if gate.status != "PASS"]
    passed = [gate for gate in base if gate.status == "PASS"]

    lines = [
        "# MVP status",
        "",
        "> Generated from `docs/roadmap/acceptance-ledger.md` by `tools/status/generate.py`. Do not edit by hand.",
        "",
        "## Current verdict",
        "",
        "**Device-lab candidate — not yet a validated MVP.**",
        "",
        f"{counts.get('PASS', 0)} of {len(base)} base gates pass. The remaining {len(remaining)} gates require physical-device or live-network evidence.",
        "",
        "| Base status | Count |",
        "|---|---:|",
    ]
    for status in sorted(counts):
        lines.append(f"| `{status}` | {counts[status]} |")
    lines += ["", "## Remaining base gates", "", "| ID | Criterion | Status | Evidence |", "|---|---|---|---|"]
    for gate in remaining:
        lines.append(f"| {gate.id} | {gate.criterion} | `{gate.status}` | {status_evidence(gate.evidence)} |")
    lines += ["", "## Passed software/base gates", "", "| ID | Criterion | Evidence |", "|---|---|---|"]
    for gate in passed:
        lines.append(f"| {gate.id} | {gate.criterion} | {status_evidence(gate.evidence)} |")
    lines += ["", "## MVP+", "", "MVP+ remains blocked until every base gate is `PASS`.", "", "| ID | Criterion | Status |", "|---|---|---|"]
    for gate in plus:
        lines.append(f"| {gate.id} | {gate.criterion} | `{gate.status}` |")
    lines += [
        "",
        "## Next validation order",
        "",
        "1. **D01:** install the exact CI-built APK and close B02 with a real QMP-qualified Alpine boot.",
        "2. **D02:** close B08–B09 with host Headscale enrollment and authenticated Host API reachability.",
        "3. **D03:** close B10–B12 with Ubuntu deployment, cloud-init, guest Tailscale, and ordinary SSH.",
        "4. **D04:** close B13 by disabling guest mesh and using the bounded host recovery proxy.",
        "5. **D05:** close B07 and B16–B17 through Activity/service/process/reboot/offline-controller tests.",
        "6. **D07:** bind all evidence to one source commit and exact APK before calling the result the MVP.",
        "",
    ]
    return "\n".join(lines)


def replace_readme_block(readme: str, block: str) -> str:
    start = readme.find(README_BEGIN)
    end = readme.find(README_END)
    if start < 0 or end < start:
        raise SystemExit("README MVP status markers are missing or malformed")
    end += len(README_END)
    return readme[:start] + block + readme[end:]


def generated_outputs(root: Path) -> dict[Path, str]:
    gates = parse_ledger(root / "docs/roadmap/acceptance-ledger.md")
    readme = (root / "README.md").read_text(encoding="utf-8")
    return {
        root / "docs/STATUS.md": status_document(gates),
        root / "README.md": replace_readme_block(readme, summary_block(gates)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write generated files instead of printing status")
    args = parser.parse_args()
    outputs = generated_outputs(repository_root())
    if args.write:
        for path, content in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content.rstrip() + "\n", encoding="utf-8")
            print(path.relative_to(repository_root()))
    else:
        print(outputs[repository_root() / "docs/STATUS.md"], end="")

if __name__ == "__main__":
    main()
