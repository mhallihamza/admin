# =====================================================================
# CLI : pipeline de réponse complet (flows 01 → 06 → 07 → 09) pour une
# question + le token utilisateur (les spécialistes rappellent la
# passerelle backend). Hors ligne (sans MISTRAL_API_KEY) le mode
# heuristique répond avec les données officielles brutes, sans inventer.
# Usage :
#   python scripts/run_pipeline.py "Comment obtenir un certificat ?" \
#       --gateway http://localhost:8100 --token <bearer-token>
# =====================================================================
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from guide_graph.config import BACKEND_GATEWAY_URL  # noqa: E402
from guide_graph.graph import run_chat  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Guide Administratif — pipeline chat")
    parser.add_argument("question")
    parser.add_argument("--gateway", default=BACKEND_GATEWAY_URL)
    parser.add_argument("--token", default="")
    parser.add_argument("--language", default="fr")
    parser.add_argument("--user-id", default="cli-user")
    args = parser.parse_args()

    payload = {
        "text": args.question,
        "user_id": args.user_id,
        "roles": ["CITIZEN"],
        "request_type": "chat",
        "disabled": False,
        "filename": None,
        "source_user_id": None,
        "agent": None,
        "tool": None,
        "agent_tool_allowed": None,
    }
    session = {
        "question": args.question,
        "language": args.language,
        "user_token": args.token,
        "gateway_base_url": args.gateway,
        "conversation_id": f"cli-{uuid.uuid4().hex[:8]}",
        "question_summary": args.question,
    }

    result = run_chat(payload, session)
    ready = [k for k in ("gate_decision", "specialist") if result.get(k)]
    print(json.dumps({
        "gate_decision": result.get("gate_decision"),
        "gate_reason": result.get("gate_reason"),
        "specialist": result.get("specialist"),
        "answer": result.get("answer"),
        "citations": result.get("citations"),
        "validation": result.get("validation"),
        "incident": result.get("incident"),
        "request_id": result.get("request_id"),
    }, indent=2, ensure_ascii=False))
    if result.get("answer") is None:
        print("\n(réponse retenue — voir gate_reason; prête: " + ", ".join(ready) + ")",
              file=sys.stderr)


if __name__ == "__main__":
    main()
