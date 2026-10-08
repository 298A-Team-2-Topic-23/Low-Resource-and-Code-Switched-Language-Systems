"""Check critical-path timing against hand-calculated dependency examples."""
from scripts.charts import timings


def test_parallel_branches_share_the_tightest_deadline():
    rows = timings([
        ("start", "Shared work", "A", 3, (), None),
        ("long", "Long branch", "B", 4, ("start",), None),
        ("short", "Short branch", "C", 2, ("start",), None),
        ("finish", "Deadline", "D", 0, ("long", "short"), 7),
    ])
    assert (rows["start"]["ES"], rows["start"]["LF"]) == (0, 3)
    assert rows["long"]["float"] == 0
    assert (rows["short"]["ES"], rows["short"]["LS"], rows["short"]["float"]) == (3, 5, 2)


def test_independent_terminal_deadlines_constrain_shared_work():
    rows = timings([
        ("shared", "Shared work", "A", 3, (), None),
        ("early", "Early delivery", "B", 2, ("shared",), 5),
        ("later", "Later delivery", "C", 1, ("shared",), 7),
    ])
    assert rows["shared"]["float"] == 0
    assert rows["early"]["float"] == 0
    assert rows["later"]["float"] == 3


def test_impossible_deadline_fails_instead_of_drawing_feasible_plan():
    import pytest

    with pytest.raises(ValueError, match="misses deadline"):
        timings([("late", "Too much work", "A", 4, (), 3)])
