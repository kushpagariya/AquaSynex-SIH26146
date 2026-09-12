# AquaSynex SIH26146 Test & Showcase Datasets

Source: the SIH synthetic sample supplied for SIH26146.

These files are **row-selected subsets** of the source dataset. Transaction
contents were not modified, so Bitcoin value conservation and the SIH schema
are preserved.

## Files

- `test_smoke_50.csv` — small 50-transaction smoke test for rapid upload/analysis testing.
- `test_normal_100.csv` — 100 SCEN_NORMAL transactions for checking false-positive behavior.
- `showcase_peeling_mixing.csv` — SCEN_PEELING + SCEN_MIXING scenarios.
- `showcase_burst_network.csv` — SCEN_BURST + SCEN_FAN + SCEN_TEMPORAL + SCEN_AMT.
- `showcase_coordinated_multihop.csv` — SCEN_COORDINATED + SCEN_MULTIHOP.
- `showcase_typology_mix.csv` — all rows except SCEN_NORMAL and SCEN_BENIGN.

## Important

`scenario_id` is evaluation/ground-truth metadata. It must NOT be used as an
input feature to the predictive model.

A showcase dataset does not guarantee that the trained model will classify
every scenario exactly as intended. Use the resulting model scores and
scenario-level evaluation to determine which dataset produces the strongest,
most defensible demonstration.

## Source scenario counts

0
SCEN_NORMAL         254
SCEN_BURST           64
SCEN_MULTIHOP        51
SCEN_PEELING         35
SCEN_COORDINATED     34
SCEN_BENIGN          30
SCEN_FAN             16
SCEN_TEMPORAL         8
SCEN_MIXING           6
SCEN_AMT              2
