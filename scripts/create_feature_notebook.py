import os
import json

def create_feature_engineering_notebook(notebook_path: str):
    def md_cell(source):
        lines = source if isinstance(source, list) else source.splitlines(keepends=True)
        return {
            "cell_type": "markdown",
            "metadata": {},
            "source": lines
        }

    def code_cell(source):
        lines = source if isinstance(source, list) else source.splitlines(keepends=True)
        return {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": lines
        }

    cells = []

    # Markdown Header
    cells.append(md_cell(
        "# AquaSynex Phase 2.3: Feature Engineering & Exploratory Analysis\n\n"
        "**SIH26146 – AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic**\n\n"
        "This notebook provides exploratory statistical analysis of the canonical feature matrix (`features_v1`)\n"
        "generated from the clean canonical dataset (`database/aquasynex.duckdb`).\n\n"
        "> **Notice**: In accordance with the ML audit protocol, **NO models are trained in this notebook**.\n"
        "> The ground-truth label is loaded strictly as an exploratory grouping variable for descriptive statistical comparisons."
    ))

    # Cell 1: Imports and Data Loading
    cells.append(code_cell(
        "import os\n"
        "import duckdb\n"
        "import numpy as np\n"
        "import pandas as pd\n\n"
        "# Connect to DuckDB analytical database\n"
        "db_path = 'database/aquasynex.duckdb' if os.path.exists('database/aquasynex.duckdb') else '../database/aquasynex.duckdb'\n"
        "con = duckdb.connect(db_path, read_only=True)\n"
        "df_features = con.execute('SELECT * FROM features_v1').fetchdf()\n"
        "df_labels = con.execute('SELECT txid as transaction_id, ground_truth_label, behavior_type FROM labels').fetchdf()\n"
        "df_merged = df_features.merge(df_labels, on='transaction_id', how='left')\n"
        "con.close()\n\n"
        "print(f'[*] Loaded Feature Matrix: {df_features.shape[0]:,} rows x {df_features.shape[1]} columns')\n"
        "print(f'[*] Merged with evaluation metadata: {df_merged.shape[0]:,} records')"
    ))

    # Cell 2: Schema & Missingness Audit
    cells.append(code_cell(
        "# Missingness and Infinite Value Audit\n"
        "num_cols = df_features.select_dtypes(include=[np.number]).columns\n"
        "nan_counts = df_features[num_cols].isna().sum()\n"
        "inf_counts = np.isinf(df_features[num_cols]).sum()\n\n"
        "print('=== DATA QUALITY AUDIT ===')\n"
        "print(f'Total Features Analyzed: {len(num_cols)}')\n"
        "print(f'Features with NaN values: {(nan_counts > 0).sum()}')\n"
        "print(f'Features with Infinite values: {(inf_counts > 0).sum()}')\n"
        "print(f'Duplicate Transaction IDs: {df_features[\"transaction_id\"].duplicated().sum()}')\n\n"
        "dtype_summary = df_features.dtypes.value_counts()\n"
        "print('\\nFeature Data Types:')\n"
        "for dt, count in dtype_summary.items():\n"
        "    print(f' - {dt}: {count} columns')"
    ))

    # Cell 3: Descriptive Distribution Statistics & Skewness
    cells.append(code_cell(
        "# Compute comprehensive distribution statistics and skewness\n"
        "stats_list = []\n"
        "for col in num_cols:\n"
        "    series = df_features[col]\n"
        "    stats_list.append({\n"
        "        'feature_name': col,\n"
        "        'mean': series.mean(),\n"
        "        'std': series.std(),\n"
        "        'min': series.min(),\n"
        "        'p25': series.quantile(0.25),\n"
        "        'median': series.median(),\n"
        "        'p75': series.quantile(0.75),\n"
        "        'p95': series.quantile(0.95),\n"
        "        'max': series.max(),\n"
        "        'skewness': series.skew()\n"
        "    })\n\n"
        "df_stats = pd.DataFrame(stats_list)\n"
        "print('=== FEATURE DISTRIBUTIONS & SKEWNESS (Top 10 High-Skew Features) ===')\n"
        "print(df_stats.sort_values(by='skewness', ascending=False)[['feature_name', 'median', 'mean', 'p95', 'skewness']].head(10).to_string(index=False))"
    ))

    # Cell 4: Feature Cardinality & Unique Value Counts
    cells.append(code_cell(
        "# Feature Cardinality Analysis\n"
        "cardinality = []\n"
        "for col in df_features.columns:\n"
        "    n_unique = df_features[col].nunique()\n"
        "    cardinality.append({\n"
        "        'feature_name': col,\n"
        "        'unique_values': n_unique,\n"
        "        'cardinality_type': 'Binary' if n_unique == 2 else ('Discrete' if n_unique < 50 else 'Continuous')\n"
        "    })\n\n"
        "df_card = pd.DataFrame(cardinality)\n"
        "print('=== CARDINALITY BREAKDOWN ===')\n"
        "print(df_card['cardinality_type'].value_counts())\n"
        "print('\\nDiscrete/Binary Features:')\n"
        "print(df_card[df_card['cardinality_type'].isin(['Binary', 'Discrete'])][['feature_name', 'unique_values']].to_string(index=False))"
    ))

    # Cell 5: Outlier Detection via IQR
    cells.append(code_cell(
        "# Outlier Detection using Interquartile Range (IQR = Q3 - Q1)\n"
        "outlier_summary = []\n"
        "for col in num_cols:\n"
        "    q1 = df_features[col].quantile(0.25)\n"
        "    q3 = df_features[col].quantile(0.75)\n"
        "    iqr = q3 - q1\n"
        "    if iqr > 0:\n"
        "        lower = q1 - 1.5 * iqr\n"
        "        upper = q3 + 1.5 * iqr\n"
        "        outliers = ((df_features[col] < lower) | (df_features[col] > upper)).sum()\n"
        "        outlier_pct = (outliers / len(df_features)) * 100\n"
        "        outlier_summary.append({\n"
        "            'feature_name': col,\n"
        "            'outlier_count': outliers,\n"
        "            'outlier_pct': outlier_pct\n"
        "        })\n\n"
        "df_outliers = pd.DataFrame(outlier_summary)\n"
        "print('=== TOP FEATURES WITH NOTABLE OUTLIERS ===')\n"
        "print(df_outliers.sort_values(by='outlier_pct', ascending=False).head(10).to_string(index=False))"
    ))

    # Cell 6: Correlation Analysis among Core Numerical Features
    cells.append(code_cell(
        "# Correlation Matrix among Core Numerical Features\n"
        "selected_cols = [\n"
        "    'tx_input_count', 'tx_output_count', 'tx_total_output_sats', 'tx_fee_sats',\n"
        "    'tx_fee_rate_sat_per_byte', 'tx_value_balance_ratio',\n"
        "    'addr_hist_tx_count', 'addr_hist_active_days',\n"
        "    'time_since_prev_global_tx_sec', 'time_since_prev_addr_tx_sec',\n"
        "    'time_txs_last_1m', 'time_txs_last_5m',\n"
        "    'rel_fan_in', 'rel_fan_out', 'rel_change_value_ratio'\n"
        "]\n"
        "corr_matrix = df_features[selected_cols].corr()\n"
        "print('=== CORRELATION MATRIX SAMPLE ===')\n"
        "print(np.round(corr_matrix[['tx_input_count', 'tx_output_count', 'tx_fee_sats', 'addr_hist_tx_count', 'time_txs_last_1m']], 2).to_string())"
    ))

    # Cell 7: Descriptive Comparisons: Benign vs Suspicious
    cells.append(code_cell(
        "# Descriptive Statistical Comparisons by Ground-Truth Group (Exploratory Only)\n"
        "comparison_cols = [\n"
        "    'tx_input_count', 'tx_output_count', 'tx_fee_rate_sat_per_byte',\n"
        "    'addr_hist_tx_count', 'addr_reuse_count',\n"
        "    'time_since_prev_addr_tx_sec', 'time_txs_last_1m',\n"
        "    'rel_fan_in', 'rel_fan_out', 'rel_change_value_ratio'\n"
        "]\n\n"
        "grouped = df_merged.groupby('ground_truth_label')[comparison_cols].agg(['median', 'mean'])\n"
        "print('=== DESCRIPTIVE COMPARISON: BENIGN (0) vs SUSPICIOUS (1) ===')\n"
        "print(grouped.T.to_string())"
    ))

    # Cell 8: Feature Categorization Matrix for Downstream Phases
    cells.append(code_cell(
        "# Downstream Feature Categorization Matrix\n"
        "print('=== DOWNSTREAM ELIGIBILITY SUMMARY ===')\n"
        "print('Total Feature Matrix: 40 Features + 1 Transaction Identifier = 41 Columns')\n"
        "print('Breakdown: 15 Transaction + 8 Address + 7 Temporal + 6 Network + 4 Relational')\n"
        "print(' - Observational Categorical Context: net_country, net_asn (require categorical encoding before ML)')\n"
        "print(' - Cyclical Preprocessing Note: time_hour_of_day, time_day_of_week should consider sin/cos transforms in modeling')\n"
        "print(' - Retained Redundancy Note: tx_input_count/rel_fan_in, tx_output_count/rel_fan_out evaluated empirically in ML')\n"
        "print(' - Candidates for Unsupervised Anomaly Detection (Isolation Forest): 18 dense continuous numerical features')\n"
        "print(' - Candidates for Supervised Classification (XGBoost / LightGBM): All 40 features (with categorical encoding)')\n"
        "print(' - Candidates for Graph Analysis (Phase 2.4): addr_hist_tx_count, rel_fan_in, rel_fan_out, addr_reuse_count')\n"
        "print('\\n[+] Phase 2.3 Feature Exploration successfully completed. Zero model training performed.')"
    ))

    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.10"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 2
    }

    os.makedirs(os.path.dirname(os.path.abspath(notebook_path)), exist_ok=True)
    with open(notebook_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2)
    print(f"[+] Successfully wrote notebook to: {notebook_path}")

if __name__ == "__main__":
    create_feature_engineering_notebook("notebooks/02_feature_engineering.ipynb")
