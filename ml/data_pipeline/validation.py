"""
AquaSynex — Data Validation Module (Phase 2.2)
SIH26146: AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic

Responsibilities:
- Validate schema types, hex formats, and regex patterns (TXIDs, addresses, IPv4).
- Verify numeric constraints (non-negative satoshis, positive fees, valid ports).
- Enforce strict Bitcoin UTXO conservation: sum(inputs) == sum(outputs) + fee.
- Verify referential integrity between transactions, inputs, outputs, and network events.
- Produce structured, actionable validation reports.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd

HEX_64_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
IPV4_PATTERN = re.compile(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")

@dataclass
class ValidationResult:
    is_valid: bool = True
    total_transactions_checked: int = 0
    total_inputs_checked: int = 0
    total_outputs_checked: int = 0
    total_events_checked: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, message: str):
        self.is_valid = False
        self.errors.append(message)

    def add_warning(self, message: str):
        self.warnings.append(message)

class DataValidationEngine:
    def __init__(self, enforce_dust_limit: bool = True, min_dust_sats: int = 546):
        self.enforce_dust_limit = enforce_dust_limit
        self.min_dust_sats = min_dust_sats

    def validate(self, observational_data: Dict[str, pd.DataFrame]) -> ValidationResult:
        """
        Execute comprehensive validation suite on observational datasets.
        """
        result = ValidationResult()

        df_tx = observational_data.get("transactions", pd.DataFrame())
        df_in = observational_data.get("transaction_inputs", pd.DataFrame())
        df_out = observational_data.get("transaction_outputs", pd.DataFrame())
        df_net = observational_data.get("network_events", pd.DataFrame())

        if df_tx.empty:
            result.add_error("Transactions table is missing or empty.")
            return result

        result.total_transactions_checked = len(df_tx)
        result.total_inputs_checked = len(df_in) if not df_in.empty else 0
        result.total_outputs_checked = len(df_out) if not df_out.empty else 0
        result.total_events_checked = len(df_net) if not df_net.empty else 0

        self._validate_transactions(df_tx, result)
        if not df_in.empty:
            self._validate_inputs(df_in, df_tx, result)
        if not df_out.empty:
            self._validate_outputs(df_out, df_tx, result)
        if not df_net.empty:
            self._validate_network_events(df_net, df_tx, result)

        if not df_in.empty and not df_out.empty:
            self._validate_conservation(df_tx, df_in, df_out, result)

        result.metrics = {
            "transactions_count": len(df_tx),
            "inputs_count": len(df_in) if not df_in.empty else 0,
            "outputs_count": len(df_out) if not df_out.empty else 0,
            "network_events_count": len(df_net) if not df_net.empty else 0,
            "error_count": len(result.errors),
            "warning_count": len(result.warnings)
        }

        return result

    def _validate_transactions(self, df_tx: pd.DataFrame, result: ValidationResult):
        # 1. Uniqueness
        if df_tx["txid"].duplicated().any():
            result.add_error(f"Duplicate TXIDs found in transactions: {df_tx['txid'].duplicated().sum()} duplicates.")

        # 2. Hex format
        invalid_hex = (~df_tx["txid"].str.match(HEX_64_PATTERN, na=False)).sum()
        if invalid_hex > 0:
            result.add_error(f"{invalid_hex} transactions have invalid 64-char hex TXIDs.")

        # 3. Numeric constraints
        if (df_tx["fee_satoshi"] < 0).any():
            result.add_error(f"{(df_tx['fee_satoshi'] < 0).sum()} transactions contain negative fees.")

        if (df_tx["total_input_value_satoshi"] <= 0).any():
            result.add_error(f"{(df_tx['total_input_value_satoshi'] <= 0).sum()} transactions have non-positive input values.")

        if (df_tx["total_output_value_satoshi"] <= 0).any():
            result.add_error(f"{(df_tx['total_output_value_satoshi'] <= 0).sum()} transactions have non-positive output values.")

        # 4. Count constraints
        if (df_tx["input_count"] < 1).any():
            result.add_error(f"{(df_tx['input_count'] < 1).sum()} transactions have input_count < 1.")

        if (df_tx["output_count"] < 1).any():
            result.add_error(f"{(df_tx['output_count'] < 1).sum()} transactions have output_count < 1.")

    def _validate_inputs(self, df_in: pd.DataFrame, df_tx: pd.DataFrame, result: ValidationResult):
        # Uniqueness
        if df_in.duplicated(subset=["txid", "input_index"]).any():
            result.add_error(f"Duplicate (txid, input_index) primary keys in transaction_inputs.")

        # Referential integrity
        orphaned = set(df_in["txid"]) - set(df_tx["txid"])
        if orphaned:
            result.add_error(f"{len(orphaned)} inputs reference non-existent transaction IDs.")

        # Value constraints
        in_val_col = "input_value_satoshi" if "input_value_satoshi" in df_in.columns else ("amount_satoshi" if "amount_satoshi" in df_in.columns else None)
        if in_val_col is not None and (df_in[in_val_col] <= 0).any():
            result.add_error(f"{(df_in[in_val_col] <= 0).sum()} inputs have non-positive {in_val_col}.")

    def _validate_outputs(self, df_out: pd.DataFrame, df_tx: pd.DataFrame, result: ValidationResult):
        # Uniqueness
        if df_out.duplicated(subset=["txid", "output_index"]).any():
            result.add_error(f"Duplicate (txid, output_index) primary keys in transaction_outputs.")

        # Referential integrity
        orphaned = set(df_out["txid"]) - set(df_tx["txid"])
        if orphaned:
            result.add_error(f"{len(orphaned)} outputs reference non-existent transaction IDs.")

        out_val_col = "output_value_satoshi" if "output_value_satoshi" in df_out.columns else ("amount_satoshi" if "amount_satoshi" in df_out.columns else None)
        if out_val_col is not None and (df_out[out_val_col] <= 0).any():
            result.add_error(f"{(df_out[out_val_col] <= 0).sum()} outputs have non-positive {out_val_col}.")

        # Dust limits
        if self.enforce_dust_limit and out_val_col is not None:
            dust_violations = (df_out[out_val_col] < self.min_dust_sats).sum()
            if dust_violations > 0:
                result.add_error(f"{dust_violations} outputs violate Bitcoin dust threshold (< {self.min_dust_sats} satoshis).")

    def _validate_network_events(self, df_net: pd.DataFrame, df_tx: pd.DataFrame, result: ValidationResult):
        # Uniqueness
        if df_net["event_id"].duplicated().any():
            result.add_error(f"Duplicate event_ids found in network_events.")

        # Referential integrity
        orphaned = set(df_net["txid"]) - set(df_tx["txid"])
        if orphaned:
            result.add_error(f"{len(orphaned)} network events reference non-existent transaction IDs.")

        # IP formats
        for col in ["src_ip", "dst_ip"]:
            invalid_ips = (~df_net[col].astype(str).str.match(IPV4_PATTERN)).sum()
            if invalid_ips > 0:
                result.add_error(f"{invalid_ips} invalid IPv4 addresses in network_events.{col}.")

        # Port ranges
        for col in ["src_port", "dst_port"]:
            invalid_ports = ((df_net[col] < 1) | (df_net[col] > 65535)).sum()
            if invalid_ports > 0:
                result.add_error(f"{invalid_ports} invalid ports (<1 or >65535) in network_events.{col}.")

        # Country codes
        invalid_countries = (df_net["country"].astype(str).str.len() != 2).sum()
        if invalid_countries > 0:
            result.add_error(f"{invalid_countries} invalid country codes in network_events.country.")

        # ASNs: Only positive integer ASNs (ASN > 0) are valid
        if "asn" in df_net.columns:
            non_null_asn = df_net["asn"].dropna()
            if len(non_null_asn) > 0:
                numeric_asn = pd.to_numeric(non_null_asn, errors="coerce")
                invalid_or_non_positive = int(((numeric_asn <= 0) | numeric_asn.isna()).sum())
                if invalid_or_non_positive > 0:
                    result.add_error(f"{invalid_or_non_positive} non-positive or invalid ASNs in network_events.asn.")

    def _validate_conservation(
        self, 
        df_tx: pd.DataFrame, 
        df_in: pd.DataFrame, 
        df_out: pd.DataFrame, 
        result: ValidationResult
    ):
        # 1. Transaction row conservation: in == out + fee
        expected_in = df_tx["total_output_value_satoshi"] + df_tx["fee_satoshi"]
        diff = (df_tx["total_input_value_satoshi"] != expected_in).sum()
        if diff > 0:
            result.add_error(f"{diff} transactions violate aggregate conservation (total_input != total_output + fee).")

        # 2. Relational input sum alignment
        in_sums = df_in.groupby("txid")["amount_satoshi"].sum()
        tx_in = df_tx.set_index("txid")["total_input_value_satoshi"]
        s1, s2 = in_sums.align(tx_in)
        mismatch_in = (s1 != s2).sum()
        if mismatch_in > 0:
            result.add_error(f"{mismatch_in} transactions have input sum mismatches with transaction header.")

        # 3. Relational output sum alignment
        out_sums = df_out.groupby("txid")["amount_satoshi"].sum()
        tx_out = df_tx.set_index("txid")["total_output_value_satoshi"]
        s3, s4 = out_sums.align(tx_out)
        mismatch_out = (s3 != s4).sum()
        if mismatch_out > 0:
            result.add_error(f"{mismatch_out} transactions have output sum mismatches with transaction header.")
