import pandas as pd

from app import storage


def frame(codes):
    return pd.DataFrame([
        {
            "code": code,
            "name": f"股票{code}",
            "price": 10.0,
            "pct_change": 2.0,
            "turnover_rate": 15.0,
            "net_inflow_cny": 150_000_000.0,
            "net_profit_yoy": 40.0,
            "revenue_yoy": 35.0,
        }
        for code in codes
    ])


def test_record_scan_tracks_enter_and_exit(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "screener.db")
    storage.init_db()

    first = storage.record_scan(frame(["000001"]))
    assert first["entered"] == ["000001"]
    assert first["exited"] == []
    assert len(storage.get_active_matches()) == 1

    second = storage.record_scan(frame([]))
    assert second["entered"] == []
    assert second["exited"] == ["000001"]
    assert storage.get_active_matches() == []

    events = storage.get_events()
    assert [event["event_type"] for event in events] == ["EXIT", "ENTER"]
