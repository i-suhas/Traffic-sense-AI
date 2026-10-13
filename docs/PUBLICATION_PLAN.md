# Publication action plan: from executable MVP to defensible paper

## 1. Freeze the research question
**RQ:** On an OSM-derived Mysuru road-network simulation, does variable-duration SMDP control reduce delay and queueing compared with fixed-time and local density-responsive control, under matched demand scenarios?

**RQ2 (after ST-GNN validation):** Does graph-temporal queue prediction add statistically reliable value over local SMDP and neighbor-aware SMDP?

## 2. Define hypotheses before experiments
- H1: density-responsive control improves at least one delay/queue metric over fixed-time under some demand regimes.
- H2: variable-duration SMDP improves average travel-time loss versus the density heuristic across held-out seeds.
- H3: ST-GNN-based forecasting improves queue prediction over persistence and moving-average baselines on held-out scenarios.
- H4: emergency priority reduces emergency-vehicle travel time without unacceptable increases in ordinary-vehicle delay.
- H5: forecast-informed pressure control improves a pre-registered traffic objective over pressure control alone.

Treat each as a hypothesis, not a promised result. A null or mixed result can still make a useful paper if methods and analysis are sound.

## 3. Build an experiment matrix
- Controllers: fixed-time, density-responsive, SMDP, pressure-informed control; emergency-priority ablation; forecast-pressure only after the ST-GNN beats simple forecasting baselines.
- Demand: low/medium/high demand, directional rush-hour imbalance, short congestion surge, incident/blocked edge if implemented.
- Seeds: at least 10 matched random seeds for an initial study; more if power/variance requires it.
- Replications: identical network, route seed, simulation horizon, vehicle types, and demand profile across controllers.
- Train/test: train the ST-GNN on training seeds only; report untouched test seeds once.

## 4. Metrics
Primary outcomes: mean trip time loss, mean trip duration, trip waiting time. Secondary: mean/max halting vehicles, queue pressure, throughput (completed trips), network travel time, max red time, fairness across approaches. Report unfinished trips and teleportation settings; disabling teleportation is useful for congestion studies but can create gridlock, so report it.

## 5. Statistical analysis
- Report per-seed results, mean ± standard deviation, median, and 95% confidence intervals.
- Use paired comparisons because demand seeds are matched. Consider paired bootstrap confidence intervals; use a paired test only after checking assumptions and report effect sizes.
- Correct for multiple comparisons if making many confirmatory claims.
- Plot controller performance versus demand intensity, not only one overall average.
- Release the exact configs, random seeds, network boundary/bbox, OSM download date, dependency versions, and raw run summaries.

## 6. Required ablations
- SMDP duration-aware discount versus a standard one-step discount.
- Local state versus neighbor state.
- With/without graph aggregation.
- With/without temporal encoder.
- Green duration action set sensitivity.
- Demand intensity and random-seed sensitivity.

## 7. Paper structure
1. Introduction: problem, limitations of fixed-time/local-actuated methods, contributions stated conservatively.
2. Related work: adaptive control, MARL, SMDP, traffic forecasting, ST-GNN; compare assumptions and datasets.
3. Problem formulation: graph definition, observation, action, reward, semi-Markov transition duration, constraints.
4. Method: controller, temporal graph model, integration, safety envelope.
5. Experimental setup: Mysuru area, OSM extraction, SUMO version, demand generation/calibration, seeds, baselines, hardware.
6. Results: descriptive results, statistical comparisons, congestion regimes, ablations.
7. Discussion: where it helps, where it fails, transfer/generalization, operational constraints.
8. Limitations and conclusion.

## 8. Fix claims in the original theoretical manuscript
- Do not say Nash-equilibrium convergence is guaranteed unless a theorem is rigorously proved for the exact algorithm, game, stationarity assumptions, and update rules. Empirical stability is not a proof.
- Complexity `O(|E| F F')` is only the graph aggregation cost under a specific sparse implementation; include temporal layers, nodes, batch, sequence length, and model dimensions for total cost.
- Explain whether agents share parameters, rewards, observations, or a centralized critic.
- Specify whether the graph is directed/weighted and how upstream/downstream adjacency is built from OSM/SUMO.
- Define all units, observation cadence, reward scaling, minimum/maximum green, yellow/all-red transitions, max-red constraints, and handling of pedestrians/emergency vehicles.
- Do not describe randomTrips demand as real traffic data. Either calibrate with counts/trajectory data or call it synthetic demand on a real road geometry.

## 9. Reproducibility and integrity checklist
- [ ] Pin Python/SUMO/package versions and upload a requirements/lock file.
- [ ] Keep all demand seeds and config files under version control.
- [ ] Save raw metrics per run; do not report only aggregated numbers.
- [ ] Ensure no test-seed leakage into model tuning.
- [ ] Include negative/null results and failed scenarios.
- [ ] Report OSM attribution/license and data acquisition date.
- [ ] Add limitations: simulation-to-reality gap, demand calibration, detector noise, safety certification, pedestrians, emergency vehicles.
- [ ] Verify the target venue's scope, review model, fees, indexing, and author guidelines on its official site before submission.
- [ ] Never pay a journal/conference based only on unsolicited email or guaranteed-acceptance claims.

## 10. Recommended next implementation milestones
A. Get the demo scenario running and validate metrics. B. Fix any controller/network-specific edge cases. C. Run matched-seed baselines. D. Build the true intersection adjacency matrix. E. Train/evaluate queue predictor. F. Integrate predictor into state and run ablations. G. Draft results only after experiments finish.
