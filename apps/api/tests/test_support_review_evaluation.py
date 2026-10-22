from scripts.evaluate_support_review import score


def test_unavailable_is_not_credited_as_correct_rejection():
    rows = [
        {"verdict": "unavailable", "expected_supported": False},
        {"verdict": "supported", "expected_supported": False},
        {"verdict": "unsupported", "expected_supported": False},
        {"verdict": "supported", "expected_supported": True},
    ]
    assert score(rows) == {
        "attempted": 4,
        "unavailable": 1,
        "correct": 2,
        "false_support": 1,
        "uncertain": 0,
    }
