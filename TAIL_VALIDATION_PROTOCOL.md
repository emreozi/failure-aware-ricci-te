# Frozen held-out validation of the direct tail-risk result

Frozen: 14 July 2026, before running any routing or failure outcome on the ten
topologies listed below.

This protocol follows the post-confirmatory design of `tail_robust` and uses a
third topology set that appears in neither the development set nor the first
confirmatory set.

## Primary estimand and test

For topology `g`, let `W_tail,g` and `W_ORC,g` be the worst frozen-route service
loss over all physical single-link failures and held-out traffic matrices under
direct tail-robust and Ollivier--Ricci routing, respectively.

`Theta_g = W_tail,g - W_ORC,g`.

Negative values favor direct tail-risk optimization. The primary test is an
exact two-sided topology-level sign-flip test at alpha = 0.05. Report the
equal-topology mean and topology-cluster bootstrap 95% confidence interval.

Secondary estimands are tail-robust minus minimum-MLU worst loss, mean service
loss, and path cost. They do not replace the primary result.

## Held-out topologies

1. Claranet
2. HiberniaUk
3. Nordu2010
4. Spiralight
5. Garr199901
6. Grena
7. HostwayInternational
8. Marwan
9. Peer1
10. Rhnet

All were screened before freezing for file readability, five traffic matrices,
strong connectivity, and lossless representation as a directed simple graph
with only equal-cost parallel bundles. No failure outcome was inspected.

## Fixed experiment

- REPETITA commit `60e679c2f34d9b65b7f256ff6f6963938fa040f9`.
- Dataset `2016TopologyZooUCL_inverseCapacity`.
- TM 0000 tunes structural regularizers; TMs 0001--0004 test them.
- Eight common delay-shortest candidate paths per OD.
- Directed capacities and OD directions preserved.
- 2% MLU slack and 5% latency budget.
- Exact unweighted ORC with alpha = 0.5.
- Frozen-route evaluation exhausts all physical single-link failures.
- `tail_robust` directly minimizes maximum physical-link flow exposure.
- Run `exp_repetita --include-tail-robust`; adaptive failure sampling is not a
  primary or secondary outcome for this validation.

## Frozen hashes

- `failure_aware.py`: `04E4FFC0A764100A166015ADD1406DDE72FA79E95DB1A5CA134CC0115FA0B659`
- `repetita.py`: `495A448E2CB345D51F62720EB2D78D844BD9A73F3501F9997C12B3DD061A8281`
- `exp_repetita.py`: `0ABE4FBD214F8025C89DEAB4C6A0B8548F84ED7D173C04F4DF7B95214A926E39`
- `analyze_tail.py`: `C9CC04A681E311D7E04012F42863708DCA8552896FB6F710728241A7401D8A64`
