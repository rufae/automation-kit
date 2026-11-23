"""Tests del importador de workflows (resolución de marcadores)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.n8n_import_flows import _resolve_markers


def _workflow_with_ref(value: str) -> dict:
    return {
        "name": "padre",
        "nodes": [
            {
                "name": "Llamar sub",
                "type": "n8n-nodes-base.executeWorkflow",
                "parameters": {"workflowId": {"value": value}},
            }
        ],
    }


class TestResolveMarkers:
    def test_resolves_known_sub(self):
        workflow = _workflow_with_ref("__SUB__:Rafita · Sub")
        _resolve_markers(workflow, {"Rafita · Sub": "abc123"})
        assert workflow["nodes"][0]["parameters"]["workflowId"]["value"] == "abc123"

    def test_unknown_sub_raises(self):
        workflow = _workflow_with_ref("__SUB__:No existe")
        with pytest.raises(RuntimeError):
            _resolve_markers(workflow, {})

    def test_plain_ids_untouched(self):
        workflow = _workflow_with_ref("id-normal")
        _resolve_markers(workflow, {})
        assert workflow["nodes"][0]["parameters"]["workflowId"]["value"] == "id-normal"


class TestFolder:
    def test_workflows_parse_as_json(self):
        folder = Path(__file__).resolve().parents[1] / "workflows"
        for path in folder.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data.get("name"), f"{path.name} sin nombre"
            assert data.get("nodes"), f"{path.name} sin nodos"
