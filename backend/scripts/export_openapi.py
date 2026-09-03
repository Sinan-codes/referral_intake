"""Writes the API's OpenAPI schema to `backend/openapi.json`.

`app.openapi()` only introspects the route/Pydantic definitions already on
`app` -- it doesn't run the lifespan, so this never touches the database.
The frontend's `openapi-typescript` points at the file this writes to
generate its request/response types, rather than the two sides maintaining
hand-written copies of the same shapes.

Run after changing anything in app/models/api.py or app/routers (as a
module, from backend/, so `app` resolves on sys.path the same way it does
under pytest):

    uv run python -m scripts.export_openapi
"""

from __future__ import annotations

import json
from pathlib import Path

from app.main import app

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "openapi.json"


def main() -> None:
    schema = app.openapi()
    OUTPUT_PATH.write_text(json.dumps(schema, indent=2) + "\n")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
