"""Pure-function unit tests for sample_order/cli.py rendering helpers.

Per docs/tasks/2026-07-15_console_ui_integration_plan.md section 6 item 6,
the interactive menu loop is verified manually (not automated here). This
file only covers the pure helpers: the status-badge color mapping and the
_paginate boundary behavior.
"""

from sample_order import cli


def test_badge_includes_status_label_for_every_known_status():
    # Even without color rendering, the raw status text must always be
    # present so meaning survives on non-ANSI terminals (SPEC.md 11).
    for status in ("RESERVED", "CONFIRMED", "PRODUCING", "RELEASE", "REJECTED"):
        badge = cli._badge(status)
        assert status in badge


def test_badge_color_mapping_matches_plan_5_4():
    assert "yellow" in cli._badge("RESERVED")
    assert "cyan" in cli._badge("CONFIRMED")
    assert "magenta" in cli._badge("PRODUCING")
    assert "green" in cli._badge("RELEASE")
    assert "red" in cli._badge("REJECTED")


def test_paginate_exact_page_size_has_no_next_page_hint():
    items = list(range(10))
    page, has_more, remaining = cli._paginate(items, page=1, page_size=10)
    assert page == items
    assert has_more is False
    assert remaining == 0


def test_paginate_one_over_page_size_shows_hint_with_remaining_count():
    items = list(range(11))
    page, has_more, remaining = cli._paginate(items, page=1, page_size=10)
    assert page == items[:10]
    assert has_more is True
    assert remaining == 1


def test_paginate_second_page_shows_the_remainder():
    items = list(range(11))
    page, has_more, remaining = cli._paginate(items, page=2, page_size=10)
    assert page == items[10:]
    assert has_more is False
    assert remaining == 0
