#!/usr/bin/env python3
"""Validate projects/*.yml and generate site/data.json.

Everything the dashboard shows that isn't typed by hand is computed here: plan
adherence, slippage, item ages, staleness and portfolio rollups. The site itself does
no date arithmetic, so what you see is always as of the last build.

    python3 scripts/build.py           # validate + write site/data.json
    python3 scripts/build.py --check   # validate only

Set DASHBOARD_TODAY=YYYY-MM-DD to pin "today" (used by the tests).
Exit codes: 0 ok, 1 validation errors.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECTS_DIR = ROOT / "projects"
OUT = ROOT / "site" / "data.json"

STALE_AFTER_DAYS = 7
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")

STATUS = ["green", "amber", "red", "paused", "done"]
STAGE = ["discovery", "build", "review", "shipped"]
MILESTONE_STATUS = ["done", "in_progress", "todo", "blocked"]
SEVERITY = ["high", "medium", "low"]

# Order projects so the ones needing attention come first.
STATUS_RANK = {"red": 0, "amber": 1, "green": 2, "paused": 3, "done": 4}


class Errors:
    """Collects every problem in every file, so one run tells you all of it."""

    def __init__(self):
        self.items: list[str] = []

    def add(self, where: str, msg: str):
        self.items.append(f"{where}: {msg}")

    def __bool__(self):
        return bool(self.items)


# ------------------------------------------------------------------------ validation

def check_str(errs, where, obj, key, *, required=True, max_len=None, default=None):
    val = obj.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        if required:
            errs.add(where, f"missing required field '{key}'")
        return default
    if not isinstance(val, str):
        errs.add(where, f"'{key}' must be text, got {type(val).__name__}")
        return default
    val = val.strip()
    if max_len and len(val) > max_len:
        errs.add(where, f"'{key}' is {len(val)} chars, limit is {max_len} "
                        f"(keep it generic — see PRIVACY.md)")
    return val


def check_enum(errs, where, obj, key, allowed, *, required=True):
    val = obj.get(key)
    if val is None:
        if required:
            errs.add(where, f"missing required field '{key}'")
        return None
    if val not in allowed:
        errs.add(where, f"'{key}' is '{val}', must be one of: {', '.join(allowed)}")
        return None
    return val


def check_date(errs, where, obj, key, *, required=True):
    val = obj.get(key)
    if val is None:
        if required:
            errs.add(where, f"missing required field '{key}'")
        return None
    if isinstance(val, dt.datetime):
        return val.date()
    if isinstance(val, dt.date):
        return val
    if isinstance(val, str):
        try:
            return dt.date.fromisoformat(val.strip())
        except ValueError:
            pass
    errs.add(where, f"'{key}' must be a date as YYYY-MM-DD, got {val!r}")
    return None


def check_list(errs, where, obj, key, *, required=False):
    val = obj.get(key)
    if val is None:
        if required:
            errs.add(where, f"missing required field '{key}'")
        return []
    if not isinstance(val, list):
        errs.add(where, f"'{key}' must be a list")
        return []
    for i, item in enumerate(val):
        if not isinstance(item, dict):
            errs.add(f"{where}.{key}[{i}]", "each entry must be a mapping of fields")
            return []
    return val


def days_between(a: dt.date, b: dt.date) -> int:
    return (a - b).days


# --------------------------------------------------------------------------- loading

def load_project(path: pathlib.Path, today: dt.date, errs: Errors) -> dict | None:
    where = path.relative_to(ROOT).as_posix()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errs.add(where, f"not valid YAML — {str(exc).splitlines()[0]}")
        return None
    if not isinstance(raw, dict):
        errs.add(where, "file must contain a mapping of fields at the top level")
        return None

    pid = check_str(errs, where, raw, "id")
    if pid and not SLUG.match(pid):
        errs.add(where, f"'id' must be lowercase letters, digits and hyphens: got '{pid}'")
    if pid and pid != path.stem:
        errs.add(where, f"'id' is '{pid}' but the filename is '{path.stem}.yml' — "
                        f"they must match")

    p = {
        "id": pid,
        "codename": check_str(errs, where, raw, "codename", max_len=40),
        "summary": check_str(errs, where, raw, "summary", max_len=200),
        "status": check_enum(errs, where, raw, "status", STATUS),
        "stage": check_enum(errs, where, raw, "stage", STAGE),
        "started": check_date(errs, where, raw, "started"),
        "target": check_date(errs, where, raw, "target", required=False),
        "updated": check_date(errs, where, raw, "updated"),
    }

    if p["started"] and p["target"] and p["target"] < p["started"]:
        errs.add(where, "'target' is before 'started'")
    if p["updated"] and p["updated"] > today:
        errs.add(where, f"'updated' is in the future ({p['updated']})")

    p["plan"] = load_plan(raw, where, today, errs)
    p["next_action"] = load_next_action(raw, where, errs)
    p["blocked_on_me"] = load_blocked(raw, where, today, errs)
    p["waiting_on"] = load_waiting(raw, where, today, errs)
    p["risks"] = load_risks(raw, where, errs)
    p["links"] = load_links(raw, where, errs)
    p["log"] = load_log(raw, where, errs)

    known = {"id", "codename", "summary", "status", "stage", "started", "target",
             "updated", "plan", "next_action", "blocked_on_me", "waiting_on", "risks",
             "links", "log"}
    for extra in sorted(set(raw) - known):
        errs.add(where, f"unknown field '{extra}' — see schema/project.schema.md")

    return derive(p, today)


def load_plan(raw, where, today, errs) -> list[dict]:
    items = check_list(errs, where, raw, "plan", required=True)
    if not items:
        if "plan" in raw:
            errs.add(where, "'plan' must contain at least one milestone")
        return []

    seen, out = set(), []
    for i, m in enumerate(items):
        w = f"{where}.plan[{i}]"
        mid = check_str(errs, w, m, "id")
        if mid:
            if mid in seen:
                errs.add(w, f"duplicate milestone id '{mid}'")
            seen.add(mid)
        due = check_date(errs, w, m, "due", required=False)
        status = check_enum(errs, w, m, "status", MILESTONE_STATUS)
        overdue = (due is not None and status != "done" and due < today)
        out.append({
            "id": mid,
            "title": check_str(errs, w, m, "title", max_len=80),
            "status": status,
            "due": due.isoformat() if due else None,
            "note": check_str(errs, w, m, "note", required=False, max_len=160),
            "overdue": overdue,
            "days_overdue": days_between(today, due) if overdue else 0,
        })
    return out


def load_next_action(raw, where, errs) -> dict | None:
    na = raw.get("next_action")
    if na is None:
        return None
    if not isinstance(na, dict):
        errs.add(where, "'next_action' must be a mapping with a 'title'")
        return None
    w = f"{where}.next_action"
    due = check_date(errs, w, na, "due", required=False)
    return {
        "title": check_str(errs, w, na, "title", max_len=120),
        "due": due.isoformat() if due else None,
    }


def load_blocked(raw, where, today, errs) -> list[dict]:
    out = []
    for i, b in enumerate(check_list(errs, where, raw, "blocked_on_me")):
        w = f"{where}.blocked_on_me[{i}]"
        since = check_date(errs, w, b, "since")
        out.append({
            "title": check_str(errs, w, b, "title", max_len=120),
            "decision": check_str(errs, w, b, "decision", required=False, max_len=200),
            "since": since.isoformat() if since else None,
            "age_days": days_between(today, since) if since else 0,
        })
    out.sort(key=lambda x: -x["age_days"])  # oldest first: what's been ignored longest
    return out


def load_waiting(raw, where, today, errs) -> list[dict]:
    out = []
    for i, item in enumerate(check_list(errs, where, raw, "waiting_on")):
        w = f"{where}.waiting_on[{i}]"
        since = check_date(errs, w, item, "since")
        chase_after = check_date(errs, w, item, "chase_after", required=False)
        out.append({
            "title": check_str(errs, w, item, "title", max_len=120),
            "who": check_str(errs, w, item, "who", max_len=60),
            "since": since.isoformat() if since else None,
            "age_days": days_between(today, since) if since else 0,
            "chase": bool(chase_after and chase_after <= today),
        })
    out.sort(key=lambda x: (not x["chase"], -x["age_days"]))
    return out


def load_risks(raw, where, errs) -> list[dict]:
    out = []
    for i, r in enumerate(check_list(errs, where, raw, "risks")):
        w = f"{where}.risks[{i}]"
        out.append({
            "title": check_str(errs, w, r, "title", max_len=120),
            "severity": check_enum(errs, w, r, "severity", SEVERITY),
            "mitigation": check_str(errs, w, r, "mitigation", required=False, max_len=200),
        })
    out.sort(key=lambda x: SEVERITY.index(x["severity"]) if x["severity"] in SEVERITY else 9)
    return out


def load_links(raw, where, errs) -> list[dict]:
    out = []
    for i, item in enumerate(check_list(errs, where, raw, "links")):
        w = f"{where}.links[{i}]"
        url = check_str(errs, w, item, "url")
        if url and not url.startswith("https://"):
            errs.add(w, "'url' must start with https:// and point at a public page")
            url = None
        out.append({"label": check_str(errs, w, item, "label", max_len=40), "url": url})
    return [x for x in out if x["url"]]


def load_log(raw, where, errs) -> list[dict]:
    entries = check_list(errs, where, raw, "log")
    if len(entries) > 10:
        errs.add(where, f"'log' has {len(entries)} entries, limit is 10 — trim the oldest")
    out = []
    for i, e in enumerate(entries):
        w = f"{where}.log[{i}]"
        date = check_date(errs, w, e, "date")
        out.append({
            "date": date.isoformat() if date else None,
            "note": check_str(errs, w, e, "note", max_len=160),
        })
    out.sort(key=lambda x: x["date"] or "", reverse=True)
    return out


# --------------------------------------------------------------------------- derived

def derive(p: dict, today: dt.date) -> dict:
    plan = p["plan"]
    total = len(plan)
    done = sum(1 for m in plan if m["status"] == "done")
    slipping = [m for m in plan if m["overdue"]]

    p["milestones_total"] = total
    p["milestones_done"] = done
    p["adherence"] = round(100 * done / total) if total else 0
    p["current_milestone"] = next(
        (m["title"] for m in plan if m["status"] == "in_progress"),
        next((m["title"] for m in plan if m["status"] != "done"), None),
    )
    p["slipping"] = [
        {"id": m["id"], "title": m["title"], "due": m["due"],
         "days_overdue": m["days_overdue"], "status": m["status"]}
        for m in sorted(slipping, key=lambda m: -m["days_overdue"])
    ]

    target = p["target"]
    p["days_to_target"] = days_between(target, today) if target else None
    p["target_overdue"] = bool(target and target < today and p["status"] != "done")

    updated = p["updated"]
    p["days_since_update"] = days_between(today, updated) if updated else None
    p["stale"] = bool(updated and p["days_since_update"] > STALE_AFTER_DAYS
                      and p["status"] != "done")

    p["is_active"] = p["status"] not in ("done", "paused")
    p["needs_attention"] = bool(p["blocked_on_me"] or p["slipping"] or p["stale"]
                                or p["target_overdue"])

    # Serialise dates for JSON.
    for key in ("started", "target", "updated"):
        if p[key]:
            p[key] = p[key].isoformat()
    return p


def rollup(projects: list[dict], today: dt.date) -> dict:
    active = [p for p in projects if p["is_active"]]
    return {
        "generated": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "today": today.isoformat(),
        "stale_after_days": STALE_AFTER_DAYS,
        "counts": {
            "projects": len(projects),
            "active": len(active),
            "blocked_on_me": sum(len(p["blocked_on_me"]) for p in projects),
            "slipping": sum(len(p["slipping"]) for p in projects),
            "waiting_on": sum(len(p["waiting_on"]) for p in projects),
            "risks_high": sum(1 for p in projects for r in p["risks"]
                              if r["severity"] == "high"),
            "stale": sum(1 for p in projects if p["stale"]),
        },
    }


# ------------------------------------------------------------------------------ main

def resolve_today() -> dt.date:
    override = os.environ.get("DASHBOARD_TODAY")
    if override:
        return dt.date.fromisoformat(override)
    return dt.datetime.now(dt.timezone.utc).date()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate without writing")
    args = ap.parse_args()

    today = resolve_today()
    errs = Errors()

    paths = sorted(p for p in PROJECTS_DIR.glob("*.y*ml") if not p.name.startswith("_"))
    if not paths:
        print("build: no project files in projects/ — copy projects/_TEMPLATE.yml to "
              "projects/<id>.yml to add one", file=sys.stderr)
        return 1

    projects = [p for p in (load_project(path, today, errs) for path in paths) if p]

    ids = [p["id"] for p in projects]
    for dupe in {i for i in ids if ids.count(i) > 1 and i}:
        errs.add("projects/", f"duplicate project id '{dupe}'")

    if errs:
        print(f"build: {len(errs.items)} validation error(s)\n", file=sys.stderr)
        for item in errs.items:
            print(f"  {item}", file=sys.stderr)
        print("\nNothing written. Field reference: schema/project.schema.md",
              file=sys.stderr)
        return 1

    projects.sort(key=lambda p: (STATUS_RANK.get(p["status"], 9),
                                 p["days_to_target"] if p["days_to_target"] is not None
                                 else 10**6,
                                 p["codename"].lower()))

    data = {"meta": rollup(projects, today), "projects": projects}

    if args.check:
        print(f"build: {len(projects)} project(s) valid")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    c = data["meta"]["counts"]
    print(f"build: wrote {OUT.relative_to(ROOT)} — {c['projects']} project(s), "
          f"{c['blocked_on_me']} blocked on you, {c['slipping']} slipping, "
          f"{c['waiting_on']} waiting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
