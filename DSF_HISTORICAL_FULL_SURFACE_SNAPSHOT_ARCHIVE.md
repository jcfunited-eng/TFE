# DSF Historical Full-Surface Snapshot Archive

This lane exists because the repo did not contain a historical series of fixed snapshots that all carried the frozen primitive surface:

- `S_UF`
- `R_UF`
- `D_k`
- `M_k`
- `R_rev_k`
- `U_star_k`
- `C_k`
- `P_k`
- `B_k`
- `bar_count`

Direct build path:

1. archived `backups/**/uf_snapshot.json` supplies the historical universe membership for each archived snapshot timestamp
2. archived `uf_snapshot_rebuild_report.json` supplies the exact snapshot timestamp
3. adjusted daily bars are fetched only up to that timestamp
4. `compute_structural_state(symbol, bars)` rebuilds the full primitive surface as of that historical date
5. rebuilt rows are stored in a local SQLite archive

Important honesty:

- this is a local database-centered archive because the historical Postgres lane does not exist in this environment
- older archived snapshots may be partial-surface only; they are used for universe membership and timestamp only, not as decision authority
- the frozen primitive is not changed by this lane
