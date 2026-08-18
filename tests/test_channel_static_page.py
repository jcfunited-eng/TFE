from pathlib import Path

from tools import channel_static_page
from tools.channel_static_page import ChannelPage, ClosedRow, OpenRow
from tools.ch3_shadow_page import recorded_shares


def page(*, opens: tuple[OpenRow, ...], closed: tuple[ClosedRow, ...] = ()) -> ChannelPage:
    return ChannelPage(
        code="CH3",
        title="CH3 test",
        engine="test",
        starting_capital=100_000,
        cash=90_000,
        opens=opens,
        closed=closed,
        rules=("Missing herd evidence is refused.",),
    )


def test_missing_mark_never_becomes_flat_position(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(channel_static_page, "live_marks", lambda symbols: {})
    monkeypatch.setattr(channel_static_page, "latest_completed_closes", lambda: {})
    destination = tmp_path / "ch3.html"
    channel_static_page.render_page(
        page(
            opens=(
                OpenRow(
                    symbol="TEST",
                    side=-1,
                    shares=10,
                    entry_price=10,
                    notional=100,
                    entered_at="2026-08-18",
                ),
            )
        ),
        destination,
    )
    document = destination.read_text(encoding="utf-8")
    assert "UNAVAILABLE — INCOMPLETE MARKS" in document
    assert "NO MARK — EXCLUDED" in document
    assert "<td class='number'>—</td><td class='number'>—</td>" in document


def test_void_record_is_visible_but_not_counted_as_resolved_trade(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(channel_static_page, "live_marks", lambda symbols: {})
    monkeypatch.setattr(channel_static_page, "latest_completed_closes", lambda: {})
    destination = tmp_path / "ch3.html"
    channel_static_page.render_page(
        page(
            opens=(),
            closed=(
                ClosedRow("WIN", -1, 10, 10, 9, 10, 10, "2026-08-14", "2026-08-15", "HARVEST"),
                ClosedRow("VOID", -1, 10, 10, 10, 0, 0, "2026-08-14", "2026-08-15", "VOID-REFUTATION-REENTRY"),
            ),
        ),
        destination,
    )
    document = destination.read_text(encoding="utf-8")
    assert "VOID-REFUTATION-REENTRY" in document
    assert "100.0%" in document
    assert "0 / 1" in document


def test_legacy_ch3_share_count_comes_from_recorded_notional() -> None:
    assert recorded_shares({"entry_px": 25.0, "notional": 2_000.0}) == 80
    assert recorded_shares({"entry_px": 25.0, "notional": 2_000.0, "shares": 79}) == 79
