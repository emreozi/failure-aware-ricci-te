# Post-confirmatory changes

The confirmatory run in `results/repetita_confirmatory.json` used the hashes
frozen in `CONFIRMATORY_PROTOCOL.md`. It is not rerun or replaced by the changes
below.

After inspecting the confirmatory secondary outcome, a new exploratory
`tail_robust` policy was added. It directly minimizes maximum physical-link flow
exposure within the same MLU and latency budgets. This policy was not part of
the frozen confirmatory protocol; every comparison involving it is exploratory.
It is disabled by default and runs only with `--include-tail-robust`, preserving
the confirmatory policy set for ordinary `exp_repetita` runs.

After design, the tail comparison was frozen in `TAIL_VALIDATION_PROTOCOL.md`
and tested on ten additional topologies not used in development or the first
confirmation. Those outcomes are confirmatory for the tail-vs-ORC comparison.
