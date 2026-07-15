# Submission-upgrade change log

## 2026-07-14 — post-upgrade scenario-risk sensitivity added

After the frozen submission-upgrade analysis was complete, a separate protocol
was written for four one-factor robustness checks: CVaR levels 0.80 and 0.95 at
the original scenario budget, and 40 or 80 design scenarios at CVaR(0.90). The
held-out evaluation split, topology set, traffic matrices, paths, MLU allowance,
and latency allowance were not changed. These results are explicitly labeled
post-upgrade sensitivity and do not replace or redefine the frozen primary
test. A separate validator checks the source-output hash, unchanged evaluation
sets, condition family, latency budgets, row counts, and finite losses.

## 2026-07-14 — adaptive-scenario default corrected before analysis

During the first execution, after three topology checkpoints had been written
but before any outcome analysis, the driver was found to use every held-out
scenario for the adaptive recovery ceiling. Section 6 of the frozen protocol
specifies a deterministic sample of at most 40 scenarios per topology and
traffic matrix. The command was terminated, the default was changed from all
held-out scenarios to the first 40 scenarios in the already hash-sorted
held-out list, and the complete output was regenerated from the first
topology. No topology, primary endpoint, routing policy, scenario assignment,
or held-out frozen-route observation was changed. The discarded checkpoints
had not been analyzed. A user-supplied explicit command-line value remains
available only for diagnostic use and must be labeled as a protocol deviation.

## 2026-07-14 — explicit test-matrix latency constraint added before analysis

During a code-to-protocol equality audit of the restarted run, the structural
ORC policy was found to enforce the 5% latency criterion when selecting its
regularization strength on training matrix 0000, but not as an explicit
constraint on each held-out matrix. Scenario-risk policies already had the
explicit per-matrix constraint. The run was stopped after three checkpoints,
again before outcome analysis. `solve_nominal_te` received an optional
`latency_limit`, the ORC calls were constrained to 105% of the corresponding
minimum-MLU path cost, and a regression test was added. Sensitivity and
scalability drivers were changed consistently. All submission-upgrade outputs
were regenerated from the first topology. This correction enforces the frozen
matched-budget design and cannot be selectively disabled in the reported run.

## 2026-07-14 — complete secondary score-correlation family added

Before the first checkpoint of the next clean run, a protocol-output audit
found that the driver stored the declared adaptive-loss association for ORC but
not for degree, edge betweenness, and Forman curvature. Those three diagnostic
scores were added exactly as specified in Section 6. They do not enter any
routing solution, scenario split, or primary endpoint. The run was restarted
before a checkpoint was produced.

## 2026-07-14 — scalability driver records unsupported fixed instances

The fixed scalability run stopped at Garr201112 because its REPETITA graph has
unequal-cost parallel arcs for a directed node pair. Collapsing those arcs
would change the path model, and the canonical parser intentionally rejects
that approximation. The scalability driver was changed to record a failed
feasibility row with the exact exception and continue to the next topology in
the already fixed sequence. Garr201112 was not replaced, and the three prior
timing checkpoints were retained unchanged. This affects no inferential result.
