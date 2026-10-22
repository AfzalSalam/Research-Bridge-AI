"""Score a local labelled export without sending it to an external provider."""

import argparse
import json
from pathlib import Path

from app.documents.evaluation import EvaluationDataset, evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    dataset = EvaluationDataset.model_validate_json(
        args.dataset.read_text(encoding="utf-8")
    )
    print(json.dumps(evaluate(dataset), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
