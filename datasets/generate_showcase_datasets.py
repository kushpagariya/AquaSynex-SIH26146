"""
AquaSynex SIH26146 dataset generator.

This generator creates deterministic test/showcase datasets by selecting rows
from the official SIH synthetic sample. It does NOT invent or alter transaction
values, addresses, timestamps, network fields, or scenario metadata.

Usage:
    python generate_showcase_datasets.py path/to/sih_transactions_sample.csv output_dir

The scenario_id column is retained for evaluation/ground-truth analysis only.
It must NOT be supplied as a predictive ML feature.
"""

from pathlib import Path
import sys
import pandas as pd

REQUIRED = [
    "timestamp", "src_ip", "dst_ip", "src_port", "dst_port", "txid",
    "input_addresses", "output_addresses", "input_amounts", "output_amounts",
    "fee", "script_type", "country", "asn",
]

def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python generate_showcase_datasets.py <input.csv> <output_dir>")

    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(src)

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required SIH fields: {missing}")

    scenario = df["scenario_id"].astype(str)

    datasets = {
        "test_smoke_50.csv": df.head(50),
        "test_normal_100.csv": df[scenario.str.startswith("SCEN_NORMAL")].head(100),
        "showcase_peeling_mixing.csv": df[
            scenario.str.startswith(("SCEN_PEELING", "SCEN_MIXING"))
        ],
        "showcase_burst_network.csv": df[
            scenario.str.startswith(("SCEN_BURST", "SCEN_FAN", "SCEN_TEMPORAL", "SCEN_AMT"))
        ],
        "showcase_coordinated_multihop.csv": df[
            scenario.str.startswith(("SCEN_COORDINATED", "SCEN_MULTIHOP"))
        ],
        "showcase_typology_mix.csv": df[
            ~scenario.str.startswith(("SCEN_NORMAL", "SCEN_BENIGN"))
        ],
    }

    for name, subset in datasets.items():
        subset.to_csv(out / name, index=False)
        print(f"{name}: {len(subset)} rows")

if __name__ == "__main__":
    main()
