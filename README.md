# automation-kit — workflows de n8n listos para producción

[![CI](https://github.com/rufae/automation-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/rufae/automation-kit/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-10-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Kit de **convenciones + validadores + plantillas** para automatizaciones n8n
en producción: reintentos con backoff, timeouts, fallo controlado, sub-
workflows reutilizables y errores siempre visibles. Las reglas no son letra
muerta: **un test las verifica** y rompe el build en CI si un workflow las
incumple.

> Extraído de la plataforma de automatización que opero en producción
> (17 workflows: briefing diario, inbox zero, radar de IA, CRM…), donde estos
> patrones eliminaron los fallos silenciosos y los flujos colgados.

## Las 7 reglas (resumen)

| Regla | Por qué |
|---|---|
| Reintentos `retryOnFail` 3× con backoff en todo HTTP y Execute Workflow | un 503 transitorio no tumba un flujo de 20 min |
| `options.timeout` en cada HTTP | nada queda zombi |
| `onError: continueRegularOutput` hacia servicios ajenos | degrada en vez de reventar |
| Subs por marcador `__SUB__:<nombre>` | lógica compartida sin duplicar; el importador los publica primero |
| Un único punto por responsabilidad | el envío a Telegram vive solo en el sub de Telegram |
| `settings.errorWorkflow` → sub de errores | ningún fallo en silencio |
| Informe de ejecución (opcional) | «¿qué ha fallado esta semana?» sin mirar consolas |

Desarrolla con detalle en [`conventions/D14.md`](conventions/D14.md).

## Qué incluye

```
workflows/                 # plantillas importables
├── 90-sub-telegram.json   # el ÚNICO punto que habla con Telegram
├── 90-sub-errores.json    # errorWorkflow: avisa de las caídas duras
└── 00-plantilla-aviso.json# padre tipo: webhook → payload → sub
scripts/n8n_import_flows.py # importador que resuelve __SUB__ y publica subs primero
tests/                     # los validadores de convenciones (el "lint")
```

## Uso

1. **Importa las plantillas** (crea una API key en n8n → Settings → API):

```bash
N8N_URL=http://localhost:5678 N8N_API_KEY=xxx \
  python scripts/n8n_import_flows.py workflows/
```

2. **Valida tus propios workflows** en CI: copia `tests/` a tu repo (o instala
   el paquete) y apúntalo a tu carpeta de workflows — cualquier flujo sin
   reintentos, timeout o errorWorkflow rompe el build.

```bash
pytest -q
```

## Desarrollo

```bash
pip install -e ".[dev]"
pytest -q && ruff check .
```

## Licencia

[MIT](LICENSE)
