# Reproducibility artifact — curvature and failure-aware traffic engineering

This directory is the executable artifact for the Computer Networks manuscript
“Does Discrete Ricci Curvature Improve Failure-Aware Traffic Engineering?”
It preserves directed capacities and OD commodities, uses common candidate
paths for every policy, and evaluates routing with independent physical-link
failure outcomes.

The exact submission artifact is archived as version 3.0.0 at
`https://doi.org/10.5281/zenodo.21375484`. The concept DOI
`10.5281/zenodo.20836716` represents the complete version history.

## Environment

Tested with Python 3.11 on Windows. Install the exact numerical environment:

```text
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-lock.txt
```

The portable Ollivier implementation solves each local optimal-transport
problem directly and does not invoke the Unix-only multiprocessing path in
GraphRicciCurvature.

## External benchmark data

Experiments use REPETITA commit
`60e679c2f34d9b65b7f256ff6f6963938fa040f9`, dataset
`data/2016TopologyZooUCL_inverseCapacity`. The benchmark is not redistributed
here. Place the checkout at `../external/Repetita`, or pass `--dataset-root`.

## Canonical pipeline

Run from this directory's parent with `reproducibility_code` on `PYTHONPATH`:

```text
$env:PYTHONPATH="reproducibility_code"  # PowerShell
python -m unittest discover -s reproducibility_code/tests -v

# Prospectively frozen ten-topology single-link confirmation
python -m geo_routing.exp_repetita \
  --topologies Aconet Easynet Noel Belnet2010 Garr200109 Fccn \
  Packetexchange GtsRomania Fatman Nextgen \
  --output reproducibility_code/results/repetita_confirmatory.json

# Separately frozen single-link tail validation
python -m geo_routing.exp_repetita --include-tail-robust \
  --topologies Claranet HiberniaUk Nordu2010 Spiralight Garr199901 Grena \
  HostwayInternational Marwan Peer1 Rhnet \
  --output reproducibility_code/results/repetita_tail_validation.json

# Frozen held-out double-link study; checkpoints are atomic
python -m geo_routing.exp_submission_upgrade
python -m geo_routing.analyze_submission_upgrade
python -m geo_routing.validate_submission_output --require-complete

# One-factor robustness checks and fixed 30–69-node timing sequence
python -m geo_routing.exp_sensitivity
python -m geo_routing.exp_scalability

# Post-upgrade CVaR-level/scenario-budget sensitivity and adaptive summary
python -m geo_routing.exp_scenario_sensitivity --resume
python -m geo_routing.analyze_scenario_sensitivity
python -m geo_routing.validate_scenario_sensitivity --require-complete
```

On macOS or Linux, replace the PowerShell assignment with
`export PYTHONPATH=reproducibility_code`.

The manuscript-level protocols and audit trail are one directory above:

- `CONFIRMATORY_PROTOCOL.md`
- `TAIL_VALIDATION_PROTOCOL.md`
- `SUBMISSION_UPGRADE_PROTOCOL.md`
- `SCENARIO_RISK_SENSITIVITY_PROTOCOL.md`
- `SUBMISSION_UPGRADE_CHANGE_LOG.md`
- `CONSISTENCY_AUDIT.md`

## Key modules

- `geo_routing/failure_aware.py`: path-based multi-commodity TE, structural
  regularization, expected/CVaR/minimax scenario-risk programs, and frozen or
  adaptive failure outcomes.
- `geo_routing/repetita.py`: directed REPETITA parser and physical projection.
- `geo_routing/exp_repetita.py`: single-link held-out experiment.
- `geo_routing/exp_submission_upgrade.py`: deterministic topology/scenario
  held-out double-link experiment.
- `geo_routing/analyze_submission_upgrade.py`: topology-cluster bootstrap,
  exact sign-flip inference, and Holm families.
- `geo_routing/exp_sensitivity.py`: frozen one-factor sensitivity suite.
- `geo_routing/exp_scenario_sensitivity.py`: one-factor CVaR-level and
  scenario-budget robustness suite on the unchanged held-out failures.
- `geo_routing/analyze_scenario_sensitivity.py`: topology-level robustness,
  adaptive recovery ceiling, and structural-score association summaries.
- `geo_routing/validate_scenario_sensitivity.py`: source-hash, held-out-set,
  condition, row-count, loss-range, and latency-budget integrity checks.
- `geo_routing/exp_scalability.py`: fixed feasibility and timing sequence.

Older synthetic-topology scripts (`final_run.py`, `exp_scal.py`,
`exp_selfheal.py`, and `exp_baseline.py`) reproduce the rejected Physica A
version. They are retained for provenance but do not support claims in the
rebuilt manuscript.

## Reproducibility rules

- Traffic matrix 0000 is used for tuning; 0001–0004 are held out from tuning.
- Physical failures remove both directed arcs.
- Failure scenarios never depend on curvature or observed performance.
- The experimental unit for inference is the topology, not the link-scenario
  row.
- JSON result files are written atomically after each topology.
- Any post-freeze bug fix must have a regression test and an entry in the
  change log.

## License

Code is released under the MIT License. REPETITA data retain their original
license and attribution.
