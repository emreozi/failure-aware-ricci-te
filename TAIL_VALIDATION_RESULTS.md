# Held-out tail-risk validation result

Protocol: `TAIL_VALIDATION_PROTOCOL.md`

Ten new REPETITA topologies were frozen after `tail_robust` was designed and
before any outcome on this set was inspected.

## Primary comparison: tail-robust minus Ollivier--Ricci

- Worst-failure service-loss difference: **-2.246 percentage points**.
- Topology-cluster bootstrap 95% CI: **[-3.596, -0.871] pp**.
- Exact two-sided topology sign-flip p-value: **0.03125**.
- Direction: tail-robust better on 6, worse on 2, tied on 2 topologies.
- Mean service-loss difference: -0.103 pp, CI [-0.393, +0.171], p = 0.5078.
- Mean path-cost difference: -0.433%, CI [-1.951%, +0.941%], p = 0.6016.

Decision: reject the primary null at alpha = 0.05. Direct tail-risk
optimization reduces worst physical-link-failure loss relative to ORC without a
detected mean-loss or path-cost penalty on this held-out set.

## Secondary comparison: tail-robust minus minimum MLU

- Worst-failure service-loss difference: **-2.543 pp**.
- Bootstrap 95% CI: **[-3.661, -1.333] pp**.
- Exact sign-flip p = **0.0078125**.
- Direction: better on all 8 non-tied topologies.
- Mean service-loss difference: +0.012 pp, CI [-0.072, +0.090], p = 0.7891.
- Mean path-cost difference: +1.702%, CI [+0.755%, +2.813%], p = 0.0039.

The result supports a specific trade-off: tail-robust TE substantially improves
the worst single-link failure, leaves mean failure loss essentially unchanged,
and uses a modestly larger path-cost budget than minimum MLU. Relative to ORC,
it improves the tail without a detected path-cost difference.
