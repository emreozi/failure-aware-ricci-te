# Failure-aware Ricci traffic engineering

This repository contains the manuscript, executable code, frozen protocols, and result files for:

> **Does Discrete Ricci Curvature Improve Failure-Aware Traffic Engineering? A Controlled Comparison with Direct Scenario-Risk Optimization**

The study tests whether discrete Ricci-curvature information adds measurable failure resilience beyond conventional congestion-aware traffic engineering, and compares structural regularization with expected-loss, CVaR, and minimax scenario-risk optimization under held-out physical-link failures.

## Main finding

Curvature-derived structural scores are useful diagnostics, but structural regularization does not reliably outperform the congestion-only baseline under the controlled evaluation. Direct scenario-risk optimization provides the more consistent protection against severe single- and double-link failure outcomes, while the manuscript reports the associated nominal-performance and runtime trade-offs.

## Repository layout

- `manuscript/`: submission manuscript source, bibliography, generated tables and figures, and the compiled PDF.
- `reproducibility_code/`: Python implementation, tests, experiment drivers, frozen outputs, and detailed execution instructions.
- `*_PROTOCOL.md`: prospectively frozen experiment and analysis protocols.
- `*_RESULTS.md`: compact experiment summaries.
- `CONSISTENCY_AUDIT.md`: cross-checks between manuscript claims, tables, figures, and executable outputs.
- `SUBMISSION_UPGRADE_CHANGE_LOG.md`: auditable post-freeze changes.

## Reproducing the analysis

The experiments were run with Python 3.11. From the repository root:

```text
python -m venv .venv
.venv/Scripts/python -m pip install -r reproducibility_code/requirements-lock.txt
$env:PYTHONPATH="reproducibility_code"
python -m unittest discover -s reproducibility_code/tests -v
```

The `PYTHONPATH` line above uses PowerShell syntax. On macOS or Linux, use
`export PYTHONPATH=reproducibility_code` instead.

The full experiment sequence, command-line options, and expected external-data layout are documented in [`reproducibility_code/README.md`](reproducibility_code/README.md).

## External benchmark data

The repository does not redistribute REPETITA benchmark data. The recorded source is REPETITA commit `60e679c2f34d9b65b7f256ff6f6963938fa040f9`, dataset `data/2016TopologyZooUCL_inverseCapacity`. Place that checkout at `external/Repetita`, or pass the experiment drivers an explicit `--dataset-root` path.

## Manuscript and archival record

The current manuscript PDF is [`manuscript/main.pdf`](manuscript/main.pdf). The exact submission artifact is archived as version 3.0.0 at [Zenodo](https://doi.org/10.5281/zenodo.21375484). The concept DOI [`10.5281/zenodo.20836716`](https://doi.org/10.5281/zenodo.20836716) represents the complete version history.

## License

Code in this repository is released under the MIT License. The manuscript and generated research outputs remain copyright of their authors unless stated otherwise. REPETITA data retain their original license and attribution.
