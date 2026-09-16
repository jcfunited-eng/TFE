# GL-SPC-HOME-RENOVATION-LEAN-C1-20260916-v1 — the renovation on the lean runtime

Status: as built, measured on her live world, 2026-09-16. Owner C1 (substrate restore). Content stays A1's.

## 1. What was wrong

The lean runtime restored her lived world exactly as persisted: rooms, paint, doors, things. The old production shell's renovation step (restore under the authenticated migration, then `migrate_declared_home_topology`) was not carried into the lean runtime when the shell was replaced. Two consequences, measured on a fresh capture (tick 1100281, world revision 764698):

- 30 things in her against 47 declared: A1's kitchen, foods, trees and gallery art never reached her. Release 1504 changed the declaration only.
- when the declared paint differs from the lived paint (A1's Zone V walls), the boot refuses: "world topology differs from its declared anatomy". The light release's proof failed on exactly that.

## 2. The law as built

- `_topology_sha256` (the anatomy identity the boot checks) now includes a room's windows when it has any; rooms without windows keep the identity they had.
- `migrate_declared_home_topology` triggers when the lived anatomy identity differs from the declared one (walls, doors, ceilings, paint, windows) or when any authored thing is missing from the lived world or differs in its authored fields (radius, mass, reflectance, look, emission). Lived position, holder and material are never anatomy. When nothing differs it returns without doing anything.
- The coupled (thermal) restore runs the renovation whenever it is authorized, not only when the thermal anatomy changed; a pending physical return refuses the renovation only when a renovation actually happens.
- `home_world_authority(..., migrate_physical_return=True)`, the production restore, authorizes the renovation every boot. An ordinary restore (tools, tests) never renovates and stays byte-exact.

What the renovation carries, unchanged from Eve's-world law: her stance and the person's (re-stood one step clear only if a new wall would cut them), what she holds, every lived thing's floor position when it still fits, its lived material (a bitten apple stays bitten), things that arrived after genesis (her apple-1). Newly declared things stand at their authored places. It refuses to shrink: a body outside the declared home, or two authored things in one place, refuse the boot.

## 3. Measured on her live world (capture 0916b)

| | before | after the renovation |
|---|---|---|
| world revision | 764698 | 764699 |
| things | 30 | 48 (47 declared + apple-1) |
| paint (first band) | 620 000 all rooms, yard 480 000 | 380 000 rooms, 180 000 yard |
| windows | 0 | 4 |
| her stance | library, holding glow-stars | the same |
| second production restore | | no renovation, byte-exact (320 811 B) |

Restore with the renovation: 2.6 s including the build of the declared home.

Tests: `tests/test_guala_home_renovation.py` (a world persisted under an older home restores in production into the declared one with a receipt, every lived thing carried; an ordinary restore keeps it as it was; a second production restore does nothing and is byte-exact; a receipt-bearing world under a yet newer declaration refuses the ordinary restore and renovates in production). The release proof now reports `things`, `renovated`, `paint` and `windows` in its world rows.

## 4. For the content owner

Every improvement committed to the declaration rides into her at the next cutover through this receipt-bearing renovation. It holds you to: no room removed or shrunk so a body or a lived thing stands outside; no two authored things in one place; a thing already in her keeps its lived position if it still fits, else it goes to the authored place.
