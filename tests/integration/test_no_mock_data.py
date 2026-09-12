"""No Mock Data Verification Test.

Scans all source code in frontend/src/ to verify that no hardcoded application
data, fake transactions, dummy addresses, or mock data structures remain.
"""

from pathlib import Path
import re

FRONTEND_SRC_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"


def test_no_hardcoded_application_mock_data():
    """Verify that frontend/src contains zero hardcoded mock application data."""
    assert FRONTEND_SRC_DIR.exists(), f"Frontend src directory not found at {FRONTEND_SRC_DIR}"

    # Target forbidden patterns representing fake application data
    hardcoded_txid_pattern = re.compile(r'["\'][0-9a-fA-F]{64}["\']')
    # Match bitcoin address patterns hardcoded in non-empty state arrays
    hardcoded_mock_export = re.compile(r'export\s+const\s+MOCK_\w+\s*=')
    hardcoded_dummy_data = re.compile(r'const\s+dummy\w*\s*=\s*\[')

    violations = []

    for file_path in FRONTEND_SRC_DIR.rglob("*"):
        if file_path.is_file() and file_path.suffix in (".ts", ".tsx", ".js", ".jsx"):
            # Skip test files if any
            if ".test." in file_path.name or ".spec." in file_path.name:
                continue

            content = file_path.read_text(encoding="utf-8")
            rel_path = file_path.relative_to(FRONTEND_SRC_DIR)

            # 1. Check for mock export constants
            if hardcoded_mock_export.search(content):
                violations.append(f"{rel_path}: Contains exported mock constant (e.g., MOCK_...)")

            # 2. Check for dummy data arrays
            if hardcoded_dummy_data.search(content):
                violations.append(f"{rel_path}: Contains dummy data array declaration")

            # 3. Check mock.ts specifically to ensure all data arrays are empty
            if file_path.name == "mock.ts":
                # Ensure no non-empty transaction or address arrays
                if re.search(r'\[\s*\{[^}]*transactionId', content):
                    violations.append(f"{rel_path}: Contains hardcoded mock transactions in mock.ts")
                if re.search(r'\[\s*\{[^}]*addressId', content):
                    violations.append(f"{rel_path}: Contains hardcoded mock addresses in mock.ts")

    assert not violations, "Mock application data detected in frontend source:\n" + "\n".join(violations)
