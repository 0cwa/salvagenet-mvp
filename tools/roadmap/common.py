#!/usr/bin/env python3
"""Shared, bounded roadmap parsing and derivation helpers."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / ".github" / "roadmap" / "seed.v1.json"
SNAPSHOT_PATH = ROOT / "website" / "data" / "roadmap.snapshot.v1.json"
INDEX_PATH = ROOT / "agents" / "generated" / "roadmap.index.v1.json"
CACHE_PATH = ROOT / ".agent-cache" / "roadmap"
MAX_ISSUES = 250
MAX_CONTEXT_FILES = 12
MAX_CONTEXT_BYTES = 24_000
MAX_COMMENT_COUNT = 5
MAX_COMMENT_BYTES = 4_000
FRESHNESS_HOURS = 72
ROADMAP_MARKER = re.compile(r"<!--\s*roadmap-id:\s*([A-Za-z0-9][A-Za-z0-9.-]*)\s*-->")


class RoadmapError(ValueError):
    """Raised for malformed, incomplete, or unsafe roadmap input."""


class SeedValidationError(RoadmapError):
    def __init__(self, errors: Iterable[str]):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def source_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RoadmapError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RoadmapError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=False, ensure_ascii=False) + "\n")


def parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RoadmapError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_relative_path(raw: str, *, must_exist: bool = True) -> Path:
    if not isinstance(raw, str) or not raw or raw.startswith("/"):
        raise RoadmapError(f"repository path must be relative: {raw!r}")
    path = Path(raw)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise RoadmapError(f"repository path contains unsafe components: {raw!r}")
    resolved = (ROOT / path).resolve()
    if resolved != ROOT and ROOT not in resolved.parents:
        raise RoadmapError(f"repository path escapes root: {raw!r}")
    if must_exist and not resolved.exists():
        raise RoadmapError(f"repository path does not exist: {raw}")
    return path


def marker_for(stable_id: str) -> str:
    return f"<!-- roadmap-id: {stable_id} -->"


def marker_from_body(body: str) -> str | None:
    match = ROADMAP_MARKER.search(body or "")
    return match.group(1) if match else None


def required_acceptance_ids() -> list[str]:
    return [f"B{i:02d}" for i in range(1, 21)] + [f"U{i:02d}" for i in range(1, 5)]


def load_seed(path: Path = SEED_PATH) -> dict[str, Any]:
    seed = load_json(path)
    validate_seed(seed)
    return seed


def _as_nonempty_string(value: Any, field: str, errors: list[str], prefix: str) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}.{field} must be a non-empty string")


def validate_seed(seed: dict[str, Any], *, root: Path = ROOT, check_active_tasks: bool = True) -> dict[str, Any]:
    """Validate the complete reviewed seed and return compact validation facts."""
    errors: list[str] = []
    if seed.get("schemaVersion") != 1:
        errors.append("schemaVersion must be 1")
    _as_nonempty_string(seed.get("seedVersion"), "seedVersion", errors, "seed")
    _as_nonempty_string(seed.get("repository"), "repository", errors, "seed")
    milestones = seed.get("milestones")
    labels = seed.get("labels")
    issues = seed.get("issues")
    if not isinstance(milestones, list) or not milestones:
        errors.append("milestones must be a non-empty list")
        milestones = []
    if not isinstance(labels, list) or not labels:
        errors.append("labels must be a non-empty list")
        labels = []
    if not isinstance(issues, list) or not issues:
        errors.append("issues must be a non-empty list")
        issues = []

    milestone_ids: set[str] = set()
    milestone_order: dict[str, int] = {}
    for index, milestone in enumerate(milestones):
        prefix = f"milestones[{index}]"
        if not isinstance(milestone, dict):
            errors.append(f"{prefix} must be an object")
            continue
        mid = milestone.get("id")
        _as_nonempty_string(mid, "id", errors, prefix)
        if isinstance(mid, str):
            if mid in milestone_ids:
                errors.append(f"duplicate milestone id: {mid}")
            milestone_ids.add(mid)
            milestone_order[mid] = milestone.get("order", index)
        _as_nonempty_string(milestone.get("title"), "title", errors, prefix)
        _as_nonempty_string(milestone.get("description"), "description", errors, prefix)

    label_names: set[str] = set()
    for index, label in enumerate(labels):
        prefix = f"labels[{index}]"
        if not isinstance(label, dict):
            errors.append(f"{prefix} must be an object")
            continue
        name = label.get("name")
        _as_nonempty_string(name, "name", errors, prefix)
        if isinstance(name, str):
            if name in label_names:
                errors.append(f"duplicate label: {name}")
            label_names.add(name)
        _as_nonempty_string(label.get("description"), "description", errors, prefix)
        color = label.get("color")
        if not isinstance(color, str) or not re.fullmatch(r"[0-9a-fA-F]{6}", color):
            errors.append(f"{prefix}.color must be six hexadecimal characters")

    issue_map: dict[str, dict[str, Any]] = {}
    dependency_map: dict[str, list[str]] = {}
    required_issue_fields = (
        "id", "title", "publicSummary", "observableOutcome", "area", "kind", "visibility",
        "milestone", "seedState", "dependencies", "acceptanceIds", "contextPaths",
        "nonGoals", "validation", "acceptanceCriteria",
    )
    for index, issue in enumerate(issues):
        prefix = f"issues[{index}]"
        if not isinstance(issue, dict):
            errors.append(f"{prefix} must be an object")
            continue
        for field in required_issue_fields:
            if field not in issue:
                errors.append(f"{prefix} missing {field}")
        stable_id = issue.get("id")
        _as_nonempty_string(stable_id, "id", errors, prefix)
        if not isinstance(stable_id, str):
            continue
        if stable_id in issue_map:
            errors.append(f"duplicate issue id: {stable_id}")
        issue_map[stable_id] = issue
        for field in ("title", "publicSummary", "observableOutcome", "area", "kind", "visibility", "milestone", "seedState"):
            _as_nonempty_string(issue.get(field), field, errors, prefix)
        if issue.get("milestone") not in milestone_ids:
            errors.append(f"{stable_id} references unknown milestone {issue.get('milestone')!r}")
        if issue.get("visibility") not in {"public", "internal"}:
            errors.append(f"{stable_id} visibility must be public or internal")
        if issue.get("seedState") not in {"planned", "queued", "active", "review", "hold", "done", "blocked"}:
            errors.append(f"{stable_id} has invalid seedState")
        for list_field in ("dependencies", "acceptanceIds", "contextPaths", "nonGoals", "validation", "acceptanceCriteria"):
            if not isinstance(issue.get(list_field), list) or (list_field in {"contextPaths", "nonGoals", "validation", "acceptanceCriteria"} and not issue.get(list_field)):
                errors.append(f"{stable_id}.{list_field} must be a non-empty list")
        task_packet = issue.get("taskPacket")
        if task_packet is not None:
            try:
                repo_relative_path(task_packet)
            except RoadmapError as exc:
                errors.append(f"{stable_id}.taskPacket: {exc}")
        for path in issue.get("contextPaths", []) if isinstance(issue.get("contextPaths"), list) else []:
            try:
                repo_relative_path(path)
            except RoadmapError as exc:
                errors.append(f"{stable_id}.contextPaths: {exc}")
        dependencies = issue.get("dependencies", [])
        if isinstance(dependencies, list):
            dependency_map[stable_id] = dependencies
            if len(dependencies) != len(set(dependencies)):
                errors.append(f"{stable_id} has duplicate dependencies")
            for dependency in dependencies:
                if dependency not in issue_map and dependency not in {entry.get("id") for entry in issues if isinstance(entry, dict)}:
                    errors.append(f"{stable_id} references unknown dependency {dependency}")

    required_labels = {"roadmap", "roadmap:public", "roadmap:internal"}
    required_labels |= {f"area:{issue.get('area')}" for issue in issues if isinstance(issue, dict) and issue.get("area")}
    required_labels |= {f"kind:{issue.get('kind')}" for issue in issues if isinstance(issue, dict) and issue.get("kind")}
    if missing := sorted(required_labels - label_names):
        errors.append(f"seed is missing labels: {', '.join(missing)}")

    for stable_id, issue in issue_map.items():
        issue_labels = issue.get("labels", [])
        if not isinstance(issue_labels, list):
            errors.append(f"{stable_id}.labels must be a list")
            issue_labels = []
        if "roadmap" not in issue_labels:
            errors.append(f"{stable_id} must have roadmap label")
        area_labels = [label for label in issue_labels if isinstance(label, str) and label.startswith("area:")]
        kind_labels = [label for label in issue_labels if isinstance(label, str) and label.startswith("kind:")]
        visibility_labels = [label for label in issue_labels if label in {"roadmap:public", "roadmap:internal"}]
        if area_labels != [f"area:{issue.get('area')}"]:
            errors.append(f"{stable_id} must have exactly one matching area label")
        if kind_labels != [f"kind:{issue.get('kind')}"]:
            errors.append(f"{stable_id} must have exactly one matching kind label")
        if visibility_labels != [f"roadmap:{issue.get('visibility')}"]:
            errors.append(f"{stable_id} must have exactly one matching visibility label")
        for label in issue_labels:
            if label not in label_names:
                errors.append(f"{stable_id} references unknown label {label}")

    for stable_id, dependencies in dependency_map.items():
        for dependency in dependencies:
            if dependency not in issue_map:
                continue
            issue_order = milestone_order.get(issue_map[stable_id].get("milestone"), 0)
            dependency_order = milestone_order.get(issue_map[dependency].get("milestone"), 0)
            if dependency_order > issue_order:
                errors.append(f"{stable_id} depends on later-milestone issue {dependency}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, trail: list[str]) -> None:
        if node in visiting:
            errors.append(f"dependency cycle: {' -> '.join(trail + [node])}")
            return
        if node in visited:
            return
        visiting.add(node)
        for dependency in dependency_map.get(node, []):
            if dependency in issue_map:
                visit(dependency, trail + [node])
        visiting.remove(node)
        visited.add(node)

    for stable_id in issue_map:
        visit(stable_id, [])

    expected_acceptance = set(required_acceptance_ids())
    seen_acceptance: dict[str, set[str]] = {acceptance_id: set() for acceptance_id in expected_acceptance}
    for stable_id, issue in issue_map.items():
        for acceptance_id in issue.get("acceptanceIds", []) if isinstance(issue.get("acceptanceIds"), list) else []:
            if acceptance_id not in expected_acceptance:
                errors.append(f"{stable_id} references unknown acceptance id {acceptance_id}")
            else:
                seen_acceptance[acceptance_id].add(stable_id)
    missing_acceptance = sorted(key for key, values in seen_acceptance.items() if not values)
    if missing_acceptance:
        errors.append(f"missing acceptance coverage: {', '.join(missing_acceptance)}")

    coverage = seed.get("acceptanceCoverage")
    if not isinstance(coverage, list):
        errors.append("acceptanceCoverage must be a list")
    else:
        coverage_map = {entry.get("id"): entry for entry in coverage if isinstance(entry, dict)}
        if set(coverage_map) != expected_acceptance:
            errors.append("acceptanceCoverage must contain exactly B01-B20 and U01-U04")
        for acceptance_id, entry in coverage_map.items():
            if not isinstance(entry.get("issueIds"), list) or set(entry["issueIds"]) != seen_acceptance.get(acceptance_id, set()):
                errors.append(f"acceptanceCoverage disagrees for {acceptance_id}")

    debt = seed.get("releaseBlockingDebt")
    if not isinstance(debt, list) or not debt:
        errors.append("releaseBlockingDebt must be a non-empty list")
    else:
        for index, item in enumerate(debt):
            if not isinstance(item, dict) or not item.get("id") or not item.get("issueIds"):
                errors.append(f"releaseBlockingDebt[{index}] is incomplete")
            elif any(issue_id not in issue_map for issue_id in item["issueIds"]):
                errors.append(f"releaseBlockingDebt[{index}] references unknown issue")

    directions = seed.get("postMvpDirections")
    if not isinstance(directions, list) or not directions:
        errors.append("postMvpDirections must be a non-empty list")
    else:
        for index, item in enumerate(directions):
            if not isinstance(item, dict) or not item.get("id") or not item.get("summary") or not item.get("issueIds"):
                errors.append(f"postMvpDirections[{index}] is incomplete")
            elif any(issue_id not in issue_map for issue_id in item["issueIds"]):
                errors.append(f"postMvpDirections[{index}] references unknown issue")

    pull_requests = seed.get("pullRequests")
    if not isinstance(pull_requests, list) or not pull_requests:
        errors.append("pullRequests must be a non-empty list")
    else:
        for index, item in enumerate(pull_requests):
            if not isinstance(item, dict) or not item.get("number") or not item.get("roadmapId") or not item.get("state"):
                errors.append(f"pullRequests[{index}] is incomplete")
            elif item.get("roadmapId") not in issue_map:
                errors.append(f"pullRequests[{index}] references unknown issue")

    task_mappings = seed.get("taskMappings")
    if not isinstance(task_mappings, list):
        errors.append("taskMappings must be a list")
        task_mappings = []
    task_mapping_counts: dict[str, int] = {}
    for index, mapping in enumerate(task_mappings):
        if not isinstance(mapping, dict) or not mapping.get("taskId") or not mapping.get("roadmapId") or not mapping.get("packet"):
            errors.append(f"taskMappings[{index}] is incomplete")
            continue
        if mapping["roadmapId"] not in issue_map:
            errors.append(f"taskMappings[{index}] references unknown issue")
        task_mapping_counts[mapping["taskId"]] = task_mapping_counts.get(mapping["taskId"], 0) + 1
        try:
            repo_relative_path(mapping["packet"])
        except RoadmapError as exc:
            errors.append(f"taskMappings[{index}].packet: {exc}")
        for path in mapping.get("contextPaths", []):
            try:
                repo_relative_path(path)
            except RoadmapError as exc:
                errors.append(f"taskMappings[{index}].contextPaths: {exc}")

    if check_active_tasks:
        dag_path = root / "agents" / "task-dag.json"
        if dag_path.exists():
            try:
                dag = load_json(dag_path)
                active_task_ids = {entry.get("id") for entry in dag.get("tasks", []) if isinstance(entry, dict)}
                for task_id in sorted(active_task_ids):
                    if task_mapping_counts.get(task_id) != 1:
                        errors.append(f"active task {task_id} must map to exactly one roadmap issue")
                for task_id in sorted(set(task_mapping_counts) - active_task_ids):
                    errors.append(f"seed maps non-active task {task_id}")
            except RoadmapError as exc:
                errors.append(str(exc))

    if errors:
        raise SeedValidationError(errors)
    return {
        "issueCount": len(issue_map),
        "milestoneCount": len(milestones),
        "labelCount": len(labels),
        "dependencyCount": sum(len(values) for values in dependency_map.values()),
        "acceptanceCount": len(expected_acceptance),
        "taskMappingCount": len(task_mappings),
    }


def seed_source(seed: dict[str, Any]) -> dict[str, Any]:
    """Return only stable seed content used for source hashing."""
    return {
        "schemaVersion": seed.get("schemaVersion"),
        "seedVersion": seed.get("seedVersion"),
        "repository": seed.get("repository"),
        "milestones": seed.get("milestones"),
        "labels": seed.get("labels"),
        "issues": seed.get("issues"),
        "acceptanceCoverage": seed.get("acceptanceCoverage"),
        "releaseBlockingDebt": seed.get("releaseBlockingDebt"),
        "postMvpDirections": seed.get("postMvpDirections"),
        "pullRequests": seed.get("pullRequests"),
        "taskMappings": seed.get("taskMappings"),
    }


def issue_body(issue: dict[str, Any]) -> str:
    lines = [
        marker_for(issue["id"]),
        f"# {issue['id']} — {issue['title']}",
        "",
        f"**Public summary:** {issue['publicSummary']}",
        "",
        "## Observable outcome",
        "",
        issue["observableOutcome"],
        "",
        "## Acceptance criteria",
        "",
        *[f"- [ ] {value}" for value in issue["acceptanceCriteria"]],
        "",
        "## Non-goals",
        "",
        *[f"- {value}" for value in issue["nonGoals"]],
        "",
        "## Required validation",
        "",
        *[f"- {value}" for value in issue["validation"]],
        "",
        f"Roadmap metadata is generated from `.github/roadmap/seed.v1.json`. Issue state does not authorize implementation or close acceptance gates.",
    ]
    if issue.get("acceptanceIds"):
        lines.extend(["", "Acceptance IDs: " + ", ".join(issue["acceptanceIds"])])
    if issue.get("taskPacket"):
        lines.extend(["", f"Task packet: `{issue['taskPacket']}`"])
    return "\n".join(lines) + "\n"


def issue_url(repository: str, number: int | None) -> str | None:
    return f"https://github.com/{repository}/issues/{number}" if number is not None else None


def _state_from_seed(seed_state: str) -> str:
    return {"queued": "planned", "planned": "planned", "blocked": "planned"}.get(seed_state, seed_state)


def graph_from_seed(seed: dict[str, Any], *, generated_at: str, source_kind: str = "seed", fallback_used: bool = False, fallback_reason: str | None = None) -> dict[str, Any]:
    validate_seed(seed)
    milestones = {entry["id"]: entry for entry in seed["milestones"]}
    issue_numbers = {issue["id"]: issue.get("issueNumber", index + 1) for index, issue in enumerate(seed["issues"])}
    issue_states = {issue["id"]: issue["seedState"] for issue in seed["issues"]}
    task_mappings = {}
    for mapping in seed.get("taskMappings", []):
        task_mappings.setdefault(mapping["roadmapId"], []).append(mapping["taskId"])
    normalized: list[dict[str, Any]] = []
    for issue in sorted(seed["issues"], key=lambda entry: (milestones[entry["milestone"]]["order"], entry["id"])):
        deps = sorted(issue["dependencies"])
        dependency_state = "clear" if all(issue_states.get(dep) == "done" for dep in deps) else "blocked"
        normalized.append({
            "stableId": issue["id"],
            "number": issue_numbers[issue["id"]],
            "title": issue["title"],
            "publicSummary": issue["publicSummary"],
            "url": issue_url(seed["repository"], issue_numbers[issue["id"]]),
            "milestone": {"id": issue["milestone"], "title": milestones[issue["milestone"]]["title"], "order": milestones[issue["milestone"]]["order"]},
            "area": issue["area"],
            "kind": issue["kind"],
            "visibility": issue["visibility"],
            "dependencies": [{"stableId": dep, "number": issue_numbers[dep]} for dep in deps],
            "acceptanceIds": sorted(issue["acceptanceIds"]),
            "taskPacket": issue.get("taskPacket"),
            "contextPaths": list(issue["contextPaths"]),
            "workState": _state_from_seed(issue["seedState"]),
            "dependencyState": dependency_state,
            "authorizationState": "authorized" if task_mappings.get(issue["id"]) else "not-authorized",
            "authorizedTaskIds": sorted(task_mappings.get(issue["id"], [])),
            "pullRequestState": next((pr["state"] for pr in seed.get("pullRequests", []) if pr.get("roadmapId") == issue["id"]), "none"),
            "updatedAt": seed.get("reviewedAt", generated_at),
            "disagreements": [],
        })
    normalized_source = {
        "repository": seed["repository"],
        "milestones": [{"id": entry["id"], "title": entry["title"], "order": entry["order"]} for entry in seed["milestones"]],
        "issues": normalized,
        "taskMappings": seed.get("taskMappings", []),
    }
    return {
        "schemaVersion": 1,
        "repository": seed["repository"],
        "complete": True,
        "dependencyFetchComplete": True,
        "generatedAt": generated_at,
        "newestIssueUpdatedAt": max((entry["updatedAt"] for entry in normalized), default=generated_at),
        "sourceHash": source_hash(seed_source(seed)) if source_kind == "seed" else source_hash(normalized_source),
        "sourceKind": source_kind,
        "fallbackUsed": fallback_used,
        "fallbackReason": fallback_reason,
        "milestones": normalized_source["milestones"],
        "issues": normalized,
        "disagreements": [],
    }


def validate_graph(graph: dict[str, Any]) -> None:
    if graph.get("schemaVersion") != 1:
        raise RoadmapError("graph schemaVersion must be 1")
    if graph.get("complete") is not True or graph.get("dependencyFetchComplete") is not True:
        raise RoadmapError("roadmap graph is partial; publication is refused")
    issues = graph.get("issues")
    if not isinstance(issues, list) or len(issues) > MAX_ISSUES:
        raise RoadmapError(f"graph issues must be a bounded list of at most {MAX_ISSUES}")
    ids = {entry.get("stableId") for entry in issues if isinstance(entry, dict)}
    if len(ids) != len(issues) or None in ids:
        raise RoadmapError("graph stable IDs must be unique")
    for issue in issues:
        if not issue.get("milestone") or not isinstance(issue.get("dependencies"), list) or not isinstance(issue.get("acceptanceIds"), list):
            raise RoadmapError(f"graph issue is incomplete: {issue.get('stableId')}")
        for dep in issue["dependencies"]:
            if dep.get("stableId") not in ids:
                raise RoadmapError(f"graph dependency is unknown: {issue['stableId']} -> {dep.get('stableId')}")
        if issue.get("workState") == "active" and issue.get("dependencyState") != "clear":
            raise RoadmapError(f"active issue has unresolved dependency: {issue['stableId']}")
        if any(len(str(value)) > 2_000 for value in issue.values() if isinstance(value, str)):
            raise RoadmapError(f"graph field is unbounded: {issue['stableId']}")


def snapshot_from_graph(graph: dict[str, Any]) -> dict[str, Any]:
    validate_graph(graph)
    milestones = []
    for milestone in sorted(graph["milestones"], key=lambda entry: (entry["order"], entry["id"])):
        items = [issue for issue in graph["issues"] if issue["milestone"]["id"] == milestone["id"]]
        milestones.append({
            "id": milestone["id"],
            "title": milestone["title"],
            "order": milestone["order"],
            "items": [
                {
                    "stableId": issue["stableId"], "number": issue["number"], "title": issue["title"],
                    "publicSummary": issue["publicSummary"], "url": issue["url"],
                    "area": issue["area"], "kind": issue["kind"], "visibility": issue["visibility"],
                    "dependencies": [dep["stableId"] for dep in issue["dependencies"]],
                    "workState": issue["workState"], "dependencyState": issue["dependencyState"],
                    "acceptanceIds": issue["acceptanceIds"], "pullRequestState": issue["pullRequestState"],
                }
                for issue in sorted(items, key=lambda entry: entry["stableId"])
            ],
        })
    return {
        "schemaVersion": 1,
        "generatedAt": graph["generatedAt"],
        "newestIssueUpdatedAt": graph["newestIssueUpdatedAt"],
        "source": {"repository": graph["repository"], "sourceHash": graph["sourceHash"], "kind": graph["sourceKind"]},
        "freshness": {"fallbackUsed": graph["fallbackUsed"], "fallbackReason": graph["fallbackReason"], "maxAgeHours": FRESHNESS_HOURS},
        "bounds": {"maxIssues": MAX_ISSUES, "fullBodiesIncluded": False, "commentsIncluded": False},
        "milestones": milestones,
        "disagreements": graph.get("disagreements", []),
    }


def index_from_graph(graph: dict[str, Any]) -> dict[str, Any]:
    validate_graph(graph)
    active_milestones = {issue["milestone"]["id"] for issue in graph["issues"] if issue["workState"] == "active"}
    current = next((entry for entry in graph["milestones"] if entry["id"] in active_milestones), None)
    if current is None and graph["milestones"]:
        current = min(graph["milestones"], key=lambda entry: entry["order"])
    # The active/ready/blocked views are intentionally derived from separate state fields.
    active = [issue for issue in graph["issues"] if issue["workState"] == "active"]
    ready = [issue for issue in graph["issues"] if issue["workState"] == "planned" and issue["dependencyState"] == "clear" and issue["authorizationState"] == "authorized"]
    blocked = [issue for issue in graph["issues"] if issue["dependencyState"] == "blocked"]

    def compact(issue: dict[str, Any]) -> dict[str, Any]:
        return {
            "stableId": issue["stableId"], "number": issue["number"], "title": issue["title"],
            "dependencies": [dep["stableId"] for dep in issue["dependencies"]],
            "acceptanceIds": issue["acceptanceIds"], "taskPacket": issue["taskPacket"],
            "workState": issue["workState"], "dependencyState": issue["dependencyState"],
            "authorizationState": issue["authorizationState"], "authorizedTaskIds": issue["authorizedTaskIds"],
        }

    return {
        "schemaVersion": 1,
        "generatedAt": graph["generatedAt"],
        "source": {"repository": graph["repository"], "sourceHash": graph["sourceHash"], "kind": graph["sourceKind"]},
        "freshness": {"fallbackUsed": graph["fallbackUsed"], "fallbackReason": graph["fallbackReason"], "maxAgeHours": FRESHNESS_HOURS},
        "currentMilestone": current,
        "active": [compact(issue) for issue in sorted(active, key=lambda entry: entry["stableId"])],
        "ready": [compact(issue) for issue in sorted(ready, key=lambda entry: entry["stableId"])],
        "blocked": [compact(issue) for issue in sorted(blocked, key=lambda entry: entry["stableId"])],
        "disagreements": graph.get("disagreements", []),
    }


def snapshot_freshness(snapshot: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    generated = parse_time(snapshot["generatedAt"])
    age_hours = max(0.0, (now - generated).total_seconds() / 3600)
    return {"ageHours": round(age_hours, 3), "maxAgeHours": FRESHNESS_HOURS, "fresh": age_hours <= FRESHNESS_HOURS, "fallbackUsed": snapshot.get("freshness", {}).get("fallbackUsed", False)}


def select_fallback_snapshot(previous: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    freshness = snapshot_freshness(previous, now=now)
    if not freshness["fresh"]:
        raise RoadmapError(f"last-known-good snapshot is stale ({freshness['ageHours']}h > {FRESHNESS_HOURS}h)")
    return previous


def bounded_text(value: str, limit: int) -> tuple[str, bool]:
    encoded = value.encode("utf-8")
    if len(encoded) <= limit:
        return value, False
    clipped = encoded[: max(0, limit - 32)].decode("utf-8", errors="ignore")
    return clipped + "\n[truncated by roadmap context bound]\n", True
