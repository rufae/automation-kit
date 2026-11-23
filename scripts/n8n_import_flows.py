#!/usr/bin/env python3
"""Importa workflows de una carpeta a n8n resolviendo marcadores `__SUB__:`.

Uso:
    N8N_URL=http://localhost:5678 N8N_API_KEY=xxx \
        python scripts/n8n_import_flows.py workflows/

- Publica primero los `90-sub-*.json` (n8n rechaza padres sin sub).
- Sustituye `{"value": "__SUB__:<nombre>"}` por el id real del sub importado.
- Crea el workflow si no existe; si existe, lo actualiza (PUT).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

MARCADOR = "__SUB__:"


def _api(method: str, path: str, body: dict | None = None, *, base: str, key: str):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        f"{base}/api/v1{path}",
        data=data,
        method=method,
        headers={"X-N8N-API-KEY": key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"{method} {path} → HTTP {exc.code}: {exc.read()[:200]}"
        ) from exc


def _resolve_markers(workflow: dict, sub_ids: dict[str, str]) -> None:
    for node in workflow.get("nodes", []):
        workflow_id = (node.get("parameters") or {}).get("workflowId")
        value = workflow_id.get("value", "") if isinstance(workflow_id, dict) else ""
        if value.startswith(MARCADOR):
            name = value[len(MARCADOR) :]
            if name not in sub_ids:
                raise RuntimeError(f"sub no importado: {name}")
            workflow_id["value"] = sub_ids[name]


def import_flows(folder: str | Path, *, base: str, key: str) -> dict[str, str]:
    folder = Path(folder)
    files = sorted(folder.glob("*.json"))
    subs = [f for f in files if f.name.startswith("90-")]
    parents = [f for f in files if not f.name.startswith("90-")]

    sub_ids: dict[str, str] = {}
    for path in subs + parents:
        workflow = json.loads(path.read_text(encoding="utf-8"))
        _resolve_markers(workflow, sub_ids)
        payload = {
            k: workflow[k]
            for k in ("name", "nodes", "connections", "settings", "pinData")
            if k in workflow
        }
        existing = None
        if workflow.get("id"):
            try:
                existing = _api(
                    "GET", f"/workflows/{workflow['id']}", base=base, key=key
                )
            except RuntimeError:
                existing = None
        if existing:
            result = _api(
                "PUT", f"/workflows/{workflow['id']}", payload, base=base, key=key
            )
        else:
            result = _api("POST", "/workflows", payload, base=base, key=key)
        sub_ids[workflow["name"]] = result["id"]
        print(f"  ✓ {path.name} → {result['id']}")
    return sub_ids


def main() -> int:
    folder = sys.argv[1] if len(sys.argv) > 1 else "workflows"
    base = os.environ.get("N8N_URL", "http://localhost:5678").rstrip("/")
    key = os.environ.get("N8N_API_KEY", "")
    if not key:
        print("N8N_API_KEY es obligatoria")
        return 1
    import_flows(folder, base=base, key=key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
