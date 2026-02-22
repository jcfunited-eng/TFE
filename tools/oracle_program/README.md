# Oracle Optimizer Program

This is the persistent program controller for the offline MoM+IRF optimizer.

It stores resumable state in the repository so progress survives chat/session changes.

## Persistent Paths

- Program root: `backups/runtime/oracle_program`
- Latest heartbeat: `backups/runtime/oracle_program/last_heartbeat.json`
- Session summaries: `backups/runtime/oracle_program/sessions/*.json`
- Session logs: `backups/runtime/oracle_program/sessions/*.log`
- Snapshot copy of optimizer state: `backups/runtime/oracle_program/mom_irf_state_snapshot`
- Program manifest: `backups/runtime/oracle_program/program_manifest.json`

## Commands

Run status:

```bash
python3 tools/oracle_program/oracle_program.py status
```

Run a short bounded cycle (example: 25 runs):

```bash
python3 tools/oracle_program/oracle_program.py short-cycle --runs 25
```

## Notes

- The controller runs `g32_mom_irf_loop_runner.py` against `/tmp/g32_mom_irf_loop`.
- It writes/uses `/tmp/g32_mom_irf_loop/STOP` to stop at a run boundary.
- It snapshots current `/tmp/g32_mom_irf_loop` back into repository storage at cycle end.
