# Computer Networks submission build status

Last full rebuild: 14 July 2026.

## Completed

- General scenario-risk LP for expected loss, CVaR(0.90), and minimax loss.
- Deterministic, disjoint design/evaluation double-link scenario split.
- Twelve-topology held-out double-failure experiment and topology-clustered
  inference.
- Six-condition one-factor sensitivity suite (K, MLU slack, ORC alpha).
- Four additional scenario-risk checks (CVaR level and design-scenario budget).
- Numerical adaptive recovery ceiling and ORC/Forman/degree/betweenness
  associations on matched held-out failures.
- Fixed 30--69-node timing/feasibility sequence; unsupported Garr201112 arcs
  are reported without replacement.
- Expanded robust, failure-aware, risk-aware, and geometric-network literature
  through 2026, with an in-manuscript closest-work table.
- Explicit scenario-risk procedure, LP size, nesting result, and design-set
  optimality/held-out boundary.
- Three manuscript figures, eight tables, 30 fully cited references, highlights,
  CRediT, competing-interest, data/code, and generative-AI declarations.
- Thirteen unit tests and both primary and sensitivity JSON integrity validations
  pass.
- MiKTeX build succeeds with no undefined citations/references and no overfull
  boxes. All 25 pages of the current PDF were rendered and visually inspected;
  no clipping, overflow, blank pages, or broken figure/table layouts were found.
  Repeat this inspection after the final DOI insertion and rebuild.

## Required before submission

1. Mint a new Zenodo version containing the final artifact, then replace the
   forward-looking data-availability sentence with its DOI.
2. Re-run the artifact hash manifest after the Zenodo package is frozen.
3. Enter the final DOI and repository URL in the cover letter and submission
   form.
4. Verify author metadata, funding statement (if any), and ORCID in Editorial
   Manager.
5. Upload `main.tex`, `references.bib`, tables, figures, highlights, cover
   letter, competing-interest declaration, and the final PDF as separate items
   where requested.

## Claims that remain excluded

- self-healing or digital-twin claims;
- negative curvature equals a cut edge;
- packet loss without a packet/queue model;
- curvature uniquely or significantly improves resilience;
- CVaR or robust TE is newly invented here;
- carrier readiness or Internet-scale performance.
