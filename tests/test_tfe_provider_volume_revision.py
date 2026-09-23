import datetime as dt

import pandas as pd

from tools.ch4_store_refresh import assemble


def test_provider_volume_revision_is_exact_and_does_not_delete_price_history():
    frame = pd.DataFrame({'Date': pd.to_datetime(['2026-09-17', '2026-09-18']),
                          'Symbol': ['SPY', 'SPY'], 'Close': [770., 773.5],
                          'Volume': [100, 50484511]})
    result, receipt = assemble(
        frame, {'SPY'}, [dt.date(2026, 9, 17), dt.date(2026, 9, 18)], 'test',
        fetch=lambda *_: [{'T': 'SPY', 'c': 773.5, 'v': 50484685.50995}])
    assert result.Close.tolist() == [770., 773.5]
    assert result.Volume.tolist() == [100., 50484685.50995]
    assert receipt['revised_overlap_rows'] == 1
    assert receipt['added_rows'] == 0
    assert frame.Volume.tolist() == [100, 50484511]
