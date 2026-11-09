"""Red team reports — stored as timestamped files in the project's
reports/ folder (written by langgraph/scripts/redteam.py after each run)
and surfaced in the security interface.

Visibility (changed 2026-11 at the owner's request): SYSTEM_ADMIN now sees
the red team reports alongside SECURITY_AUDITOR and PLATFORM_SUPER_ADMIN.
Read-only: the folder never accepts writes from the API."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status

from ..auth import AuthUser, require_roles

router = APIRouter(prefix="/api/security", tags=["security"])

REPORTS_DIR = Path(__file__).resolve().parents[3] / "reports"
ALLOWED_SUFFIXES = (".json", ".md")


def _latest_run() -> dict | None:
    """Dernière exécution depuis public.redteam_runs / redteam_case_results."""
    try:
        from .. import db

        run = db.fetch_one(
            "select id, run_at, total_cases, failures, verdict"
            " from public.redteam_runs order by run_at desc limit 1"
        )
        if not run:
            return None
        cases = db.fetch_all(
            "select category, case_name, decision, expected, status, layer2"
            " from public.redteam_case_results where run_id = %s"
            " order by created_at asc",
            (run["id"],),
        )
        return {
            "run_at": str(run["run_at"]),
            "total_cases": run["total_cases"],
            "failures": run["failures"],
            "verdict": run["verdict"],
            "cases": [
                {"category": c["category"], "case": c["case_name"],
                 "decision": c["decision"], "expected": c["expected"],
                 "status": c["status"], "layer2": c.get("layer2") or "-"}
                for c in cases
            ],
        }
    except Exception:  # noqa: BLE001 — repli sur les fichiers
        return None


@router.get("/redteam-reports")
def redteam_reports(user: AuthUser = Depends(require_roles(
        "SECURITY_AUDITOR", "SYSTEM_ADMIN", "PLATFORM_SUPER_ADMIN"))) -> dict:
    entries: list[dict] = []
    if REPORTS_DIR.is_dir():
        for path in sorted(REPORTS_DIR.iterdir(), reverse=True):
            if path.suffix not in ALLOWED_SUFFIXES or not path.is_file():
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                continue
            entry: dict = {"filename": path.name, "kind": path.suffix.lstrip("."),
                           "content": content[:20000]}
            if path.suffix == ".json":
                try:
                    parsed = json.loads(content)
                    entry["verdict"] = parsed.get("verdict")
                    entry["generated_at"] = parsed.get("generated_at")
                    entry["failures"] = parsed.get("failures")
                    entry["total"] = parsed.get("total")
                    entry["cases"] = parsed.get("cases", [])
                except ValueError:
                    pass
            entries.append(entry)
    return {"latest_run": _latest_run(), "reports": entries}
