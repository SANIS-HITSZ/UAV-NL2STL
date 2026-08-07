# STL grammar used in UAV-NL2STL

The dataset uses a compact ASCII serialization of bounded Signal Temporal Logic.

| Construct | Meaning | Example |
| --- | --- | --- |
| `F[a:b](p)` | `p` eventually holds between `a` and `b` | `F[0:80](red mailbox)` |
| `G[a:b](p)` | `p` always holds between `a` and `b` | `G[0:80](~blue sofa)` |
| `p U[a:b] q` | `p` holds until `q` occurs in the interval | `(~goal)U[0:80](waypoint)` |
| `~p` | negation | `~blue sofa` |
| `p&q` | conjunction | `F[0:80](p)&F[0:80](q)` |
| `p|q` | disjunction | `F[0:80](p)|F[0:80](q)` |

Intervals are closed, integer-valued, and written with a colon, for example `[0:80]`.
Atomic propositions are natural-language object or landmark names and may contain spaces and hyphens.

This serialization is dataset-specific. Consumers that require conventional comma-separated intervals or Unicode Boolean operators should convert the syntax explicitly rather than silently changing labels.
