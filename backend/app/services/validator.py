import pandas as pd
import numpy as np
from scipy import stats
from sklearn.metrics import mutual_info_score
from typing import Dict, Any, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

from app.utils.logger import get_logger

logger = get_logger(__name__)

def calculate_kl_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """Calculate KL divergence between two distributions"""
    # Add small epsilon to avoid log(0)
    epsilon = 1e-10
    p = np.array(p) + epsilon
    q = np.array(q) + epsilon
    # Normalize
    p = p / p.sum()
    q = q / q.sum()
    return float(np.sum(p * np.log(p / q)))

def calculate_js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    """Calculate Jensen-Shannon divergence between two distributions"""
    epsilon = 1e-10
    p = np.array(p) + epsilon
    q = np.array(q) + epsilon
    # Normalize
    p = p / p.sum()
    q = q / q.sum()
    m = 0.5 * (p + q)
    return float(0.5 * (stats.entropy(p, m) + stats.entropy(q, m)))

def calculate_distribution_similarity(original: pd.Series, synthetic: pd.Series) -> Dict[str, Any]:
    """Calculate distribution similarity metrics with divergence measures"""
    metrics = {}
    metrics['column_type'] = 'numeric' if pd.api.types.is_numeric_dtype(original) else 'categorical'

    try:
        if pd.api.types.is_numeric_dtype(original):
            # Clean data
            orig_clean = original.dropna()
            synth_clean = synthetic.dropna()

            # KS test for continuous variables
            ks_stat, ks_pval = stats.ks_2samp(orig_clean, synth_clean)
            metrics['ks_statistic'] = float(ks_stat)
            metrics['ks_pvalue'] = float(ks_pval)

            # Traditional statistics
            metrics['original_mean'] = float(orig_clean.mean())
            metrics['synthetic_mean'] = float(synth_clean.mean())
            metrics['original_std'] = float(orig_clean.std())
            metrics['synthetic_std'] = float(synth_clean.std())
            metrics['mean_diff'] = abs(orig_clean.mean() - synth_clean.mean())
            metrics['std_diff'] = abs(orig_clean.std() - synth_clean.std())
            metrics['std_ratio'] = synth_clean.std() / (orig_clean.std() + 1e-10)

            # Calculate histogram-based divergence
            # Create bins based on original data range
            bins = np.linspace(min(orig_clean.min(), synth_clean.min()),
                              max(orig_clean.max(), synth_clean.max()), 30)
            orig_hist, _ = np.histogram(orig_clean, bins=bins, density=True)
            synth_hist, _ = np.histogram(synth_clean, bins=bins, density=True)

            # Normalize histograms to get probability distributions
            orig_hist = orig_hist / (orig_hist.sum() + 1e-10)
            synth_hist = synth_hist / (synth_hist.sum() + 1e-10)

            # Calculate divergences
            metrics['kl_divergence'] = calculate_kl_divergence(orig_hist, synth_hist)
            metrics['js_divergence'] = calculate_js_divergence(orig_hist, synth_hist)

            # Calculate distribution overlap (histogram intersection)
            overlap = np.sum(np.minimum(orig_hist, synth_hist))
            metrics['distribution_overlap'] = float(overlap)

            # Store histogram data for visualization
            metrics['histogram_data'] = {
                'bins': bins.tolist(),
                'original': orig_hist.tolist(),
                'synthetic': synth_hist.tolist()
            }

        else:
            # Categorical variables
            orig_counts = original.value_counts(normalize=True)
            synth_counts = synthetic.value_counts(normalize=True)

            # Align categories
            all_categories = sorted(set(orig_counts.index) | set(synth_counts.index))
            orig_freq = np.array([orig_counts.get(cat, 0) for cat in all_categories])
            synth_freq = np.array([synth_counts.get(cat, 0) for cat in all_categories])

            # Chi-square test
            chi2_stat = np.sum((orig_freq - synth_freq) ** 2 / (orig_freq + 1e-10))
            metrics['chi2_statistic'] = float(chi2_stat)

            # Calculate divergences
            metrics['kl_divergence'] = calculate_kl_divergence(orig_freq, synth_freq)
            metrics['js_divergence'] = calculate_js_divergence(orig_freq, synth_freq)

            # Distribution overlap
            overlap = np.sum(np.minimum(orig_freq, synth_freq))
            metrics['distribution_overlap'] = float(overlap)

            # Store category distribution for visualization
            metrics['category_data'] = {
                'categories': all_categories,
                'original': orig_freq.tolist(),
                'synthetic': synth_freq.tolist()
            }

    except Exception as e:
        logger.error(f"Error calculating distribution similarity: {e}")
        metrics['error'] = str(e)

    return metrics

def calculate_correlation_preservation(original_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> float:
    """Calculate correlation preservation score"""
    try:
        # Get numeric columns
        numeric_cols = original_df.select_dtypes(include=[np.number]).columns.tolist()

        if len(numeric_cols) < 2:
            return 1.0  # Perfect score if not enough numeric columns

        # Calculate correlations
        orig_corr = original_df[numeric_cols].corr()
        synth_corr = synthetic_df[numeric_cols].corr()

        # Calculate correlation of correlations
        orig_corr_flat = orig_corr.values[np.triu_indices_from(orig_corr.values, k=1)]
        synth_corr_flat = synth_corr.values[np.triu_indices_from(synth_corr.values, k=1)]

        # Pearson correlation between correlation matrices
        if len(orig_corr_flat) > 0:
            correlation = np.corrcoef(orig_corr_flat, synth_corr_flat)[0, 1]
            return float(max(0.0, correlation))  # Ensure non-negative
        else:
            return 1.0

    except Exception as e:
        logger.error(f"Error calculating correlation preservation: {e}")
        return 0.5

def calculate_privacy_score(original_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> Dict[str, float]:
    """Calculate privacy-related metrics"""
    metrics = {}

    try:
        # Check for exact matches (distance to closest record - DCR)
        # Sample a subset for efficiency
        sample_size = min(100, len(synthetic_df))
        synth_sample = synthetic_df.sample(n=sample_size, random_state=42)

        numeric_cols = original_df.select_dtypes(include=[np.number]).columns.tolist()

        if len(numeric_cols) > 0:
            # Normalize data
            orig_norm = (original_df[numeric_cols] - original_df[numeric_cols].mean()) / (original_df[numeric_cols].std() + 1e-10)
            synth_norm = (synth_sample[numeric_cols] - original_df[numeric_cols].mean()) / (original_df[numeric_cols].std() + 1e-10)

            # Calculate minimum distances
            min_distances = []
            for _, synth_row in synth_norm.iterrows():
                distances = np.sqrt(((orig_norm - synth_row) ** 2).sum(axis=1))
                min_distances.append(distances.min())

            avg_min_distance = np.mean(min_distances)
            metrics['avg_distance_to_closest'] = float(avg_min_distance)

            # Check for exact matches (very close records)
            exact_matches = sum(1 for d in min_distances if d < 0.01)
            metrics['exact_matches'] = exact_matches
            metrics['exact_match_rate'] = exact_matches / len(min_distances)

            # Privacy score calculation (higher distance = better privacy)
            # Updated formula: More balanced scoring using sigmoid-like function
            # This gives:
            #   - Distance < 0.5: Poor privacy (0-40%)
            #   - Distance 0.5-1.0: Moderate privacy (40-65%)
            #   - Distance 1.0-2.0: Good privacy (65-85%)
            #   - Distance 2.0+: Excellent privacy (85-100%)

            # Use a logarithmic scale for more realistic scoring
            if avg_min_distance < 0.01:
                # Essentially exact matches - very poor privacy
                privacy_score = 0.1
            elif avg_min_distance < 0.5:
                # Very close records - poor privacy
                privacy_score = 0.2 + (avg_min_distance / 0.5) * 0.3  # 0.2 to 0.5
            elif avg_min_distance < 1.0:
                # Moderately close - acceptable privacy
                privacy_score = 0.5 + ((avg_min_distance - 0.5) / 0.5) * 0.2  # 0.5 to 0.7
            elif avg_min_distance < 2.0:
                # Good distance - good privacy
                privacy_score = 0.7 + ((avg_min_distance - 1.0) / 1.0) * 0.15  # 0.7 to 0.85
            else:
                # Excellent distance - excellent privacy
                # Cap at 0.95 to be realistic (perfect privacy is rare)
                privacy_score = min(0.95, 0.85 + ((avg_min_distance - 2.0) / 3.0) * 0.10)

            # Apply penalty for exact matches
            if exact_matches > 0:
                exact_match_penalty = min(0.15, exact_matches / len(min_distances) * 0.3)
                privacy_score = max(0.1, privacy_score - exact_match_penalty)

            metrics['privacy_score'] = float(privacy_score)

        else:
            # For non-numeric data, use a simpler heuristic
            metrics['privacy_score'] = 0.8  # Default good privacy

    except Exception as e:
        logger.error(f"Error calculating privacy score: {e}")
        metrics['privacy_score'] = 0.5
        metrics['error'] = str(e)

    return metrics

def calculate_overall_quality_score(column_metrics: Dict, correlation_score: float, privacy_score: float) -> float:
    """Calculate overall quality score"""
    try:
        # Average column-level scores
        column_scores = []
        for col, metrics in column_metrics.items():
            if 'quality_score' in metrics:
                column_scores.append(metrics['quality_score'])

        avg_column_score = np.mean(column_scores) if column_scores else 0.5

        # Weighted combination
        quality_score = (
            0.5 * avg_column_score +
            0.3 * correlation_score +
            0.2 * privacy_score
        )

        return float(np.clip(quality_score, 0.0, 1.0))

    except Exception as e:
        logger.error(f"Error calculating overall quality: {e}")
        return 0.5

def perform_pairwise_relationship_tests(original_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> Dict[str, Any]:
    """Perform statistical tests for pairwise relationships between features"""
    relationship_tests = {
        'numeric_pairs': [],
        'categorical_pairs': [],
        'mixed_pairs': []
    }

    numeric_cols = original_df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = original_df.select_dtypes(exclude=[np.number]).columns.tolist()

    # T-tests for numeric pairs (test if means are similar)
    for i, col1 in enumerate(numeric_cols):
        for col2 in numeric_cols[i+1:]:
            try:
                # T-test on original data
                orig_t_stat, orig_p_val = stats.ttest_ind(
                    original_df[col1].dropna(),
                    original_df[col2].dropna()
                )

                # T-test on synthetic data
                synth_t_stat, synth_p_val = stats.ttest_ind(
                    synthetic_df[col1].dropna(),
                    synthetic_df[col2].dropna()
                )

                # Check if null hypothesis rejection is consistent
                alpha = 0.05
                orig_reject_null = orig_p_val < alpha
                synth_reject_null = synth_p_val < alpha
                hypothesis_consistent = orig_reject_null == synth_reject_null

                relationship_tests['numeric_pairs'].append({
                    'feature_1': col1,
                    'feature_2': col2,
                    'test_type': 't-test',
                    'original_statistic': float(orig_t_stat),
                    'original_pvalue': float(orig_p_val),
                    'synthetic_statistic': float(synth_t_stat),
                    'synthetic_pvalue': float(synth_p_val),
                    'original_reject_null': bool(orig_reject_null),
                    'synthetic_reject_null': bool(synth_reject_null),
                    'hypothesis_consistent': bool(hypothesis_consistent)
                })
            except Exception as e:
                logger.error(f"Error in t-test for {col1} and {col2}: {e}")

    # Chi-square tests for categorical pairs (test for independence)
    for i, col1 in enumerate(categorical_cols):
        for col2 in categorical_cols[i+1:]:
            try:
                # Chi-square test on original data
                orig_contingency = pd.crosstab(original_df[col1], original_df[col2])
                orig_chi2, orig_p_val, _, _ = stats.chi2_contingency(orig_contingency)

                # Chi-square test on synthetic data
                synth_contingency = pd.crosstab(synthetic_df[col1], synthetic_df[col2])
                synth_chi2, synth_p_val, _, _ = stats.chi2_contingency(synth_contingency)

                # Check if null hypothesis rejection is consistent
                alpha = 0.05
                orig_reject_null = orig_p_val < alpha
                synth_reject_null = synth_p_val < alpha
                hypothesis_consistent = orig_reject_null == synth_reject_null

                relationship_tests['categorical_pairs'].append({
                    'feature_1': col1,
                    'feature_2': col2,
                    'test_type': 'chi-square',
                    'original_statistic': float(orig_chi2),
                    'original_pvalue': float(orig_p_val),
                    'synthetic_statistic': float(synth_chi2),
                    'synthetic_pvalue': float(synth_p_val),
                    'original_reject_null': bool(orig_reject_null),
                    'synthetic_reject_null': bool(synth_reject_null),
                    'hypothesis_consistent': bool(hypothesis_consistent)
                })
            except Exception as e:
                logger.error(f"Error in chi-square test for {col1} and {col2}: {e}")

    return relationship_tests

def calculate_structural_similarity(original_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate structural similarity metrics including schema validation,
    missing value patterns, value ranges, and cardinality checks
    """
    structural_metrics = {
        'schema_validation': {},
        'missing_patterns': {},
        'value_ranges': {},
        'cardinality': {},
        'data_quality': {},
        'overall_structural_score': 0.0
    }

    scores = []

    # 1. SCHEMA VALIDATION
    orig_columns = set(original_df.columns)
    synth_columns = set(synthetic_df.columns)

    schema_validation = {
        'column_count_match': len(orig_columns) == len(synth_columns),
        'original_column_count': len(orig_columns),
        'synthetic_column_count': len(synth_columns),
        'missing_columns': list(orig_columns - synth_columns),
        'extra_columns': list(synth_columns - orig_columns),
        'column_names_match': orig_columns == synth_columns,
        'data_type_matches': {}
    }

    # Check data type matches for common columns
    common_columns = orig_columns & synth_columns
    type_matches = 0
    for col in common_columns:
        orig_dtype = str(original_df[col].dtype)
        synth_dtype = str(synthetic_df[col].dtype)
        matches = orig_dtype == synth_dtype
        schema_validation['data_type_matches'][col] = {
            'original': orig_dtype,
            'synthetic': synth_dtype,
            'matches': matches
        }
        if matches:
            type_matches += 1

    schema_score = type_matches / len(common_columns) if common_columns else 0.0
    schema_validation['type_match_score'] = float(schema_score)
    scores.append(schema_score)
    structural_metrics['schema_validation'] = schema_validation

    # 2. MISSING VALUE PATTERNS
    missing_patterns = {
        'column_wise_comparison': {}
    }

    missing_scores = []
    for col in common_columns:
        orig_missing_pct = float(original_df[col].isna().mean() * 100)
        synth_missing_pct = float(synthetic_df[col].isna().mean() * 100)
        missing_diff = abs(orig_missing_pct - synth_missing_pct)

        # Score based on how close the missing percentages are
        # Perfect match = 1.0, difference >10% = 0.0
        col_missing_score = max(0.0, 1.0 - (missing_diff / 10.0))
        missing_scores.append(col_missing_score)

        missing_patterns['column_wise_comparison'][col] = {
            'original_missing_pct': orig_missing_pct,
            'synthetic_missing_pct': synth_missing_pct,
            'difference': missing_diff,
            'similarity_score': float(col_missing_score)
        }

    missing_pattern_score = np.mean(missing_scores) if missing_scores else 1.0
    missing_patterns['overall_missing_pattern_score'] = float(missing_pattern_score)
    scores.append(missing_pattern_score)
    structural_metrics['missing_patterns'] = missing_patterns

    # 3. VALUE RANGE VALIDATION (for numeric columns)
    value_ranges = {
        'numeric_columns': {}
    }

    numeric_cols = original_df.select_dtypes(include=[np.number]).columns.tolist()
    range_scores = []

    for col in numeric_cols:
        if col in synthetic_df.columns:
            orig_min = float(original_df[col].min())
            orig_max = float(original_df[col].max())
            synth_min = float(synthetic_df[col].min())
            synth_max = float(synthetic_df[col].max())

            orig_range = orig_max - orig_min

            # Check if synthetic values are within reasonable bounds (allow 10% overflow)
            overflow_margin = 0.10 * orig_range
            lower_bound = orig_min - overflow_margin
            upper_bound = orig_max + overflow_margin

            within_bounds = (synth_min >= lower_bound and synth_max <= upper_bound)

            # Calculate range preservation score
            if orig_range > 0:
                min_diff_normalized = abs(orig_min - synth_min) / orig_range
                max_diff_normalized = abs(orig_max - synth_max) / orig_range
                range_score = max(0.0, 1.0 - (min_diff_normalized + max_diff_normalized) / 2)
            else:
                range_score = 1.0 if orig_min == synth_min else 0.0

            range_scores.append(range_score)

            value_ranges['numeric_columns'][col] = {
                'original_min': orig_min,
                'original_max': orig_max,
                'synthetic_min': synth_min,
                'synthetic_max': synth_max,
                'within_bounds': within_bounds,
                'range_preservation_score': float(range_score)
            }

    value_range_score = np.mean(range_scores) if range_scores else 1.0
    value_ranges['overall_range_score'] = float(value_range_score)
    scores.append(value_range_score)
    structural_metrics['value_ranges'] = value_ranges

    # 4. CARDINALITY CHECKS (for categorical columns)
    cardinality = {
        'categorical_columns': {}
    }

    categorical_cols = original_df.select_dtypes(exclude=[np.number]).columns.tolist()
    cardinality_scores = []

    for col in categorical_cols:
        if col in synthetic_df.columns:
            orig_unique = int(original_df[col].nunique())
            synth_unique = int(synthetic_df[col].nunique())

            # Check category preservation
            orig_categories = set(original_df[col].dropna().unique())
            synth_categories = set(synthetic_df[col].dropna().unique())

            common_categories = orig_categories & synth_categories
            category_preservation = len(common_categories) / len(orig_categories) if orig_categories else 1.0

            # Cardinality similarity score
            if orig_unique > 0:
                cardinality_ratio = min(synth_unique, orig_unique) / max(synth_unique, orig_unique)
            else:
                cardinality_ratio = 1.0 if synth_unique == 0 else 0.0

            # Combined score
            col_cardinality_score = (category_preservation + cardinality_ratio) / 2
            cardinality_scores.append(col_cardinality_score)

            cardinality['categorical_columns'][col] = {
                'original_unique_count': orig_unique,
                'synthetic_unique_count': synth_unique,
                'category_preservation_rate': float(category_preservation),
                'cardinality_ratio': float(cardinality_ratio),
                'similarity_score': float(col_cardinality_score),
                'missing_categories': list(orig_categories - synth_categories),
                'new_categories': list(synth_categories - orig_categories)
            }

    cardinality_score = np.mean(cardinality_scores) if cardinality_scores else 1.0
    cardinality['overall_cardinality_score'] = float(cardinality_score)
    scores.append(cardinality_score)
    structural_metrics['cardinality'] = cardinality

    # 5. DATA QUALITY METRICS
    data_quality = {
        'overall_null_rate_original': float(original_df.isna().mean().mean() * 100),
        'overall_null_rate_synthetic': float(synthetic_df.isna().mean().mean() * 100),
        'row_count_original': len(original_df),
        'row_count_synthetic': len(synthetic_df)
    }

    # Overall null rate similarity
    null_rate_diff = abs(data_quality['overall_null_rate_original'] - data_quality['overall_null_rate_synthetic'])
    null_rate_score = max(0.0, 1.0 - (null_rate_diff / 10.0))
    data_quality['null_rate_similarity_score'] = float(null_rate_score)
    scores.append(null_rate_score)

    structural_metrics['data_quality'] = data_quality

    # OVERALL STRUCTURAL SIMILARITY SCORE
    overall_structural_score = np.mean(scores) if scores else 0.0
    structural_metrics['overall_structural_score'] = float(overall_structural_score)

    # Summary
    structural_metrics['summary'] = {
        'schema_score': float(schema_score),
        'missing_pattern_score': float(missing_pattern_score),
        'value_range_score': float(value_range_score),
        'cardinality_score': float(cardinality_score),
        'data_quality_score': float(null_rate_score)
    }

    return structural_metrics

def calculate_statistical_measures(original_df: pd.DataFrame, synthetic_df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate traditional statistical measures for comparison"""
    measures = {}

    numeric_cols = original_df.select_dtypes(include=[np.number]).columns.tolist()

    if len(numeric_cols) > 0:
        # Means comparison
        measures['means'] = {
            'original': {col: float(original_df[col].mean()) for col in numeric_cols},
            'synthetic': {col: float(synthetic_df[col].mean()) for col in numeric_cols}
        }

        # Standard deviations comparison
        measures['std_devs'] = {
            'original': {col: float(original_df[col].std()) for col in numeric_cols},
            'synthetic': {col: float(synthetic_df[col].std()) for col in numeric_cols}
        }

        # Correlation matrices
        orig_corr = original_df[numeric_cols].corr()
        synth_corr = synthetic_df[numeric_cols].corr()

        measures['correlations'] = {
            'original': orig_corr.to_dict(),
            'synthetic': synth_corr.to_dict()
        }

        # Covariance matrices
        orig_cov = original_df[numeric_cols].cov()
        synth_cov = synthetic_df[numeric_cols].cov()

        measures['covariances'] = {
            'original': orig_cov.to_dict(),
            'synthetic': synth_cov.to_dict()
        }

        # Calculate difference metrics
        measures['correlation_difference'] = float(np.mean(np.abs(orig_corr.values - synth_corr.values)))
        measures['covariance_difference'] = float(np.mean(np.abs(orig_cov.values - synth_cov.values)))

    return measures

def generate_assessment_summary(
    column_metrics: Dict,
    correlation_score: float,
    privacy_score: float,
    relationship_tests: Dict,
    statistical_measures: Dict,
    overall_quality: float
) -> str:
    """Generate a detailed text assessment of the synthetic data quality"""

    summary_parts = []

    # Overall Assessment
    summary_parts.append("=== OVERALL ASSESSMENT ===\n")
    if overall_quality >= 0.9:
        summary_parts.append(f"EXCELLENT: The synthetic data achieved an outstanding quality score of {overall_quality:.2%}. ")
        summary_parts.append("The generated data demonstrates exceptional fidelity to the original dataset.\n")
    elif overall_quality >= 0.75:
        summary_parts.append(f"GOOD: The synthetic data achieved a strong quality score of {overall_quality:.2%}. ")
        summary_parts.append("The generated data shows good fidelity to the original dataset with minor discrepancies.\n")
    elif overall_quality >= 0.6:
        summary_parts.append(f"FAIR: The synthetic data achieved a moderate quality score of {overall_quality:.2%}. ")
        summary_parts.append("The generated data captures major patterns but may have noticeable differences.\n")
    else:
        summary_parts.append(f"NEEDS IMPROVEMENT: The synthetic data achieved a quality score of {overall_quality:.2%}. ")
        summary_parts.append("Consider adjusting generation parameters or using a different model.\n")

    # Distribution Analysis
    summary_parts.append("\n=== DISTRIBUTION SIMILARITY ===\n")
    numeric_cols = [col for col, metrics in column_metrics.items() if metrics.get('column_type') == 'numeric']
    categorical_cols = [col for col, metrics in column_metrics.items() if metrics.get('column_type') == 'categorical']

    if numeric_cols:
        avg_js_div = np.mean([column_metrics[col].get('js_divergence', 0) for col in numeric_cols])
        avg_overlap = np.mean([column_metrics[col].get('distribution_overlap', 0) for col in numeric_cols])
        summary_parts.append(f"Numeric Features ({len(numeric_cols)} columns):\n")
        summary_parts.append(f"  - Average JS Divergence: {avg_js_div:.4f} (lower is better, 0 is perfect)\n")
        summary_parts.append(f"  - Average Distribution Overlap: {avg_overlap:.2%} (higher is better)\n")

        # Highlight best and worst columns
        js_divs = {col: column_metrics[col].get('js_divergence', 1) for col in numeric_cols}
        best_col = min(js_divs, key=js_divs.get)
        worst_col = max(js_divs, key=js_divs.get)
        summary_parts.append(f"  - Best preserved: '{best_col}' (JS Div: {js_divs[best_col]:.4f})\n")
        summary_parts.append(f"  - Needs attention: '{worst_col}' (JS Div: {js_divs[worst_col]:.4f})\n")

    if categorical_cols:
        avg_js_div = np.mean([column_metrics[col].get('js_divergence', 0) for col in categorical_cols])
        summary_parts.append(f"\nCategorical Features ({len(categorical_cols)} columns):\n")
        summary_parts.append(f"  - Average JS Divergence: {avg_js_div:.4f}\n")

    # Relationship Preservation
    summary_parts.append("\n=== RELATIONSHIP PRESERVATION ===\n")
    summary_parts.append(f"Correlation Preservation Score: {correlation_score:.2%}\n")

    if 'means' in statistical_measures:
        mean_diffs = [abs(statistical_measures['means']['original'][col] - statistical_measures['means']['synthetic'][col])
                      for col in statistical_measures['means']['original'].keys()]
        avg_mean_diff = np.mean(mean_diffs)
        summary_parts.append(f"Average Mean Difference: {avg_mean_diff:.4f}\n")

    # Pairwise tests summary
    numeric_pairs = relationship_tests.get('numeric_pairs', [])
    categorical_pairs = relationship_tests.get('categorical_pairs', [])

    if numeric_pairs:
        consistent_numeric = sum(1 for test in numeric_pairs if test['hypothesis_consistent'])
        summary_parts.append(f"\nNumeric Feature Relationships (t-tests):\n")
        summary_parts.append(f"  - Tests performed: {len(numeric_pairs)}\n")
        summary_parts.append(f"  - Hypothesis consistency: {consistent_numeric}/{len(numeric_pairs)} ")
        summary_parts.append(f"({consistent_numeric/len(numeric_pairs):.1%})\n")
        summary_parts.append(f"  - Interpretation: The synthetic data {'preserves' if consistent_numeric/len(numeric_pairs) > 0.8 else 'partially preserves'} ")
        summary_parts.append(f"the statistical relationships between numeric features.\n")

    if categorical_pairs:
        consistent_categorical = sum(1 for test in categorical_pairs if test['hypothesis_consistent'])
        summary_parts.append(f"\nCategorical Feature Relationships (chi-square tests):\n")
        summary_parts.append(f"  - Tests performed: {len(categorical_pairs)}\n")
        summary_parts.append(f"  - Hypothesis consistency: {consistent_categorical}/{len(categorical_pairs)} ")
        summary_parts.append(f"({consistent_categorical/len(categorical_pairs):.1%})\n")
        summary_parts.append(f"  - Interpretation: The synthetic data {'preserves' if consistent_categorical/len(categorical_pairs) > 0.8 else 'partially preserves'} ")
        summary_parts.append(f"the independence/dependence patterns between categorical features.\n")

    # Privacy Assessment
    summary_parts.append("\n=== PRIVACY ASSESSMENT ===\n")
    summary_parts.append(f"Privacy Score: {privacy_score:.2%}\n")
    if privacy_score >= 0.8:
        summary_parts.append("STRONG: The synthetic data shows low risk of re-identification. ")
        summary_parts.append("Records are sufficiently different from the original data.\n")
    elif privacy_score >= 0.6:
        summary_parts.append("MODERATE: The synthetic data has reasonable privacy protection. ")
        summary_parts.append("Some records may be similar to original data.\n")
    else:
        summary_parts.append("WEAK: Consider increasing privacy parameters. ")
        summary_parts.append("Some records may be too similar to original data.\n")

    # Recommendations
    summary_parts.append("\n=== RECOMMENDATIONS ===\n")
    if overall_quality >= 0.85 and privacy_score >= 0.75:
        summary_parts.append("✓ This synthetic dataset is suitable for production use.\n")
        summary_parts.append("✓ Can be used for ML model training, testing, and data sharing.\n")
    elif overall_quality >= 0.7:
        summary_parts.append("• The dataset is usable but consider regenerating with adjusted parameters.\n")
        summary_parts.append("• Suitable for development and testing purposes.\n")
    else:
        summary_parts.append("• Consider using a different model (e.g., CTGAN for complex distributions).\n")
        summary_parts.append("• Increase training epochs for better convergence.\n")
        summary_parts.append("• Check if the original data has sufficient samples for training.\n")

    return "".join(summary_parts)

def validate_synthetic_data(
    original_df: pd.DataFrame,
    synthetic_df: pd.DataFrame,
    target_variables: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Validate synthetic data and return comprehensive metrics

    Args:
        original_df: Original dataset
        synthetic_df: Synthetic dataset
        target_variables: Optional list of user-specified target variables
                         Format: [{'column_name': str, 'task_type': 'classification'|'regression', 'enabled': bool}]
    """

    # Column-level metrics
    column_metrics = {}
    for col in original_df.columns:
        if col in synthetic_df.columns:
            dist_metrics = calculate_distribution_similarity(original_df[col], synthetic_df[col])

            # Calculate column quality score based on JS divergence (works for both numeric and categorical)
            quality_score = 0.7  # Default
            if 'js_divergence' in dist_metrics:
                # Lower divergence = more similar (JS divergence ranges from 0 to 1)
                quality_score = float(np.clip(1.0 - dist_metrics['js_divergence'], 0, 1))
            elif 'ks_pvalue' in dist_metrics:
                # Higher p-value = more similar distributions
                quality_score = float(np.clip(dist_metrics['ks_pvalue'], 0, 1))

            column_metrics[col] = {
                **dist_metrics,
                'quality_score': quality_score
            }

    # Correlation preservation
    correlation_score = calculate_correlation_preservation(original_df, synthetic_df)
    correlation_score = float(np.clip(correlation_score, 0.0, 1.0))

    # Privacy metrics
    privacy_metrics = calculate_privacy_score(original_df, synthetic_df)
    privacy_score = float(np.clip(privacy_metrics.get('privacy_score', 0.5), 0.0, 1.0))

    # Pairwise relationship tests
    relationship_tests = perform_pairwise_relationship_tests(original_df, synthetic_df)

    # Traditional statistical measures
    statistical_measures = calculate_statistical_measures(original_df, synthetic_df)

    # Structural similarity metrics (NEW)
    structural_similarity = calculate_structural_similarity(original_df, synthetic_df)

    # Novel quality metrics (INNOVATIVE)
    try:
        from .novel_quality import compute_novel_quality_metrics
        novel_metrics = compute_novel_quality_metrics(
            original_df,
            synthetic_df,
            target_variables=target_variables
        )
    except Exception as e:
        logger.error(f"Error computing novel quality metrics: {e}", exc_info=True)
        novel_metrics = {'overall_novel_quality_score': 0.5}

    # Time-Series ML Efficacy (LSTM/ARIMA) if time-series data detected
    try:
        from .timegan import TimeSeriesDetector
        from .timeseries_metrics import TimeSeriesMLEfficacy

        ts_detection = TimeSeriesDetector.detect_time_series(original_df)
        if ts_detection.get('is_time_series', False):
            logger.info(f"Time-series detected (confidence: {ts_detection.get('confidence', 0)}), evaluating LSTM/ARIMA metrics...")

            # Get datetime column if available
            datetime_col = ts_detection.get('datetime_columns', [None])[0] if ts_detection.get('datetime_columns') else None

            # Get target columns from target_variables or use auto-detection
            target_cols = None
            if target_variables:
                target_cols = [t['column_name'] for t in target_variables if t.get('enabled', True)]

            # Evaluate time-series metrics
            ts_evaluator = TimeSeriesMLEfficacy(
                original_df,
                synthetic_df,
                datetime_col=datetime_col,
                target_columns=target_cols
            )

            ts_metrics = ts_evaluator.evaluate_all(seq_len=10)

            # Add to novel_metrics
            if 'time_series_ml_efficacy' not in novel_metrics:
                novel_metrics['time_series_ml_efficacy'] = ts_metrics

            logger.info(f"Time-series evaluation complete: {ts_metrics.get('interpretation', 'N/A')}")

    except Exception as e:
        logger.error(f"Error computing time-series metrics: {e}", exc_info=True)

    # Overall quality (incorporating novel metrics)
    overall_quality = calculate_overall_quality_score(column_metrics, correlation_score, privacy_score)
    # Boost quality score if novel metrics are excellent
    if 'overall_novel_quality_score' in novel_metrics:
        novel_score = float(np.clip(novel_metrics['overall_novel_quality_score'], 0.0, 1.0))
        overall_quality = (overall_quality * 0.7) + (novel_score * 0.3)

    # Ensure overall quality is within [0, 1] range
    overall_quality = float(np.clip(overall_quality, 0.0, 1.0))

    # Generate assessment summary
    assessment_summary = generate_assessment_summary(
        column_metrics,
        correlation_score,
        privacy_score,
        relationship_tests,
        statistical_measures,
        overall_quality
    )

    # Prepare statistical similarity summary
    statistical_similarity = {
        'correlation_preservation': correlation_score,
        'avg_column_quality': np.mean([m['quality_score'] for m in column_metrics.values()]),
        'num_columns_evaluated': len(column_metrics)
    }

    # Prepare chart data
    charts = {
        'column_quality': {
            col: metrics['quality_score']
            for col, metrics in column_metrics.items()
        },
        'correlation_matrices': {
            'original': original_df.select_dtypes(include=[np.number]).corr().to_dict(),
            'synthetic': synthetic_df.select_dtypes(include=[np.number]).corr().to_dict()
        }
    }

    return {
        'metrics': {
            'quality_score': overall_quality,
            'statistical_similarity': statistical_similarity,
            'correlation_preservation': correlation_score,
            'privacy_score': privacy_score,
            'structural_similarity': structural_similarity,
            'privacy_metrics': privacy_metrics,
            'novel_quality_metrics': novel_metrics,
            'column_metrics': column_metrics,
            'relationship_tests': relationship_tests,
            'statistical_measures': statistical_measures
        },
        'assessment_summary': assessment_summary,
        'charts': charts
    }
