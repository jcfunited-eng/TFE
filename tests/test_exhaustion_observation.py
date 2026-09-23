from datetime import datetime
import pytest
from tools.measure_exhaustion_telemetry import FIELDS, fetch_history, measure


def row(day, d=1, m=0, label='Accumulate'):
    field = dict.fromkeys(FIELDS, 0)
    field.update(D_k=d, M_k=m)
    return {'symbol': 'X', 'observed_at': f'2026-09-{day:02}', 'field': field, 'label': label}


def test_equal_direction_does_not_hide_motion():
    report = measure([row(1), row(2, m=2)], 'publication')
    assert report['equal_D_with_other_field_changes'] == 1
    assert report['adjacent_pairs'][0]['changed_fields'] == ['M_k']
    assert report['bar_continuity_verified'] is False
    assert 'tau_in' not in report


def test_invalid_observation_breaks_both_adjacent_comparisons():
    middle = row(2)
    middle['field']['D_k'] = None
    report = measure([row(1), middle, row(3)], 'publication')
    assert report['observation_count'] == 3
    assert report['adjacent_pair_count'] == 2
    assert report['valid_pair_count'] == 0


def test_intervening_avoid_observation_is_retained():
    report = measure([row(1), row(2, d=-1, label='Avoid'), row(3)], 'publication')
    assert [p['delta_D_k'] for p in report['adjacent_pairs']] == [-2, 2]


def test_duplicate_publications_are_not_silently_counted_as_bars():
    with pytest.raises(ValueError, match='non-increasing'):
        measure([row(1), row(1)], 'publication')


def test_database_query_does_not_filter_historical_labels():
    class Cursor:
        def execute(self, sql, params):
            assert params == (30,)
            historical_part = sql.split(')')[1]
            assert 'decision_label' not in historical_part
            assert "WHERE decision_label = 'Accumulate'" in sql
        def __iter__(self):
            for day, label in [(1, 'Accumulate'), (2, 'Avoid'), (3, 'Accumulate')]:
                yield ('X', datetime(2026, 9, day), label, row(day)['field'])
    result = fetch_history(Cursor(), 30)
    assert [r['label'] for r in result] == ['Accumulate', 'Avoid', 'Accumulate']


@pytest.mark.parametrize('bad', [True, '1', float('nan'), float('inf')])
def test_invalid_field_values_are_reported_without_coercion(bad):
    second = row(2)
    second['field']['M_k'] = bad
    report = measure([row(1), second], 'publication')
    assert report['valid_pair_count'] == 0
    assert report['adjacent_pairs'][0]['invalid_after'] == ['M_k']
