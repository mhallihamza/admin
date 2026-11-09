# =====================================================================
# CLI : exécute le Central Security Gate (flow 01) sur un payload
# fourni en JSON argument (ou un exemple citoyen sans argument).
# Usage :
#   python scripts/run_gate.py
#   python scripts/run_gate.py "{\"text\": \"hi\", \"user_id\": \"u-1\",
#        \"roles\": [\"VISITOR\"], \"request_type\": \"chat\"}"
# =====================================================================
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from guide_graph.nodes.gate import run_gate  # noqa: E402


def main() -> None:
    if len(sys.argv) > 1:
        raw = sys.argv[1]
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
    else:
        payload = {
            "text": "Comment renouveler ma carte d'identité ?",
            "user_id": "u-exemple",
            "roles": ["CITIZEN"],
            "request_type": "chat",
            "disabled": False,
            "filename": None,
            "source_user_id": None,
            "agent": None,
            "tool": None,
            "agent_tool_allowed": None,
        }

    result = run_gate(payload)
    print(json.dumps({
        "gate_decision": result.get("gate_decision"),
        "gate_reason": result.get("gate_reason"),
        "layer1_violations": result.get("layer1_violations", []),
        "layer2": {
            "connected": result.get("layer2_connected", False),
            "risk_level": result.get("layer2_risk", "LOW"),
            "attack_type": result.get("layer2_attack_type"),
            "confidence": result.get("layer2_confidence", 0.0),
            "reason": result.get("layer2_reason", ""),
        },
        "incident": result.get("incident"),
        "logged": result.get("logged"),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
