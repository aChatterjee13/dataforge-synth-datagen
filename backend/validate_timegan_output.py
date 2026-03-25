"""
Quick validation script for TimeGAN synthetic data
Run this to check if your synthetic time-series data is good
"""

import pandas as pd
import numpy as np
from pathlib import Path


def validate_timegan_output(original_csv: str, synthetic_csv: str):
    """
    Validate TimeGAN synthetic time-series data

    Args:
        original_csv: Path to original CSV file
        synthetic_csv: Path to synthetic CSV file
    """
    print("=" * 60)
    print("TimeGAN Synthetic Data Validation Report")
    print("=" * 60)

    # Load data
    print("\n1. Loading data...")
    original_df = pd.read_csv(original_csv)
    synthetic_df = pd.read_csv(synthetic_csv)

    print(f"   ✓ Original: {len(original_df)} rows, {len(original_df.columns)} columns")
    print(f"   ✓ Synthetic: {len(synthetic_df)} rows, {len(synthetic_df.columns)} columns")

    # Check columns
    print("\n2. Checking columns...")
    orig_cols = set(original_df.columns)
    syn_cols = set(synthetic_df.columns)

    if orig_cols == syn_cols:
        print(f"   ✓ All columns present: {list(orig_cols)}")
    else:
        print(f"   ✗ Column mismatch!")
        print(f"     Missing in synthetic: {orig_cols - syn_cols}")
        print(f"     Extra in synthetic: {syn_cols - orig_cols}")

    # Identify numeric and datetime columns
    print("\n3. Identifying column types...")

    # Try to detect datetime columns
    datetime_cols = []
    for col in original_df.columns:
        if 'date' in col.lower() or 'time' in col.lower():
            try:
                pd.to_datetime(original_df[col])
                datetime_cols.append(col)
            except:
                pass

    numeric_cols = original_df.select_dtypes(include=[np.number]).columns.tolist()

    print(f"   DateTime columns: {datetime_cols}")
    print(f"   Numeric columns: {numeric_cols}")

    # Check datetime column
    if datetime_cols:
        print("\n4. Validating datetime column...")
        dt_col = datetime_cols[0]

        # Check if datetime column exists in synthetic
        if dt_col in synthetic_df.columns:
            print(f"   ✓ DateTime column '{dt_col}' present")

            # Check if it's actually datetime
            try:
                synthetic_dates = pd.to_datetime(synthetic_df[dt_col])
                print(f"   ✓ Valid datetime values")

                # Check date range
                orig_dates = pd.to_datetime(original_df[dt_col])
                print(f"   Original range: {orig_dates.min()} to {orig_dates.max()}")
                print(f"   Synthetic range: {synthetic_dates.min()} to {synthetic_dates.max()}")

                # Check if dates are sequential
                date_diff = synthetic_dates.diff().dropna()
                if date_diff.nunique() <= 3:  # Allow some variation
                    print(f"   ✓ Dates are sequential (freq: {date_diff.mode().iloc[0]})")
                else:
                    print(f"   ⚠ Dates may not be evenly spaced")

            except:
                print(f"   ✗ DateTime column exists but values are not valid dates")
        else:
            print(f"   ✗ DateTime column '{dt_col}' MISSING in synthetic data!")

    # Check numeric columns
    print("\n5. Validating numeric columns...")
    results = []

    for col in numeric_cols:
        if col not in synthetic_df.columns:
            print(f"   ✗ {col}: MISSING")
            continue

        orig_mean = original_df[col].mean()
        orig_std = original_df[col].std()
        orig_min = original_df[col].min()
        orig_max = original_df[col].max()

        syn_mean = synthetic_df[col].mean()
        syn_std = synthetic_df[col].std()
        syn_min = synthetic_df[col].min()
        syn_max = synthetic_df[col].max()

        # Check if distributions are similar (within 30%)
        mean_diff = abs(syn_mean - orig_mean) / abs(orig_mean) if orig_mean != 0 else 0
        std_diff = abs(syn_std - orig_std) / abs(orig_std) if orig_std != 0 else 0

        status = "✓" if mean_diff < 0.3 and std_diff < 0.3 else "⚠"

        print(f"\n   {status} {col}:")
        print(f"      Original  - μ={orig_mean:8.2f}, σ={orig_std:8.2f}, range=[{orig_min:8.2f}, {orig_max:8.2f}]")
        print(f"      Synthetic - μ={syn_mean:8.2f}, σ={syn_std:8.2f}, range=[{syn_min:8.2f}, {syn_max:8.2f}]")
        print(f"      Difference - μ: {mean_diff*100:5.1f}%, σ: {std_diff*100:5.1f}%")

        results.append({
            'column': col,
            'mean_diff': mean_diff,
            'std_diff': std_diff,
            'ok': mean_diff < 0.3 and std_diff < 0.3
        })

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    ok_count = sum(1 for r in results if r['ok'])
    total_count = len(results)

    print(f"\nNumeric columns validated: {ok_count}/{total_count} passed")

    if datetime_cols and datetime_cols[0] in synthetic_df.columns:
        print(f"DateTime column: ✓ Present")
    elif datetime_cols:
        print(f"DateTime column: ✗ Missing")
    else:
        print(f"DateTime column: - None expected")

    # Overall assessment
    print("\n" + "=" * 60)
    if ok_count == total_count and (not datetime_cols or datetime_cols[0] in synthetic_df.columns):
        print("✓ OVERALL: EXCELLENT - Synthetic data looks good!")
    elif ok_count >= total_count * 0.7:
        print("⚠ OVERALL: ACCEPTABLE - Some columns need attention")
    else:
        print("✗ OVERALL: POOR - Significant quality issues")
    print("=" * 60)

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python validate_timegan_output.py <original.csv> <synthetic.csv>")
        print("\nExample:")
        print("  python validate_timegan_output.py data/original.csv outputs/synthetic.csv")
        sys.exit(1)

    original_path = sys.argv[1]
    synthetic_path = sys.argv[2]

    if not Path(original_path).exists():
        print(f"Error: Original file not found: {original_path}")
        sys.exit(1)

    if not Path(synthetic_path).exists():
        print(f"Error: Synthetic file not found: {synthetic_path}")
        sys.exit(1)

    validate_timegan_output(original_path, synthetic_path)
