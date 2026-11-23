"""Valida cualquier carpeta de workflows de n8n contra las convenciones D14.

Estos tests son el "lint de workflows": corren en CI y rompen el build si un
flujo incumple reintentos, timeouts, fallo controlado, marcadores `__SUB__:`
o errorWorkflow. Funcionan sobre `workflows/*.json` del repo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
DIR = RAIZ / "workflows"
MARCADOR = "__SUB__:"


def _workflows() -> list[tuple[str, dict]]:
    return [
        (f.name, json.loads(f.read_text(encoding="utf-8")))
        for f in sorted(DIR.glob("*.json"))
    ]


def _padres() -> list[tuple[str, dict]]:
    return [(n, w) for n, w in _workflows() if not n.startswith("90-")]


def _http(workflow: dict) -> list[dict]:
    return [n for n in workflow["nodes"] if n["type"].endswith("httpRequest")]


def _execute(workflow: dict) -> list[dict]:
    return [
        n for n in workflow["nodes"] if n["type"] == "n8n-nodes-base.executeWorkflow"
    ]


@pytest.fixture(scope="module")
def workflows() -> list[tuple[str, dict]]:
    data = _workflows()
    if not data:
        pytest.skip("sin workflows en workflows/")
    return data


class TestReintentosYTimeouts:
    def test_http_reintenta_con_backoff(self, workflows):
        for name, workflow in workflows:
            for node in _http(workflow):
                assert node.get("retryOnFail") is True, (
                    f"{name}/{node['name']} sin retry"
                )
                assert int(node.get("maxTries", 0)) >= 3, (
                    f"{name}/{node['name']} <3 intentos"
                )
                assert int(node.get("waitBetweenTries", 0)) >= 1000, (
                    f"{name}/{node['name']} sin backoff"
                )

    def test_http_tiene_timeout(self, workflows):
        for name, workflow in workflows:
            for node in _http(workflow):
                options = (node.get("parameters") or {}).get("options") or {}
                assert options.get("timeout"), f"{name}/{node['name']} sin timeout"

    def test_execute_reintenta(self, workflows):
        for name, workflow in workflows:
            for node in _execute(workflow):
                assert node.get("retryOnFail") is True, (
                    f"{name}/{node['name']} sin retry"
                )
                assert int(node.get("maxTries", 0)) >= 3
                assert int(node.get("waitBetweenTries", 0)) >= 1000


class TestFalloControlado:
    def test_llamadas_a_telegram_degradan(self, workflows):
        for name, workflow in workflows:
            for node in _http(workflow):
                url = str((node.get("parameters") or {}).get("url", ""))
                if "telegram.org" in url:
                    assert node.get("onError") == "continueRegularOutput", (
                        f"{name}/{node['name']}"
                    )


class TestSubWorkflows:
    def test_padres_usan_marcadores_y_error_workflow(self):
        subs_conocidos = {
            json.loads(f.read_text(encoding="utf-8"))["name"]
            for f in DIR.glob("90-*.json")
        }
        for name, workflow in _padres():
            settings = workflow.get("settings", {})
            error_workflow = str(settings.get("errorWorkflow", ""))
            if not error_workflow.startswith(MARCADOR):
                pytest.fail(
                    f"{name} sin settings.errorWorkflow → {MARCADOR}<sub de errores>"
                )
            for node in _execute(workflow):
                ref = (
                    (node.get("parameters") or {})
                    .get("workflowId", {})
                    .get("value", "")
                )
                assert ref.startswith(MARCADOR), f"{name}/{node['name']} sin marcador"
                assert ref[len(MARCADOR) :] in subs_conocidos, (
                    f"{name}/{node['name']} → sub desconocido {ref}"
                )

    def test_create_hmac_solo_en_subs(self, workflows):
        for name, workflow in workflows:
            for node in workflow["nodes"]:
                code = str((node.get("parameters") or {}).get("jsCode", ""))
                if "createHmac" in code:
                    assert name.startswith("90-"), (
                        f"{name}/{node['name']}: HMAC fuera de un sub"
                    )
