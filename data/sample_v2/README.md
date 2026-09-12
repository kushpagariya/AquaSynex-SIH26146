# AquaSynex Synthetic Development Dataset (SIH26146)

> **Notice**: This dataset is a project-generated synthetic development dataset inspired by the SIH26146 problem statement. It contains no real user, wallet, or criminal data.

## Overview
- **Total Transactions**: 10,000
- **Total Inputs**: 16,116
- **Total Outputs**: 30,501
- **Total Network Events**: 10,000
- **Total Entities**: 1,000
- **Generated On**: 2026-09-12T03:13:48.688431+00:00
- **Random Seed**: 42

## Files
1. `sih_transactions.parquet` — Consolidated raw SIH problem statement format (`input_addresses[]`, `output_addresses[]`, amounts, IP/port/ASN/country).
2. `transactions.parquet` — Canonical transaction level records.
3. `transaction_inputs.parquet` — Normalized inputs with UTXO references.
4. `transaction_outputs.parquet` — Normalized outputs with change flags.
5. `network_events.parquet` — Correlated network-layer peer observations.
6. `entities.parquet` — Synthetic wallet clusters and entity types.
7. `labels.parquet` — Ground-truth scenario labels (isolated to prevent ML leakage).
8. `generation_metadata.json` — Generation parameters and distribution statistics.
9. `sih_transactions_sample.csv` — First 500 records for human inspection.
