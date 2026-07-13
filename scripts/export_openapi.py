from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_SOURCE = ROOT / "services" / "api" / "src"
OUTPUT = ROOT / "packages" / "contracts" / "openapi.json"

sys.path.insert(0, str(API_SOURCE))

from fable5_api.main import app  # noqa: E402


def rendered_schema() -> str:
    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export the canonical FastAPI OpenAPI schema.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the committed schema differs instead of rewriting it.",
    )
    args = parser.parse_args()
    expected = rendered_schema()

    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != expected:
            print("OpenAPI contract is stale. Run `npm run contracts:generate`.", file=sys.stderr)
            return 1
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(expected, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
