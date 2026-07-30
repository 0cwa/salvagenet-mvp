#!/usr/bin/env python3
"""SalvageNet issue-roadmap bootstrap, validation, snapshots, and bounded context.

GitHub Issues become roadmap planning truth only after a reviewed bootstrap apply.
The active task DAG remains implementation authorization, and the acceptance
ledger remains product-claim truth.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Iterable
from urllib import error, parse, request

ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = ROOT / ".github/roadmap/seed.v1.json"
STATE_PATH = ROOT / ".github/roadmap/bootstrap-state.v1.json"
SNAPSHOT_PATH = ROOT / "website/data/roadmap.snapshot.v1.json"
INDEX_PATH = ROOT / "agents/generated/roadmap.index.v1.json"
CACHE_DIR = ROOT / ".agent-cache/roadmap"
LEDGER_PATH = ROOT / "docs/roadmap/acceptance-ledger.md"
DAG_PATH = ROOT / "agents/task-dag.json"
REGISTRY_PATH = ROOT / "agents/task-registry.json"
SCHEMA_VERSION = 1
API_VERSION = "2026-03-10"
ROADMAP_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]{2}$")
ROADMAP_MARKER_RE = re.compile(r"<!--\s*roadmap-id:\s*([A-Z][A-Z0-9]*-[0-9]{2})\s*-->")
TASK_MARKER_RE = re.compile(r"<!--\s*task-packet:\s*([^>]+?)\s*-->")
SUMMARY_MARKER_RE = re.compile(r"<!--\s*public-summary:\s*(.*?)\s*-->")
LEDGER_ROW_RE = re.compile(
    r"^\|\s*(?P<id>[BU]\d{2})\s*\|\s*(?P<criterion>.*?)\s*\|\s*(?P<status>[A-Z-]+)\s*\|\s*(?P<evidence>.*?)\s*\|$"
)
REQUIRED_GATES = {*(f"B{i:02d}" for i in range(1, 21)), *(f"U{i:02d}" for i in range(1, 5))}
REQUIRED_ITEMS = {
    "FND-01", "FND-02", "FND-03", "FND-04", "FND-05", "FND-06",
    "WEB-00", "WEB-01", "WEB-02", "WEB-03", "WEB-04", "WEB-05", "WEB-06",
    "GUEST-01", "GUEST-02", "DEVICE-01", "DEVICE-02", "DEVICE-03", "DEVICE-04", "RELEASE-01",
    "EA-00", "EA-01", "EA-02", "EA-03", "EA-04", "EA-05", "EA-06",
    "REL-01", "REL-02", "REL-03", "REL-04", "REL-05", "REL-06",
    "PLAT-01", "PLAT-02", "PLAT-03", "PLAT-04", "PLAT-05", "PLAT-06", "PLAT-07",
    "PLAT-08", "PLAT-09", "PLAT-10", "PLAT-11", "PLAT-12", "PLAT-13", "PLAT-14", "PLAT-15",
    "USB-01", "USB-02", "USB-03", "USB-04", "USB-05",
}
REQUIRED_POST_MVP = {
    "PLAT-01", "PLAT-02", "PLAT-03", "PLAT-04", "PLAT-05", "PLAT-06", "PLAT-07",
    "PLAT-08", "PLAT-09", "PLAT-10", "PLAT-11", "PLAT-12", "PLAT-13", "PLAT-14", "PLAT-15", "USB-05",
}
REQUIRED_RELEASE_DEBT = {"EA-00", "PLAT-01", "PLAT-02", "PLAT-03", "REL-05", "FND-06"}
WORK_STATES = {"done", "review", "queued", "ready", "active", "hold"}
VISIBILITIES = {"public", "internal"}
AGENT_LABELS = {
    "queued": "agent:queued",
    "ready": "agent:ready",
    "active": "agent:active",
    "review": "agent:review",
    "hold": "agent:hold",
}


class RoadmapError(ValueError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RoadmapError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise RoadmapError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def safe_relative(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts and path.as_posix() == value


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def unique(values: Iterable[str], noun: str, errors: list[str]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        errors.append(f"duplicate {noun}: {', '.join(sorted(duplicates))}")


def load_seed(path: Path = SEED_PATH) -> dict[str, Any]:
    return read_json(path)


def validate_seed(seed: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    errors: list[str] = []
    require(seed.get("schemaVersion") == SCHEMA_VERSION, f"schemaVersion must be {SCHEMA_VERSION}", errors)
    require(seed.get("repository") == "0cwa/salvagenet-mvp", "repository must be 0cwa/salvagenet-mvp", errors)
    require(seed.get("bootstrapOnly") is True, "bootstrapOnly must be true", errors)
    policy = seed.get("policy")
    require(isinstance(policy, dict), "policy must be an object", errors)
    for key, expected in {
        "issuesBecomeAuthoritativeAfterBootstrap": True,
        "futurePhasePlansMustReevaluateQueuedItems": True,
        "issueClosureDoesNotCloseAcceptanceGates": True,
        "activeTaskAuthorizationRemainsIn": "agents/task-dag.json",
    }.items():
        require(isinstance(policy, dict) and policy.get(key) == expected, f"policy.{key} must be {expected!r}", errors)

    milestones = seed.get("milestones")
    labels = seed.get("labels")
    items = seed.get("items")
    require(isinstance(milestones, list) and bool(milestones), "milestones must be a non-empty array", errors)
    require(isinstance(labels, list) and bool(labels), "labels must be a non-empty array", errors)
    require(isinstance(items, list) and bool(items), "items must be a non-empty array", errors)
    if not isinstance(milestones, list) or not isinstance(labels, list) or not isinstance(items, list):
        raise RoadmapError("\n".join(errors))

    milestone_by_id: dict[str, dict[str, Any]] = {}
    for index, milestone in enumerate(milestones):
        name = f"milestones[{index}]"
        require(isinstance(milestone, dict), f"{name} must be an object", errors)
        if not isinstance(milestone, dict):
            continue
        mid = milestone.get("id")
        title = milestone.get("title")
        order = milestone.get("order")
        state = milestone.get("state")
        description = milestone.get("description")
        require(isinstance(mid, str) and bool(mid), f"{name}.id must be non-empty", errors)
        require(isinstance(title, str) and 5 <= len(title) <= 120, f"{name}.title must be 5–120 characters", errors)
        require(isinstance(order, int) and order >= 0, f"{name}.order must be non-negative", errors)
        require(state in {"open", "closed"}, f"{name}.state must be open or closed", errors)
        require(isinstance(description, str) and 10 <= len(description) <= 240, f"{name}.description must be 10–240 characters", errors)
        if isinstance(mid, str):
            milestone_by_id[mid] = milestone
    unique((m.get("id", "") for m in milestones if isinstance(m, dict)), "milestone IDs", errors)
    unique((m.get("title", "") for m in milestones if isinstance(m, dict)), "milestone titles", errors)
    orders = [m.get("order") for m in milestones if isinstance(m, dict) and isinstance(m.get("order"), int)]
    unique((str(value) for value in orders), "milestone orders", errors)
    if sorted(orders) != list(range(len(orders))):
        errors.append("milestone order values must be contiguous from 0")

    label_names: set[str] = set()
    for index, label in enumerate(labels):
        name = f"labels[{index}]"
        require(isinstance(label, dict), f"{name} must be an object", errors)
        if not isinstance(label, dict):
            continue
        lname = label.get("name")
        color = label.get("color")
        description = label.get("description")
        require(isinstance(lname, str) and bool(lname), f"{name}.name must be non-empty", errors)
        require(isinstance(color, str) and bool(re.fullmatch(r"[0-9A-Fa-f]{6}", color)), f"{name}.color must be six hexadecimal digits", errors)
        require(isinstance(description, str) and 5 <= len(description) <= 160, f"{name}.description must be 5–160 characters", errors)
        if isinstance(lname, str):
            label_names.add(lname)
    unique((l.get("name", "") for l in labels if isinstance(l, dict)), "label names", errors)
    for required in {"roadmap", "roadmap:public", "roadmap:internal", *AGENT_LABELS.values()}:
        require(required in label_names, f"missing required label {required}", errors)
    areas = {value.removeprefix("area:") for value in label_names if value.startswith("area:")}
    kinds = {value.removeprefix("kind:") for value in label_names if value.startswith("kind:")}

    item_by_id: dict[str, dict[str, Any]] = {}
    coverage: set[str] = set()
    for index, item in enumerate(items):
        name = f"items[{index}]"
        require(isinstance(item, dict), f"{name} must be an object", errors)
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if isinstance(item_id, str):
            name = item_id
        require(isinstance(item_id, str) and bool(ROADMAP_ID_RE.fullmatch(item_id)), f"{name}.id is invalid", errors)
        for field, minimum, maximum in (
            ("title", 8, 120), ("summary", 20, 320), ("outcome", 20, 420), ("whyNow", 20, 420)
        ):
            value = item.get(field)
            require(isinstance(value, str) and minimum <= len(value) <= maximum, f"{name}.{field} must be {minimum}–{maximum} characters", errors)
        milestone = item.get("milestone")
        area = item.get("area")
        kind = item.get("kind")
        state = item.get("seedState")
        visibility = item.get("visibility")
        require(milestone in milestone_by_id, f"{name} references unknown milestone {milestone!r}", errors)
        require(area in areas, f"{name} references unknown area {area!r}", errors)
        require(kind in kinds, f"{name} references unknown kind {kind!r}", errors)
        require(state in WORK_STATES, f"{name}.seedState is invalid", errors)
        require(visibility in VISIBILITIES, f"{name}.visibility is invalid", errors)
        blockers = item.get("blockedBy")
        gates = item.get("acceptanceIds")
        context = item.get("contextPaths")
        non_goals = item.get("nonGoals")
        validation = item.get("validation")
        require(isinstance(blockers, list) and all(isinstance(v, str) for v in blockers), f"{name}.blockedBy must be a string array", errors)
        require(isinstance(gates, list) and all(isinstance(v, str) and v in REQUIRED_GATES for v in gates), f"{name}.acceptanceIds contains an invalid gate", errors)
        require(isinstance(context, list) and len(context) <= 8 and all(isinstance(v, str) and safe_relative(v) for v in context), f"{name}.contextPaths must contain at most eight safe paths", errors)
        require(isinstance(non_goals, list) and bool(non_goals) and all(isinstance(v, str) and v.strip() for v in non_goals), f"{name}.nonGoals must be a non-empty string array", errors)
        require(isinstance(validation, list) and bool(validation) and all(isinstance(v, str) and v.strip() for v in validation), f"{name}.validation must be a non-empty string array", errors)
        packet = item.get("taskPacket")
        require(packet is None or (isinstance(packet, str) and safe_relative(packet)), f"{name}.taskPacket must be null or a safe path", errors)
        if isinstance(packet, str):
            require((root / packet).is_file(), f"{name}.taskPacket does not exist: {packet}", errors)
        if isinstance(context, list):
            for relative in context:
                require((root / relative).exists(), f"{name}.contextPath does not exist: {relative}", errors)
        if isinstance(item_id, str):
            item_by_id[item_id] = item
        if isinstance(gates, list):
            coverage.update(gates)
    unique((i.get("id", "") for i in items if isinstance(i, dict)), "roadmap item IDs", errors)
    require(set(item_by_id) == REQUIRED_ITEMS, "roadmap item set differs from the reviewed inventory", errors)
    require(REQUIRED_POST_MVP <= set(item_by_id), "accepted post-MVP directions are incomplete", errors)
    require(REQUIRED_RELEASE_DEBT <= set(item_by_id), "release-blocking/open-debt coverage is incomplete", errors)
    require(coverage == REQUIRED_GATES, f"acceptance coverage differs: missing={sorted(REQUIRED_GATES-coverage)} extra={sorted(coverage-REQUIRED_GATES)}", errors)

    for item_id, item in item_by_id.items():
        blockers = item.get("blockedBy", [])
        unique(blockers, f"blockers for {item_id}", errors)
        for blocker in blockers:
            require(blocker in item_by_id, f"{item_id} references unknown blocker {blocker}", errors)
            if blocker in item_by_id:
                left = milestone_by_id[item["milestone"]]["order"]
                right = milestone_by_id[item_by_id[blocker]["milestone"]]["order"]
                require(right <= left, f"{item_id} is blocked by later-milestone item {blocker}", errors)
            require(blocker != item_id, f"{item_id} cannot block itself", errors)

    visiting: list[str] = []
    complete: set[str] = set()
    def visit(item_id: str) -> None:
        if item_id in complete:
            return
        if item_id in visiting:
            cycle = visiting[visiting.index(item_id):] + [item_id]
            errors.append("roadmap dependency cycle: " + " -> ".join(cycle))
            return
        visiting.append(item_id)
        for blocker in item_by_id[item_id].get("blockedBy", []):
            if blocker in item_by_id:
                visit(blocker)
        visiting.pop()
        complete.add(item_id)
    for item_id in sorted(item_by_id):
        visit(item_id)

    dag = read_json(root / "agents/task-dag.json")
    active_task_ids = {task["id"] for task in dag.get("tasks", []) if isinstance(task, dict) and isinstance(task.get("id"), str)}
    active_seed = {
        Path(item["taskPacket"]).parent.name
        for item in items
        if isinstance(item, dict) and item.get("seedState") == "active" and isinstance(item.get("taskPacket"), str)
    }
    require(active_seed == active_task_ids, f"active seed/task DAG disagreement: seed={sorted(active_seed)} dag={sorted(active_task_ids)}", errors)

    if errors:
        raise RoadmapError("\n".join(errors))
    return {
        "milestones": len(milestones),
        "labels": len(labels),
        "items": len(items),
        "dependencies": sum(len(item["blockedBy"]) for item in items),
        "acceptanceCoverage": sorted(coverage),
        "sourceHash": sha256_json(seed),
    }


def parse_acceptance() -> dict[str, dict[str, str]]:
    gates: dict[str, dict[str, str]] = {}
    for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        match = LEDGER_ROW_RE.match(line)
        if match:
            gates[match.group("id")] = match.groupdict()
    if set(gates) != REQUIRED_GATES:
        raise RoadmapError("acceptance ledger does not contain B01–B20 and U01–U04 exactly once")
    return gates


def active_authorization() -> dict[str, Any]:
    dag = read_json(DAG_PATH)
    registry = read_json(REGISTRY_PATH)
    status_by_id = {item.get("id"): item.get("status") for item in registry.get("tasks", []) if isinstance(item, dict)}
    return {
        "phase": dag.get("phase", {}),
        "tasks": [
            {
                "id": task.get("id"),
                "slug": task.get("slug"),
                "status": status_by_id.get(task.get("id")),
            }
            for task in dag.get("tasks", [])
            if isinstance(task, dict)
        ],
    }


def issue_body(item: dict[str, Any], seed_hash: str) -> str:
    packet = item.get("taskPacket") or ""
    lines = [
        f"<!-- roadmap-id: {item['id']} -->",
        f"<!-- roadmap-schema: {SCHEMA_VERSION} -->",
        f"<!-- roadmap-seed-hash: {seed_hash} -->",
        f"<!-- public-summary: {item['summary']} -->",
        f"<!-- task-packet: {packet} -->",
        "",
        "## Public summary",
        "",
        item["summary"],
        "",
        "## Observable outcome",
        "",
        item["outcome"],
        "",
        "## Why now",
        "",
        item["whyNow"],
        "",
        "## Acceptance criteria",
        "",
        f"- [ ] The observable outcome above is true and reviewable.",
    ]
    lines.extend(f"- [ ] {value}" for value in item["validation"])
    lines += ["", "## Acceptance gates", ""]
    lines.append(", ".join(item["acceptanceIds"]) if item["acceptanceIds"] else "No direct product gate; this remains planning, foundation, or post-MVP work.")
    lines += ["", "## Context paths", ""]
    lines.extend(f"- `{value}`" for value in item["contextPaths"])
    lines += ["", "## Non-goals", ""]
    lines.extend(f"- {value}" for value in item["nonGoals"])
    lines += [
        "",
        "## Planning contract",
        "",
        "- This issue may be split, merged, reordered, deferred, or superseded during a reviewed phase boundary.",
        "- Issue state and labels do not authorize implementation; `agents/task-dag.json` and an active packet do.",
        "- Closing this issue does not change the acceptance ledger.",
        "",
    ]
    return "\n".join(lines)


@dataclasses.dataclass
class ApiResult:
    status: int
    headers: dict[str, str]
    value: Any


class GitHubClient:
    def __init__(self, repository: str, token: str | None, api_url: str = "https://api.github.com") -> None:
        self.repository = repository
        self.owner, self.repo = repository.split("/", 1)
        self.token = token
        self.api_url = api_url.rstrip("/")

    def call(self, method: str, path: str, payload: Any | None = None, *, accept: str = "application/vnd.github+json", retries: int = 5) -> ApiResult:
        url = self.api_url + path
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": accept, "X-GitHub-Api-Version": API_VERSION, "User-Agent": "salvagenet-roadmap/1"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if data is not None:
            headers["Content-Type"] = "application/json"
        for attempt in range(retries):
            req = request.Request(url, data=data, headers=headers, method=method)
            try:
                with request.urlopen(req, timeout=45) as response:
                    raw = response.read()
                    value = json.loads(raw) if raw else None
                    return ApiResult(response.status, {k.lower(): v for k, v in response.headers.items()}, value)
            except error.HTTPError as exc:
                raw = exc.read()
                detail = raw.decode("utf-8", "replace")[:1200]
                if exc.code in {403, 429, 502, 503, 504} and attempt + 1 < retries:
                    retry_after = exc.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 20)
                    time.sleep(delay)
                    continue
                raise RoadmapError(f"GitHub API {method} {path} failed: HTTP {exc.code}: {detail}") from exc
            except error.URLError as exc:
                if attempt + 1 < retries:
                    time.sleep(min(2 ** attempt, 20))
                    continue
                raise RoadmapError(f"GitHub API {method} {path} failed: {exc}") from exc
        raise AssertionError("unreachable")

    def paginate(self, path: str) -> list[Any]:
        separator = "&" if "?" in path else "?"
        page = 1
        values: list[Any] = []
        while True:
            result = self.call("GET", f"{path}{separator}per_page=100&page={page}")
            if not isinstance(result.value, list):
                raise RoadmapError(f"expected array from {path}")
            values.extend(result.value)
            if len(result.value) < 100:
                return values
            page += 1
            if page > 50:
                raise RoadmapError(f"pagination bound exceeded for {path}")

    def repo_path(self, suffix: str) -> str:
        return f"/repos/{self.owner}/{self.repo}{suffix}"


def current_agent_label(item: dict[str, Any], authorization: dict[str, Any]) -> str | None:
    packet = item.get("taskPacket")
    task_id = Path(packet).parent.name if isinstance(packet, str) else None
    active = {task.get("id") for task in authorization.get("tasks", [])}
    if task_id in active:
        return "agent:active"
    return AGENT_LABELS.get(item.get("seedState"))


def bootstrap(seed: dict[str, Any], client: GitHubClient, apply: bool, state_output: Path | None) -> dict[str, Any]:
    summary = validate_seed(seed)
    seed_hash = summary["sourceHash"]
    authorization = active_authorization()
    existing_labels = {item["name"]: item for item in client.paginate(client.repo_path("/labels"))}
    existing_milestones = {item["title"]: item for item in client.paginate(client.repo_path("/milestones?state=all"))}
    all_issues = client.paginate(client.repo_path("/issues?state=all"))
    roadmap_issues: dict[str, dict[str, Any]] = {}
    for issue in all_issues:
        if "pull_request" in issue:
            continue
        marker = ROADMAP_MARKER_RE.search(issue.get("body") or "")
        if marker:
            item_id = marker.group(1)
            if item_id in roadmap_issues:
                raise RoadmapError(f"duplicate live roadmap ID {item_id}")
            roadmap_issues[item_id] = issue

    plan: list[str] = []
    for label in seed["labels"]:
        live = existing_labels.get(label["name"])
        if live is None:
            plan.append(f"create label {label['name']}")
            if apply:
                client.call("POST", client.repo_path("/labels"), {"name": label["name"], "color": label["color"], "description": label["description"]})
                time.sleep(0.15)
        elif live.get("color", "").lower() != label["color"].lower() or (live.get("description") or "") != label["description"]:
            plan.append(f"label metadata drift {label['name']}")

    milestone_by_id: dict[str, dict[str, Any]] = {}
    for milestone in seed["milestones"]:
        live = existing_milestones.get(milestone["title"])
        if live is None:
            plan.append(f"create milestone {milestone['title']}")
            if apply:
                created = client.call("POST", client.repo_path("/milestones"), {"title": milestone["title"], "state": milestone["state"], "description": milestone["description"]}).value
                live = created
                time.sleep(0.2)
        elif (live.get("description") or "") != milestone["description"] or live.get("state") != milestone["state"]:
            plan.append(f"milestone metadata drift {milestone['title']}")
        if live is not None:
            milestone_by_id[milestone["id"]] = live

    for item in seed["items"]:
        live = roadmap_issues.get(item["id"])
        labels = ["roadmap", f"roadmap:{item['visibility']}", f"area:{item['area']}", f"kind:{item['kind']}"]
        agent_label = current_agent_label(item, authorization)
        if agent_label:
            labels.append(agent_label)
        if live is None:
            plan.append(f"create issue {item['id']}")
            if apply:
                milestone = milestone_by_id.get(item["milestone"])
                if milestone is None:
                    raise RoadmapError(f"milestone unavailable for {item['id']}")
                payload = {
                    "title": f"[{item['id']}] {item['title']}",
                    "body": issue_body(item, seed_hash),
                    "labels": labels,
                    "milestone": milestone["number"],
                }
                live = client.call("POST", client.repo_path("/issues"), payload).value
                roadmap_issues[item["id"]] = live
                time.sleep(0.35)
                if item["seedState"] == "done":
                    live = client.call("PATCH", client.repo_path(f"/issues/{live['number']}"), {"state": "closed", "state_reason": "completed"}).value
                    roadmap_issues[item["id"]] = live
                    time.sleep(0.25)
        else:
            expected = {"roadmap", f"roadmap:{item['visibility']}", f"area:{item['area']}", f"kind:{item['kind']}"}
            actual = {label["name"] for label in live.get("labels", [])}
            missing = sorted(expected - actual)
            if missing:
                plan.append(f"issue metadata drift {item['id']}: missing labels {missing}")
            marker_hash = re.search(r"<!--\s*roadmap-seed-hash:\s*([^\s]+)\s*-->", live.get("body") or "")
            if not marker_hash:
                plan.append(f"issue body drift {item['id']}: bootstrap hash marker absent")

    if apply:
        missing = REQUIRED_ITEMS - set(roadmap_issues)
        if missing:
            raise RoadmapError(f"bootstrap did not create all issues: {sorted(missing)}")

    dependency_count = 0
    issue_map: dict[str, dict[str, int]] = {}
    for item_id, live in roadmap_issues.items():
        issue_map[item_id] = {"number": int(live["number"]), "id": int(live["id"])}
    for item in seed["items"]:
        if item["id"] not in roadmap_issues:
            continue
        issue = roadmap_issues[item["id"]]
        current = client.paginate(client.repo_path(f"/issues/{issue['number']}/dependencies/blocked_by"))
        current_ids = {int(value["id"]) for value in current}
        expected_ids = {issue_map[blocker]["id"] for blocker in item["blockedBy"] if blocker in issue_map}
        for blocker in item["blockedBy"]:
            dependency_count += 1
            blocker_id = issue_map.get(blocker, {}).get("id")
            if blocker_id is None:
                plan.append(f"cannot add dependency {item['id']} <- {blocker}: blocker missing")
            elif blocker_id not in current_ids:
                plan.append(f"add dependency {item['id']} <- {blocker}")
                if apply:
                    client.call("POST", client.repo_path(f"/issues/{issue['number']}/dependencies/blocked_by"), {"issue_id": blocker_id})
                    time.sleep(0.4)
        extra = current_ids - expected_ids
        if extra:
            plan.append(f"dependency drift {item['id']}: {len(extra)} extra blocker(s); not removed")

    result = {
        "schemaVersion": SCHEMA_VERSION,
        "repository": seed["repository"],
        "seedHash": seed_hash,
        "appliedAt": utc_now() if apply else None,
        "mode": "apply" if apply else "dry-run",
        "milestones": len(seed["milestones"]),
        "labels": len(seed["labels"]),
        "issues": len(roadmap_issues),
        "dependencies": dependency_count,
        "issueMap": issue_map,
        "plan": plan,
    }
    if apply and state_output:
        state_output.parent.mkdir(parents=True, exist_ok=True)
        state_output.write_text(json.dumps({key: value for key, value in result.items() if key != "plan"}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def parse_issue_summary(issue: dict[str, Any]) -> tuple[str, str | None, str]:
    body = issue.get("body") or ""
    marker = ROADMAP_MARKER_RE.search(body)
    if not marker:
        raise RoadmapError(f"roadmap-labelled issue #{issue.get('number')} has no stable ID marker")
    task = TASK_MARKER_RE.search(body)
    summary = SUMMARY_MARKER_RE.search(body)
    return marker.group(1), task.group(1).strip() if task and task.group(1).strip() else None, summary.group(1).strip() if summary else ""


def fetch_live_graph(client: GitHubClient) -> dict[str, Any]:
    milestones = client.paginate(client.repo_path("/milestones?state=all"))
    issues = client.paginate(client.repo_path("/issues?state=all"))
    roadmap: dict[str, dict[str, Any]] = {}
    newest: str | None = None
    for issue in issues:
        if "pull_request" in issue:
            continue
        labels = {label["name"] for label in issue.get("labels", [])}
        if "roadmap" not in labels:
            continue
        item_id, task_packet, summary = parse_issue_summary(issue)
        if item_id in roadmap:
            raise RoadmapError(f"duplicate live roadmap ID {item_id}")
        updated = issue.get("updated_at")
        if isinstance(updated, str) and (newest is None or updated > newest):
            newest = updated
        roadmap[item_id] = {
            "id": item_id,
            "number": int(issue["number"]),
            "nodeId": issue.get("node_id"),
            "databaseId": int(issue["id"]),
            "title": re.sub(r"^\[[A-Z0-9-]+\]\s*", "", issue["title"]),
            "summary": summary,
            "url": issue["html_url"],
            "issueState": issue["state"],
            "labels": sorted(labels),
            "milestoneNumber": issue.get("milestone", {}).get("number") if issue.get("milestone") else None,
            "milestoneTitle": issue.get("milestone", {}).get("title") if issue.get("milestone") else None,
            "taskPacket": task_packet,
            "updatedAt": updated,
            "blockedBy": [],
        }
    if set(roadmap) != REQUIRED_ITEMS:
        raise RoadmapError(f"live roadmap item set is incomplete: missing={sorted(REQUIRED_ITEMS-set(roadmap))} extra={sorted(set(roadmap)-REQUIRED_ITEMS)}")
    by_database_id = {item["databaseId"]: item_id for item_id, item in roadmap.items()}
    for item_id, item in roadmap.items():
        dependencies = client.paginate(client.repo_path(f"/issues/{item['number']}/dependencies/blocked_by"))
        blockers: list[str] = []
        for dependency in dependencies:
            blocker_id = by_database_id.get(int(dependency["id"]))
            if blocker_id is None:
                raise RoadmapError(f"{item_id} is blocked by a non-roadmap issue #{dependency.get('number')}")
            blockers.append(blocker_id)
        item["blockedBy"] = sorted(blockers)
    milestone_view = [
        {
            "number": int(value["number"]),
            "title": value["title"],
            "state": value["state"],
            "description": value.get("description") or "",
        }
        for value in milestones
        if value["title"].startswith(("M0", "M1", "M2", "M3", "M4", "MVP+"))
    ]
    return {"repository": client.repository, "newestIssueUpdate": newest, "milestones": milestone_view, "items": roadmap}


def work_state(item: dict[str, Any]) -> str:
    if item["issueState"] == "closed":
        return "done"
    labels = set(item["labels"])
    for state in ("active", "review", "ready", "hold", "queued"):
        if AGENT_LABELS[state] in labels:
            return state
    return "planned"


def derive_snapshot(graph: dict[str, Any], *, fallback: bool, generated_at: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    generated_at = generated_at or utc_now()
    authorization = active_authorization()
    active_task_ids = {task["id"] for task in authorization["tasks"]}
    gates = parse_acceptance()
    items = copy.deepcopy(graph["items"])
    open_ids = {item_id for item_id, item in items.items() if item["issueState"] != "closed"}
    disagreements: list[str] = []
    public_items: list[dict[str, Any]] = []
    index_items: list[dict[str, Any]] = []
    for item_id in sorted(items):
        item = items[item_id]
        state = work_state(item)
        dependency_state = "blocked" if any(blocker in open_ids for blocker in item["blockedBy"]) else "clear"
        task_id = Path(item["taskPacket"]).parent.name if item.get("taskPacket") else None
        authorized = task_id in active_task_ids if task_id else False
        if state == "active" and not authorized:
            disagreements.append(f"{item_id} is labelled active but its task is not in the active DAG")
        if authorized and state != "active":
            disagreements.append(f"{item_id} is authorized by the DAG but is not labelled active")
        if state == "active" and dependency_state == "blocked":
            disagreements.append(f"{item_id} is active while an issue dependency remains open")
        acceptance = [
            {"id": gate_id, "status": gates[gate_id]["status"]}
            for gate_id in sorted(gate for gate in REQUIRED_GATES if gate in item.get("acceptanceIds", []))
        ]
        projection = {
            "id": item_id,
            "number": item["number"],
            "title": item["title"],
            "summary": item["summary"],
            "url": item["url"],
            "milestone": item["milestoneTitle"],
            "area": next((label.removeprefix("area:") for label in item["labels"] if label.startswith("area:")), "unknown"),
            "kind": next((label.removeprefix("kind:") for label in item["labels"] if label.startswith("kind:")), "unknown"),
            "public": "roadmap:public" in item["labels"],
            "workState": state,
            "dependencyState": dependency_state,
            "blockedBy": item["blockedBy"],
            "taskPacket": item.get("taskPacket"),
            "taskAuthorized": authorized,
            "acceptance": acceptance,
            "updatedAt": item.get("updatedAt"),
        }
        public_items.append(projection)
        index_items.append({key: projection[key] for key in ("id", "number", "title", "workState", "dependencyState", "blockedBy", "taskPacket", "taskAuthorized", "acceptance")})
    normalized_for_hash = {"repository": graph["repository"], "milestones": graph["milestones"], "items": public_items}
    source_hash = sha256_json(normalized_for_hash)
    snapshot = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "source": {
            "repository": graph["repository"],
            "sourceHash": source_hash,
            "newestIssueUpdate": graph.get("newestIssueUpdate"),
            "fallback": fallback,
        },
        "milestones": sorted(graph["milestones"], key=lambda value: value["number"]),
        "items": public_items,
        "disagreements": disagreements,
    }
    active = [item for item in index_items if item["workState"] == "active"]
    ready = [item for item in index_items if item["workState"] == "ready" and item["dependencyState"] == "clear"]
    blocked = [item for item in index_items if item["dependencyState"] == "blocked" and item["workState"] != "done"]
    current_milestone = None
    if active:
        active_id = active[0]["id"]
        current_milestone = next((item["milestone"] for item in public_items if item["id"] == active_id), None)
    index = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "sourceHash": source_hash,
        "currentMilestone": current_milestone,
        "active": active,
        "ready": ready,
        "blocked": blocked,
        "disagreements": disagreements,
    }
    return snapshot, index


def seed_graph(seed: dict[str, Any]) -> dict[str, Any]:
    milestone_number = {value["id"]: value["order"] + 1 for value in seed["milestones"]}
    milestone_title = {value["id"]: value["title"] for value in seed["milestones"]}
    items: dict[str, Any] = {}
    for item in seed["items"]:
        labels = ["roadmap", f"roadmap:{item['visibility']}", f"area:{item['area']}", f"kind:{item['kind']}"]
        agent = AGENT_LABELS.get(item["seedState"])
        if agent:
            labels.append(agent)
        items[item["id"]] = {
            "id": item["id"], "number": None, "title": item["title"], "summary": item["summary"],
            "url": None, "issueState": "closed" if item["seedState"] == "done" else "open",
            "labels": labels, "milestoneNumber": milestone_number[item["milestone"]],
            "milestoneTitle": milestone_title[item["milestone"]], "taskPacket": item.get("taskPacket"),
            "updatedAt": None, "blockedBy": list(item["blockedBy"]),
        }
    return {
        "repository": seed["repository"],
        "newestIssueUpdate": None,
        "milestones": [
            {"number": value["order"] + 1, "title": value["title"], "state": value["state"], "description": value["description"]}
            for value in seed["milestones"]
        ],
        "items": items,
    }


def write_snapshots(snapshot: dict[str, Any], index: dict[str, Any]) -> None:
    for path, value in ((SNAPSHOT_PATH, snapshot), (INDEX_PATH, index)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def sync_live(client: GitHubClient | None, *, write: bool, strict_live: bool, max_age_hours: int = 72) -> tuple[dict[str, Any], dict[str, Any]]:
    failure: Exception | None = None
    if client is not None:
        try:
            graph = fetch_live_graph(client)
            snapshot, index = derive_snapshot(graph, fallback=False)
            if write:
                write_snapshots(snapshot, index)
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                (CACHE_DIR / "roadmap.v1.json").write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                (CACHE_DIR / "fetched-at.json").write_text(json.dumps({"fetchedAt": snapshot["generatedAt"], "sourceHash": snapshot["source"]["sourceHash"]}, indent=2) + "\n", encoding="utf-8")
            return snapshot, index
        except Exception as exc:  # fallback is deliberate and validated below
            failure = exc
            if strict_live:
                raise
    if SNAPSHOT_PATH.is_file() and INDEX_PATH.is_file():
        snapshot = read_json(SNAPSHOT_PATH)
        index = read_json(INDEX_PATH)
        generated = snapshot.get("generatedAt")
        if not isinstance(generated, str):
            raise RoadmapError("fallback snapshot has no generatedAt")
        age = dt.datetime.now(dt.timezone.utc) - parse_time(generated)
        if age > dt.timedelta(hours=max_age_hours):
            raise RoadmapError(f"fallback snapshot is stale ({age}); live error: {failure}")
        snapshot = copy.deepcopy(snapshot)
        snapshot["source"]["fallback"] = True
        snapshot["source"]["fallbackReason"] = str(failure)[:500] if failure else "live fetch not requested"
        if write:
            write_snapshots(snapshot, index)
        return snapshot, index
    seed = load_seed()
    validate_seed(seed)
    snapshot, index = derive_snapshot(seed_graph(seed), fallback=True)
    snapshot["source"]["fallbackReason"] = "pre-bootstrap seed projection"
    if write:
        write_snapshots(snapshot, index)
    return snapshot, index


def bounded_context(snapshot: dict[str, Any], selector: str, *, max_files: int = 12, max_bytes: int = 65536) -> str:
    item = next((value for value in snapshot.get("items", []) if str(value.get("number")) == selector or value.get("id") == selector), None)
    if item is None:
        raise RoadmapError(f"roadmap item not found: {selector}")
    lines = [
        f"# Roadmap context: {item['id']} — {item['title']}", "",
        f"- Issue: {item.get('url') or 'not materialized'}",
        f"- Milestone: {item.get('milestone')}",
        f"- Work state: {item.get('workState')}",
        f"- Dependency state: {item.get('dependencyState')}",
        f"- Task authorized: {item.get('taskAuthorized')}",
        f"- Task packet: {item.get('taskPacket') or 'none'}",
        f"- Blocked by: {', '.join(item.get('blockedBy', [])) or 'none'}", "",
        "## Public summary", "", item.get("summary") or "", "",
        "## Acceptance links", "",
    ]
    acceptance = item.get("acceptance", [])
    lines.extend(f"- {gate['id']}: {gate['status']}" for gate in acceptance)
    if not acceptance:
        lines.append("- No direct acceptance gate.")
    lines += ["", "## Context files", ""]
    seed_item = next((value for value in load_seed()["items"] if value["id"] == item["id"]), None)
    context_paths = list(seed_item.get("contextPaths", [])) if seed_item else []
    if len(context_paths) > max_files:
        raise RoadmapError(f"context file bound exceeded: {len(context_paths)} > {max_files}")
    lines.extend(f"- `{value}`" for value in context_paths)
    text = "\n".join(lines).rstrip() + "\n"
    if len(text.encode("utf-8")) > max_bytes:
        raise RoadmapError(f"context byte bound exceeded: {len(text.encode('utf-8'))} > {max_bytes}")
    return text


def print_status(index: dict[str, Any]) -> None:
    print(f"Roadmap source: {index.get('sourceHash')}")
    print(f"Generated: {index.get('generatedAt')}")
    print(f"Current milestone: {index.get('currentMilestone') or 'none'}")
    for heading, key in (("ACTIVE", "active"), ("READY", "ready"), ("BLOCKED", "blocked")):
        print(f"\n{heading}")
        values = index.get(key, [])
        if not values:
            print("none")
        for item in values:
            blockers = f" <- {', '.join(item['blockedBy'])}" if item.get("blockedBy") else ""
            number = f"#{item['number']} " if item.get("number") else ""
            print(f"{number}{item['id']} {item['title']}{blockers}")
    if index.get("disagreements"):
        print("\nDISAGREEMENTS")
        for value in index["disagreements"]:
            print(f"- {value}")


def cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate-seed")
    bootstrap_parser = sub.add_parser("bootstrap")
    bootstrap_parser.add_argument("--apply", action="store_true")
    bootstrap_parser.add_argument("--state-output", type=Path)
    sync_parser = sub.add_parser("sync")
    sync_parser.add_argument("--write", action="store_true")
    sync_parser.add_argument("--strict-live", action="store_true")
    sync_parser.add_argument("--seed-only", action="store_true")
    sub.add_parser("status")
    check_parser = sub.add_parser("check")
    check_parser.add_argument("--max-age-hours", type=int, default=72)
    context_parser = sub.add_parser("context")
    context_parser.add_argument("selector")
    context_parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    seed = load_seed()
    if args.command == "validate-seed":
        print(json.dumps(validate_seed(seed), indent=2, sort_keys=True))
        return 0

    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    client = GitHubClient(seed["repository"], token) if token and args.command in {"bootstrap", "sync", "check"} else None
    if args.command == "bootstrap":
        if client is None:
            raise RoadmapError("GH_TOKEN or GITHUB_TOKEN is required for live bootstrap")
        result = bootstrap(seed, client, args.apply, args.state_output)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "sync":
        live = None if args.seed_only else client
        snapshot, index = sync_live(live, write=args.write, strict_live=args.strict_live)
        print(json.dumps({"source": snapshot["source"], "active": len(index["active"]), "blocked": len(index["blocked"]), "disagreements": index["disagreements"]}, indent=2))
        return 0
    if args.command == "status":
        _, index = sync_live(None, write=False, strict_live=False)
        print_status(index)
        return 0
    if args.command == "check":
        if client is None:
            raise RoadmapError("GH_TOKEN or GITHUB_TOKEN is required for freshness check")
        live_snapshot, _ = sync_live(client, write=False, strict_live=True)
        committed = read_json(SNAPSHOT_PATH)
        current = committed.get("source", {}).get("sourceHash")
        live = live_snapshot.get("source", {}).get("sourceHash")
        if current != live:
            raise RoadmapError(f"roadmap snapshot is stale: committed={current} live={live}")
        generated = committed.get("generatedAt")
        if not isinstance(generated, str) or dt.datetime.now(dt.timezone.utc) - parse_time(generated) > dt.timedelta(hours=args.max_age_hours):
            raise RoadmapError("roadmap snapshot age exceeds policy")
        print("roadmap snapshot is current")
        return 0
    if args.command == "context":
        snapshot = read_json(SNAPSHOT_PATH)
        text = bounded_context(snapshot, args.selector)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
            print(args.output)
        else:
            print(text, end="")
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    try:
        raise SystemExit(cli())
    except RoadmapError as exc:
        print(f"roadmap error: {exc}", file=sys.stderr)
        raise SystemExit(2)
