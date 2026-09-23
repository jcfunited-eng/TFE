import subprocess
from pathlib import Path


def test_refresh_failure_does_not_launch_readers_or_trading_engines():
    root = Path(__file__).resolve().parents[1]
    script = '''
source tools/ch4_spring_daily_runner.sh
python() { printf 'CALL:%s\\n' "$1"; return 23; }
nohup() { echo 'UNEXPECTED CHILD'; return 99; }
run_close_pass
'''
    result = subprocess.run(['bash', '-c', script], cwd=root, capture_output=True, text=True)
    assert result.returncode == 23
    assert result.stdout.splitlines() == ['CALL:tools/ch4_store_refresh.py']


def test_later_failure_stops_only_after_successful_dependencies():
    root = Path(__file__).resolve().parents[1]
    script = '''
source tools/ch4_spring_daily_runner.sh
python() {
  printf 'CALL:%s\\n' "$1"
  if [[ "$1" = 'tools/population_reading_backfill.py' ]]; then return 17; fi
  return 0
}
nohup() { echo 'UNEXPECTED CHILD'; return 99; }
run_close_pass
'''
    result = subprocess.run(['bash', '-c', script], cwd=root, capture_output=True, text=True)
    assert result.returncode == 17
    assert result.stdout.splitlines() == [
        'CALL:tools/ch4_store_refresh.py', 'CALL:tools/ch3_supply_tail.py',
        'CALL:tools/population_reading_backfill.py']
