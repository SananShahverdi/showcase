def score_recipe(success_count: int, failure_count: int) -> float:
    """Scores recipe versions by extraction success rate."""
    total = success_count + failure_count
    if total == 0:
        return 0.0
    return success_count / total
