"""
Data Drift Detection Service (Feature 11)
Detects distribution shifts between a baseline and a production snapshot.
Includes concept drift detection when a target column is specified.
"""
import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Any, List, Optional

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import LabelEncoder


def detect_column_drift(
    baseline: pd.Series,
    snapshot: pd.Series,
    column_name: str
) -> Dict[str, Any]:
    """Detect drift for a single column"""
    result = {
        "column_name": column_name,
        "column_type": "numeric" if pd.api.types.is_numeric_dtype(baseline) else "categorical",
        "drift_score": 0.0,
        "p_value": 1.0,
        "test_used": "",
        "alert_level": "green",
        "details": {}
    }

    try:
        if pd.api.types.is_numeric_dtype(baseline):
            # KS test for numeric columns
            base_clean = baseline.dropna()
            snap_clean = snapshot.dropna()

            if len(base_clean) == 0 or len(snap_clean) == 0:
                return result

            ks_stat, p_value = stats.ks_2samp(base_clean, snap_clean)
            result["test_used"] = "Kolmogorov-Smirnov"
            result["p_value"] = float(p_value)
            result["drift_score"] = float(ks_stat)

            result["details"] = {
                "baseline_mean": float(base_clean.mean()),
                "snapshot_mean": float(snap_clean.mean()),
                "baseline_std": float(base_clean.std()),
                "snapshot_std": float(snap_clean.std()),
                "mean_shift": float(abs(base_clean.mean() - snap_clean.mean())),
            }
        else:
            # Chi-square test for categorical columns
            base_counts = baseline.value_counts(normalize=True)
            snap_counts = snapshot.value_counts(normalize=True)

            all_categories = sorted(set(base_counts.index) | set(snap_counts.index))
            base_freq = np.array([base_counts.get(cat, 0) for cat in all_categories])
            snap_freq = np.array([snap_counts.get(cat, 0) for cat in all_categories])

            # Jensen-Shannon divergence as drift score
            epsilon = 1e-10
            p = base_freq + epsilon
            q = snap_freq + epsilon
            p = p / p.sum()
            q = q / q.sum()
            m = 0.5 * (p + q)
            js_div = float(0.5 * (stats.entropy(p, m) + stats.entropy(q, m)))

            # Chi-square test for p-value
            base_raw = baseline.value_counts()
            snap_raw = snapshot.value_counts()
            all_cats = sorted(set(base_raw.index) | set(snap_raw.index))
            observed = np.array([snap_raw.get(c, 0) for c in all_cats], dtype=float)
            expected = np.array([base_raw.get(c, 0) for c in all_cats], dtype=float)
            expected = expected / expected.sum() * observed.sum()
            expected = np.maximum(expected, 1e-10)

            chi2_stat, p_value = stats.chisquare(observed, expected)

            result["test_used"] = "Chi-Square + JS Divergence"
            result["p_value"] = float(p_value)
            result["drift_score"] = float(js_div)

            result["details"] = {
                "js_divergence": float(js_div),
                "chi2_statistic": float(chi2_stat),
                "categories_in_baseline": len(base_counts),
                "categories_in_snapshot": len(snap_counts),
                "new_categories": list(set(snap_counts.index) - set(base_counts.index)),
                "missing_categories": list(set(base_counts.index) - set(snap_counts.index)),
            }

        # Determine alert level
        if result["p_value"] < 0.001 or result["drift_score"] > 0.3:
            result["alert_level"] = "red"
        elif result["p_value"] < 0.05 or result["drift_score"] > 0.1:
            result["alert_level"] = "yellow"
        else:
            result["alert_level"] = "green"

    except Exception as e:
        result["details"]["error"] = str(e)

    return result


# ============================================================================
# CONCEPT DRIFT DETECTION
# ============================================================================

def _prepare_features(
    df: pd.DataFrame,
    target_column: str
) -> tuple:
    """
    Prepare feature matrix and target vector for ML models.
    Encodes categoricals, drops non-usable columns, returns (X, y, feature_names, label_encoders).
    """
    feature_cols = [c for c in df.columns if c != target_column]
    X = df[feature_cols].copy()
    y = df[target_column].copy()

    # Drop rows where target is null
    valid_mask = y.notna()
    X = X[valid_mask]
    y = y[valid_mask]

    label_encoders = {}
    cols_to_drop = []

    for col in X.columns:
        if pd.api.types.is_numeric_dtype(X[col]):
            X[col] = X[col].fillna(X[col].median())
        else:
            # Encode categorical features
            le = LabelEncoder()
            X[col] = X[col].fillna("__MISSING__").astype(str)
            le.fit(X[col])
            X[col] = le.transform(X[col])
            label_encoders[col] = le

    feature_names = list(X.columns)
    return X.values, y.values, feature_names, label_encoders


def _get_task_type(y: np.ndarray) -> str:
    """Determine if target is classification or regression."""
    nunique = len(np.unique(y[~pd.isna(y)]))
    if nunique <= 20:
        return "classification"
    return "regression"


def _encode_target(y: np.ndarray, task_type: str) -> np.ndarray:
    """Encode target for sklearn models."""
    if task_type == "classification":
        le = LabelEncoder()
        return le.fit_transform(y.astype(str))
    return y.astype(float)


def detect_prediction_drift(
    baseline_df: pd.DataFrame,
    snapshot_df: pd.DataFrame,
    target_column: str
) -> Dict[str, Any]:
    """
    Prediction-based concept drift detection.
    Train a model on baseline, compare performance on baseline vs snapshot.
    A significant accuracy drop indicates concept drift.
    """
    X_base, y_base, feature_names, le_base = _prepare_features(baseline_df, target_column)
    X_snap, y_snap, _, _ = _prepare_features(snapshot_df, target_column)

    task_type = _get_task_type(y_base)
    y_base_enc = _encode_target(y_base, task_type)
    y_snap_enc = _encode_target(y_snap, task_type)

    # Use common feature set (handle mismatched encoded columns)
    n_features = min(X_base.shape[1], X_snap.shape[1])
    X_base = X_base[:, :n_features]
    X_snap = X_snap[:, :n_features]

    if task_type == "classification":
        model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        scoring = "accuracy"
    else:
        model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        scoring = "r2"

    # Cross-val score on baseline
    n_splits = min(5, max(2, len(X_base) // 5))
    cv_scores = cross_val_score(model, X_base, y_base_enc, cv=n_splits, scoring=scoring)
    baseline_score = float(np.mean(cv_scores))

    # Train on full baseline, evaluate on snapshot
    model.fit(X_base, y_base_enc)
    snapshot_score = float(model.score(X_snap, y_snap_enc))

    accuracy_drop = baseline_score - snapshot_score

    # Determine alert level
    if accuracy_drop > 0.15:
        alert_level = "red"
    elif accuracy_drop > 0.05:
        alert_level = "yellow"
    else:
        alert_level = "green"

    return {
        "task_type": task_type,
        "baseline_score": round(baseline_score, 4),
        "snapshot_score": round(snapshot_score, 4),
        "accuracy_drop": round(accuracy_drop, 4),
        "drift_detected": accuracy_drop > 0.05,
        "alert_level": alert_level,
        "model_used": "RandomForest"
    }


def detect_feature_importance_shift(
    baseline_df: pd.DataFrame,
    snapshot_df: pd.DataFrame,
    target_column: str
) -> Dict[str, Any]:
    """
    Compare feature importance rankings from RandomForest
    between baseline and snapshot datasets.
    """
    X_base, y_base, feature_names_base, _ = _prepare_features(baseline_df, target_column)
    X_snap, y_snap, feature_names_snap, _ = _prepare_features(snapshot_df, target_column)

    task_type = _get_task_type(y_base)
    y_base_enc = _encode_target(y_base, task_type)
    y_snap_enc = _encode_target(y_snap, task_type)

    ModelClass = RandomForestClassifier if task_type == "classification" else RandomForestRegressor

    # Train on baseline
    model_base = ModelClass(n_estimators=100, random_state=42, n_jobs=-1)
    model_base.fit(X_base, y_base_enc)
    imp_base = model_base.feature_importances_

    # Train on snapshot
    model_snap = ModelClass(n_estimators=100, random_state=42, n_jobs=-1)
    model_snap.fit(X_snap, y_snap_enc)
    imp_snap = model_snap.feature_importances_

    # Use common features for comparison
    common_features = [f for f in feature_names_base if f in feature_names_snap]
    base_idx = [feature_names_base.index(f) for f in common_features]
    snap_idx = [feature_names_snap.index(f) for f in common_features]

    imp_base_common = imp_base[base_idx]
    imp_snap_common = imp_snap[snap_idx]

    # Spearman rank correlation
    if len(common_features) >= 2:
        rank_corr, _ = stats.spearmanr(imp_base_common, imp_snap_common)
        rank_corr = float(rank_corr) if not np.isnan(rank_corr) else 0.0
    else:
        rank_corr = 0.0

    # Cosine similarity
    norm_base = np.linalg.norm(imp_base_common)
    norm_snap = np.linalg.norm(imp_snap_common)
    if norm_base > 0 and norm_snap > 0:
        cosine_sim = float(np.dot(imp_base_common, imp_snap_common) / (norm_base * norm_snap))
    else:
        cosine_sim = 0.0

    importance_drift_score = max(0.0, min(1.0, 1.0 - rank_corr))

    # Top-5 features from each
    top_n = min(5, len(common_features))
    base_sorted = sorted(zip(common_features, imp_base_common), key=lambda x: -x[1])[:top_n]
    snap_sorted = sorted(zip(common_features, imp_snap_common), key=lambda x: -x[1])[:top_n]

    baseline_top = [{"feature_name": f, "importance": round(float(v), 4)} for f, v in base_sorted]
    snapshot_top = [{"feature_name": f, "importance": round(float(v), 4)} for f, v in snap_sorted]

    # Alert level
    if importance_drift_score > 0.4:
        alert_level = "red"
    elif importance_drift_score > 0.2:
        alert_level = "yellow"
    else:
        alert_level = "green"

    return {
        "rank_correlation": round(rank_corr, 4),
        "cosine_similarity": round(cosine_sim, 4),
        "importance_drift_score": round(importance_drift_score, 4),
        "baseline_top_features": baseline_top,
        "snapshot_top_features": snapshot_top,
        "alert_level": alert_level
    }


def detect_conditional_distribution_shift(
    baseline_df: pd.DataFrame,
    snapshot_df: pd.DataFrame,
    target_column: str
) -> Dict[str, Any]:
    """
    Compare P(Y|X_i) per feature using binned analysis.
    Detect which feature-target relationships have changed.
    """
    common_cols = sorted(set(baseline_df.columns) & set(snapshot_df.columns))
    feature_cols = [c for c in common_cols if c != target_column]

    target_is_numeric = pd.api.types.is_numeric_dtype(baseline_df[target_column])
    features_results = []

    for col in feature_cols:
        try:
            base_sub = baseline_df[[col, target_column]].dropna()
            snap_sub = snapshot_df[[col, target_column]].dropna()

            if len(base_sub) < 5 or len(snap_sub) < 5:
                continue

            col_is_numeric = pd.api.types.is_numeric_dtype(base_sub[col])

            # Create bins for the feature
            if col_is_numeric:
                try:
                    base_sub = base_sub.copy()
                    snap_sub = snap_sub.copy()
                    _, bin_edges = pd.qcut(base_sub[col], q=5, retbins=True, duplicates='drop')
                    base_sub.loc[:, 'bin'] = pd.cut(base_sub[col], bins=bin_edges, include_lowest=True)
                    snap_sub.loc[:, 'bin'] = pd.cut(snap_sub[col], bins=bin_edges, include_lowest=True)
                except (ValueError, IndexError):
                    continue
            else:
                base_sub = base_sub.copy()
                snap_sub = snap_sub.copy()
                base_sub.loc[:, 'bin'] = base_sub[col].astype(str)
                snap_sub.loc[:, 'bin'] = snap_sub[col].astype(str)

            # Compute conditional target stats per bin
            common_bins = set(base_sub['bin'].dropna().unique()) & set(snap_sub['bin'].dropna().unique())
            if len(common_bins) == 0:
                continue

            bin_diffs = []
            bin_details = []

            for b in sorted(common_bins, key=str):
                base_target = base_sub[base_sub['bin'] == b][target_column]
                snap_target = snap_sub[snap_sub['bin'] == b][target_column]

                if len(base_target) == 0 or len(snap_target) == 0:
                    continue

                if target_is_numeric:
                    base_mean = float(base_target.mean())
                    snap_mean = float(snap_target.mean())
                    # Normalize diff by baseline range to get 0..1 scale
                    target_range = baseline_df[target_column].max() - baseline_df[target_column].min()
                    if target_range > 0:
                        diff = abs(base_mean - snap_mean) / target_range
                    else:
                        diff = 0.0
                    bin_diffs.append(min(diff, 1.0))
                    bin_details.append({
                        "bin": str(b),
                        "baseline_mean": round(base_mean, 4),
                        "snapshot_mean": round(snap_mean, 4),
                        "diff": round(diff, 4)
                    })
                else:
                    # For categorical target: JS divergence of P(Y|bin)
                    base_dist = base_target.value_counts(normalize=True)
                    snap_dist = snap_target.value_counts(normalize=True)
                    all_vals = sorted(set(base_dist.index) | set(snap_dist.index))
                    p = np.array([base_dist.get(v, 0) for v in all_vals]) + 1e-10
                    q = np.array([snap_dist.get(v, 0) for v in all_vals]) + 1e-10
                    p = p / p.sum()
                    q = q / q.sum()
                    m_arr = 0.5 * (p + q)
                    js = float(0.5 * (stats.entropy(p, m_arr) + stats.entropy(q, m_arr)))
                    bin_diffs.append(min(js, 1.0))
                    bin_details.append({
                        "bin": str(b),
                        "js_divergence": round(js, 4)
                    })

            if len(bin_diffs) == 0:
                continue

            conditional_drift_score = float(np.mean(bin_diffs))

            # Alert level
            if conditional_drift_score > 0.3:
                alert_level = "red"
            elif conditional_drift_score > 0.1:
                alert_level = "yellow"
            else:
                alert_level = "green"

            features_results.append({
                "feature_name": col,
                "conditional_drift_score": round(conditional_drift_score, 4),
                "alert_level": alert_level,
                "bin_details": bin_details
            })

        except Exception:
            continue

    # Sort by drift score descending
    features_results.sort(key=lambda x: -x["conditional_drift_score"])

    overall_score = float(np.mean([f["conditional_drift_score"] for f in features_results])) if features_results else 0.0
    most_drifted = [f["feature_name"] for f in features_results[:3]]

    return {
        "features": features_results,
        "overall_conditional_drift_score": round(min(overall_score, 1.0), 4),
        "most_drifted_features": most_drifted
    }


def detect_concept_drift(
    baseline_df: pd.DataFrame,
    snapshot_df: pd.DataFrame,
    target_column: str
) -> Dict[str, Any]:
    """
    Orchestrate all three concept drift detection techniques.
    Returns combined concept drift results.
    """
    if target_column not in baseline_df.columns or target_column not in snapshot_df.columns:
        raise ValueError(f"Target column '{target_column}' not found in both datasets.")

    if baseline_df[target_column].isna().all() or snapshot_df[target_column].isna().all():
        raise ValueError(f"Target column '{target_column}' is entirely null in one or both datasets.")

    if len(baseline_df) < 10 or len(snapshot_df) < 10:
        raise ValueError("Both datasets must have at least 10 rows for concept drift detection.")

    task_type = _get_task_type(baseline_df[target_column].dropna().values)

    # Run all three techniques
    prediction = detect_prediction_drift(baseline_df, snapshot_df, target_column)
    importance = detect_feature_importance_shift(baseline_df, snapshot_df, target_column)
    conditional = detect_conditional_distribution_shift(baseline_df, snapshot_df, target_column)

    # Weighted overall score
    pred_score = max(0.0, prediction["accuracy_drop"])  # Only count drops, not improvements
    imp_score = importance["importance_drift_score"]
    cond_score = conditional["overall_conditional_drift_score"]

    overall = 0.4 * min(pred_score * 2, 1.0) + 0.3 * imp_score + 0.3 * cond_score  # Scale pred_score: 0.5 drop → 1.0
    overall = round(min(overall, 1.0), 4)

    concept_detected = overall > 0.1 or prediction["alert_level"] == "red" or importance["alert_level"] == "red"

    # Generate summary
    parts = []
    metric_label = "Accuracy" if task_type == "classification" else "R2 Score"

    if prediction["drift_detected"]:
        parts.append(
            f"Prediction drift detected: {metric_label} dropped from "
            f"{prediction['baseline_score']:.2%} to {prediction['snapshot_score']:.2%} "
            f"({prediction['accuracy_drop']:.2%} drop)."
        )
    else:
        parts.append(f"Prediction performance is stable ({metric_label}: {prediction['snapshot_score']:.2%}).")

    if importance["alert_level"] in ("yellow", "red"):
        parts.append(
            f"Feature importance rankings shifted (rank correlation: {importance['rank_correlation']:.2f})."
        )
    else:
        parts.append(f"Feature importance rankings are consistent (rank correlation: {importance['rank_correlation']:.2f}).")

    if conditional["most_drifted_features"]:
        drifted_str = ", ".join(conditional["most_drifted_features"])
        parts.append(f"Most drifted feature-target relationships: {drifted_str}.")

    if concept_detected:
        parts.insert(0, "CONCEPT DRIFT DETECTED.")
    else:
        parts.insert(0, "No significant concept drift detected.")

    summary = " ".join(parts)

    return {
        "target_column": target_column,
        "task_type": task_type,
        "overall_concept_drift_score": overall,
        "concept_drift_detected": concept_detected,
        "prediction_drift": prediction,
        "feature_importance_shift": importance,
        "conditional_distribution_shift": conditional,
        "summary": summary
    }


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

def detect_drift(
    baseline_df: pd.DataFrame,
    snapshot_df: pd.DataFrame,
    target_column: Optional[str] = None
) -> Dict[str, Any]:
    """
    Detect distribution drift between a baseline and snapshot dataset.
    Returns per-column drift metrics and an overall summary.
    Optionally detects concept drift if target_column is specified.
    """
    columns = []
    alert_counts = {"green": 0, "yellow": 0, "red": 0}
    drift_scores = []

    common_cols = set(baseline_df.columns) & set(snapshot_df.columns)

    for col in sorted(common_cols):
        result = detect_column_drift(baseline_df[col], snapshot_df[col], col)
        columns.append(result)
        alert_counts[result["alert_level"]] += 1
        drift_scores.append(result["drift_score"])

    overall_drift = float(np.mean(drift_scores)) if drift_scores else 0.0

    # Generate summary
    total = len(columns)
    if alert_counts["red"] > 0:
        summary = f"Significant drift detected in {alert_counts['red']}/{total} columns. "
        summary += "Review red-flagged columns for potential data quality issues."
    elif alert_counts["yellow"] > 0:
        summary = f"Minor drift detected in {alert_counts['yellow']}/{total} columns. "
        summary += "The data distribution has shifted slightly."
    else:
        summary = f"No significant drift detected across {total} columns. "
        summary += "The datasets appear to have similar distributions."

    # Concept drift detection (optional, isolated from feature drift)
    concept_drift = None
    if target_column:
        try:
            concept_drift = detect_concept_drift(baseline_df, snapshot_df, target_column)
        except Exception as e:
            concept_drift = {"error": str(e)}

    return {
        "overall_drift_score": min(overall_drift, 1.0),
        "columns": columns,
        "summary": summary,
        "alert_counts": alert_counts,
        "concept_drift": concept_drift
    }
