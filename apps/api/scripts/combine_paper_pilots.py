"""Combine saved public-pilot outputs without rerunning retrieval or calling AI."""

import argparse
import json
from pathlib import Path

from app.documents.evaluation import EvaluationDataset, combine_datasets, evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", type=Path, nargs="+")
    parser.add_argument("--name", default="public-paper-pilot-combined")
    args = parser.parse_args()
    datasets = [
        EvaluationDataset.model_validate(
            json.loads(path.read_text(encoding="utf-8"))["dataset"]
        )
        for path in args.inputs
    ]
    combined = combine_datasets(args.name, datasets)
    print(
        json.dumps(
            {
                "dataset": combined.model_dump(),
                "report": evaluate(combined),
                "sources": [path.name for path in args.inputs],
                "limitations": "Aggregation does not validate relevance labels or make "
                "a small pilot representative. Timing reflects the original runs.",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
