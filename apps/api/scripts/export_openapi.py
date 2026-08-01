import argparse
import json
from pathlib import Path

from app.main import create_app

OPENAPI_PATH = Path(__file__).resolve().parents[1] / "openapi.json"


def render_openapi() -> str:
    """Return a deterministic, reviewable OpenAPI representation."""

    return json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the FastAPI OpenAPI contract.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when the checked-in OpenAPI document is missing or stale.",
    )
    arguments = parser.parse_args()
    rendered = render_openapi()

    if arguments.check:
        if (
            not OPENAPI_PATH.exists()
            or OPENAPI_PATH.read_text(encoding="utf-8") != rendered
        ):
            print("openapi.json is stale; run: uv run python scripts/export_openapi.py")
            return 1
        print("openapi.json matches the FastAPI application.")
        return 0

    OPENAPI_PATH.write_text(rendered, encoding="utf-8")
    print(f"Exported {OPENAPI_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
