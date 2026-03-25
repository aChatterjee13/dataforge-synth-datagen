"""
Novel Quality Innovations - Advanced Synthetic Data Quality Metrics
Implements cutting-edge quality assessment techniques beyond traditional statistical tests
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from scipy import stats
from scipy.spatial.distance import pdist, squareform
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, mean_squared_error, r2_score
from sklearn.tree import DecisionTreeClassifier
import warnings
warnings.filterwarnings('ignore')

from app.utils.logger import get_logger

logger = get_logger(__name__)


class NovelQualityMetrics:
    """
    Novel quality metrics for comprehensive synthetic data evaluation
    """

    def __init__(
        self,
        original_df: pd.DataFrame,
        synthetic_df: pd.DataFrame,
        target_variables: Optional[List[Dict[str, str]]] = None
    ):
        self.original_df = original_df
        self.synthetic_df = synthetic_df
        self.target_variables = target_variables  # Store user-specified targets
        self.numeric_cols = original_df.select_dtypes(include=[np.number]).columns.tolist()
        self.categorical_cols = original_df.select_dtypes(include=['object', 'category']).columns.tolist()

    def compute_all_novel_metrics(self) -> Dict[str, Any]:
        """Compute all novel quality metrics"""
        novel_metrics = {}

        try:
            # 1. ML Efficacy Score
            ml_efficacy = self.compute_ml_efficacy_score()
            novel_metrics['ml_efficacy'] = ml_efficacy

            # 2. Feature Importance Preservation
            feature_importance = self.compute_feature_importance_preservation()
            novel_metrics['feature_importance_preservation'] = feature_importance

            # 3. Rare Event Preservation
            rare_events = self.compute_rare_event_preservation()
            novel_metrics['rare_event_preservation'] = rare_events

            # 4. Multivariate Interaction Score
            multivariate = self.compute_multivariate_interaction_score()
            novel_metrics['multivariate_interactions'] = multivariate

            # 5. Synthetic Detectability Score (TSTR - Train on Synthetic, Test on Real)
            detectability = self.compute_synthetic_detectability()
            novel_metrics['synthetic_detectability'] = detectability

            # 6. Boundary Preservation Score
            boundary = self.compute_boundary_preservation()
            novel_metrics['boundary_preservation'] = boundary

            # 7. Data Manifold Similarity
            manifold = self.compute_manifold_similarity()
            novel_metrics['manifold_similarity'] = manifold

            # Overall Novel Quality Score
            overall_score = self._compute_overall_novel_score(novel_metrics)
            novel_metrics['overall_novel_quality_score'] = overall_score

        except Exception as e:
            logger.error(f"Error computing novel quality metrics: {e}")
            novel_metrics['error'] = str(e)
            novel_metrics['overall_novel_quality_score'] = 0.5

        return novel_metrics

    def compute_ml_efficacy_score(self) -> Dict[str, Any]:
        """
        ML Efficacy Score - Test if models trained on synthetic data perform
        similarly to models trained on real data

        TRTR (Train Real, Test Real) vs TSTR (Train Synthetic, Test Real)
        """
        ml_metrics = {
            'classification_tasks': [],
            'regression_tasks': [],
            'overall_ml_efficacy': 0.0
        }

        try:
            if len(self.numeric_cols) < 2:
                ml_metrics['overall_ml_efficacy'] = 0.5
                ml_metrics['note'] = 'Insufficient numeric columns for ML efficacy test'
                return ml_metrics

            # Determine which targets to evaluate
            if self.target_variables:
                # Use user-specified targets
                logger.info(f"Using user-specified targets: {self.target_variables}")
                classification_targets = [
                    t['column_name'] for t in self.target_variables
                    if t.get('task_type') == 'classification'
                    and t['column_name'] in self.original_df.columns
                ]
                regression_targets = [
                    t['column_name'] for t in self.target_variables
                    if t.get('task_type') == 'regression'
                    and t['column_name'] in self.original_df.columns
                ]
                logger.debug(f"Classification targets: {classification_targets}")
                logger.debug(f"Regression targets: {regression_targets}")
            else:
                # Fall back to auto-detection
                classification_targets = self.categorical_cols[:2]  # Test up to 2 categorical targets
                regression_targets = self.numeric_cols[:2]  # Test up to 2 numeric targets
                logger.debug(f"Auto-detected classification targets: {classification_targets}")
                logger.debug(f"Auto-detected regression targets: {regression_targets}")

            # Try classification tasks
            for target_col in classification_targets:
                try:
                    efficacy = self._test_classification_efficacy(target_col)
                    if efficacy:
                        ml_metrics['classification_tasks'].append(efficacy)
                except Exception as e:
                    logger.error(f"Error testing classification for {target_col}: {e}")
                    continue

            # Try regression tasks
            for target_col in regression_targets:
                try:
                    efficacy = self._test_regression_efficacy(target_col)
                    if efficacy:
                        ml_metrics['regression_tasks'].append(efficacy)
                except Exception as e:
                    logger.error(f"Error testing regression for {target_col}: {e}")
                    continue

            # Compute overall efficacy
            all_scores = []
            if ml_metrics['classification_tasks']:
                all_scores.extend([t['efficacy_score'] for t in ml_metrics['classification_tasks']])
            if ml_metrics['regression_tasks']:
                all_scores.extend([t['efficacy_score'] for t in ml_metrics['regression_tasks']])

            ml_metrics['overall_ml_efficacy'] = float(np.mean(all_scores)) if all_scores else 0.5

        except Exception as e:
            logger.error(f"Error in ML efficacy: {e}")
            ml_metrics['overall_ml_efficacy'] = 0.5

        return ml_metrics

    def _test_classification_efficacy(self, target_col: str) -> Optional[Dict[str, Any]]:
        """Test classification task efficacy"""
        if target_col not in self.original_df.columns or target_col not in self.synthetic_df.columns:
            return None

        # Check if target has enough classes
        if self.original_df[target_col].nunique() < 2 or self.original_df[target_col].nunique() > 10:
            return None

        feature_cols = [c for c in self.numeric_cols if c != target_col]
        if len(feature_cols) < 2:
            return None

        # Prepare real data
        X_real = self.original_df[feature_cols].dropna()
        y_real = self.original_df.loc[X_real.index, target_col].dropna()
        common_idx = X_real.index.intersection(y_real.index)
        X_real = X_real.loc[common_idx]
        y_real = y_real.loc[common_idx]

        if len(X_real) < 50:
            return None

        # Encode target
        le = LabelEncoder()
        y_real_encoded = le.fit_transform(y_real)

        # Prepare synthetic data
        X_synth = self.synthetic_df[feature_cols].dropna()
        y_synth = self.synthetic_df.loc[X_synth.index, target_col].dropna()
        common_idx_synth = X_synth.index.intersection(y_synth.index)
        X_synth = X_synth.loc[common_idx_synth]
        y_synth = y_synth.loc[common_idx_synth]

        # Filter to common classes
        common_classes = set(y_real.unique()) & set(y_synth.unique())
        if len(common_classes) < 2:
            return None

        y_synth_encoded = le.transform(y_synth)

        # Split real data
        X_train_real, X_test_real, y_train_real, y_test_real = train_test_split(
            X_real, y_real_encoded, test_size=0.3, random_state=42
        )

        # TRTR: Train on Real, Test on Real
        model_real = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
        model_real.fit(X_train_real, y_train_real)
        score_trtr = model_real.score(X_test_real, y_test_real)

        # TSTR: Train on Synthetic, Test on Real
        model_synth = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)

        # Limit synthetic training size
        train_size = min(len(X_synth), len(X_train_real))
        X_train_synth = X_synth.iloc[:train_size]
        y_train_synth = y_synth_encoded[:train_size]

        model_synth.fit(X_train_synth, y_train_synth)
        score_tstr = model_synth.score(X_test_real, y_test_real)

        # Efficacy score (how close TSTR is to TRTR)
        efficacy_score = 1.0 - abs(score_trtr - score_tstr)

        return {
            'target_column': target_col,
            'task_type': 'classification',
            'trtr_accuracy': float(score_trtr),
            'tstr_accuracy': float(score_tstr),
            'efficacy_score': float(efficacy_score),
            'interpretation': 'EXCELLENT' if efficacy_score >= 0.9 else 'GOOD' if efficacy_score >= 0.8 else 'MODERATE'
        }

    def _test_regression_efficacy(self, target_col: str) -> Optional[Dict[str, Any]]:
        """Test regression task efficacy"""
        feature_cols = [c for c in self.numeric_cols if c != target_col]
        if len(feature_cols) < 2:
            return None

        # Prepare real data
        X_real = self.original_df[feature_cols].dropna()
        y_real = self.original_df.loc[X_real.index, target_col].dropna()
        common_idx = X_real.index.intersection(y_real.index)
        X_real = X_real.loc[common_idx]
        y_real = y_real.loc[common_idx]

        if len(X_real) < 50:
            return None

        # Prepare synthetic data
        X_synth = self.synthetic_df[feature_cols].dropna()
        y_synth = self.synthetic_df.loc[X_synth.index, target_col].dropna()
        common_idx_synth = X_synth.index.intersection(y_synth.index)
        X_synth = X_synth.loc[common_idx_synth]
        y_synth = y_synth.loc[common_idx_synth]

        # Split real data
        X_train_real, X_test_real, y_train_real, y_test_real = train_test_split(
            X_real, y_real, test_size=0.3, random_state=42
        )

        # TRTR: Train on Real, Test on Real
        model_real = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42)
        model_real.fit(X_train_real, y_train_real)
        score_trtr = model_real.score(X_test_real, y_test_real)

        # TSTR: Train on Synthetic, Test on Real
        model_synth = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42)

        # Limit synthetic training size
        train_size = min(len(X_synth), len(X_train_real))
        X_train_synth = X_synth.iloc[:train_size]
        y_train_synth = y_synth.iloc[:train_size]

        model_synth.fit(X_train_synth, y_train_synth)
        score_tstr = model_synth.score(X_test_real, y_test_real)

        # Efficacy score (how close TSTR is to TRTR)
        efficacy_score = 1.0 - abs(score_trtr - score_tstr)

        return {
            'target_column': target_col,
            'task_type': 'regression',
            'trtr_r2': float(score_trtr),
            'tstr_r2': float(score_tstr),
            'efficacy_score': float(efficacy_score),
            'interpretation': 'EXCELLENT' if efficacy_score >= 0.9 else 'GOOD' if efficacy_score >= 0.8 else 'MODERATE'
        }

    def compute_feature_importance_preservation(self) -> Dict[str, Any]:
        """
        Measure if feature importance rankings are preserved
        """
        importance_metrics = {
            'tasks': [],
            'overall_preservation': 0.0
        }

        try:
            # Determine targets to test
            if self.target_variables:
                # Use user-specified targets (both classification and regression)
                target_cols = [
                    t['column_name'] for t in self.target_variables
                    if t['column_name'] in self.original_df.columns
                ]
            else:
                # Auto-detect: test first 3 numeric targets
                target_cols = self.numeric_cols[:3]

            # Test feature importance for each target
            for target_col in target_cols:
                # Determine if this is classification or regression target
                is_classification = False
                if self.target_variables:
                    # Check user-specified task type
                    target_info = next((t for t in self.target_variables if t['column_name'] == target_col), None)
                    if target_info:
                        is_classification = target_info.get('task_type') == 'classification'
                else:
                    # Auto-detect: classification if categorical or low cardinality
                    is_classification = (
                        target_col in self.categorical_cols or
                        (target_col in self.numeric_cols and self.original_df[target_col].nunique() <= 10)
                    )

                feature_cols = [c for c in self.numeric_cols if c != target_col]
                if len(feature_cols) < 3:
                    continue

                # Prepare data
                X_real = self.original_df[feature_cols].dropna()
                y_real = self.original_df.loc[X_real.index, target_col].dropna()
                common_idx = X_real.index.intersection(y_real.index)
                X_real = X_real.loc[common_idx]
                y_real = y_real.loc[common_idx]

                if len(X_real) < 50:
                    continue

                X_synth = self.synthetic_df[feature_cols].dropna()
                y_synth = self.synthetic_df.loc[X_synth.index, target_col].dropna()
                common_idx_synth = X_synth.index.intersection(y_synth.index)
                X_synth = X_synth.loc[common_idx_synth]
                y_synth = y_synth.loc[common_idx_synth]

                if len(X_synth) < 50:
                    continue

                # Choose appropriate model based on task type
                if is_classification:
                    # Encode categorical targets for classification
                    le = LabelEncoder()
                    y_real_encoded = le.fit_transform(y_real.astype(str))
                    y_synth_encoded = le.transform(y_synth.astype(str))

                    model_real = RandomForestClassifier(n_estimators=50, random_state=42)
                    model_real.fit(X_real, y_real_encoded)
                    importance_real = model_real.feature_importances_

                    model_synth = RandomForestClassifier(n_estimators=50, random_state=42)
                    model_synth.fit(X_synth, y_synth_encoded)
                    importance_synth = model_synth.feature_importances_
                else:
                    # Regression
                    model_real = RandomForestRegressor(n_estimators=50, random_state=42)
                    model_real.fit(X_real, y_real)
                    importance_real = model_real.feature_importances_

                    model_synth = RandomForestRegressor(n_estimators=50, random_state=42)
                    model_synth.fit(X_synth, y_synth)
                    importance_synth = model_synth.feature_importances_

                # Compute rank correlation (Spearman)
                rank_correlation, _ = stats.spearmanr(importance_real, importance_synth)

                # Compute cosine similarity
                cosine_sim = np.dot(importance_real, importance_synth) / (
                    np.linalg.norm(importance_real) * np.linalg.norm(importance_synth) + 1e-10
                )

                importance_metrics['tasks'].append({
                    'target': target_col,
                    'rank_correlation': float(rank_correlation),
                    'cosine_similarity': float(cosine_sim),
                    'top_features_real': [feature_cols[i] for i in np.argsort(importance_real)[-3:][::-1]],
                    'top_features_synthetic': [feature_cols[i] for i in np.argsort(importance_synth)[-3:][::-1]]
                })

            # Overall preservation score
            if importance_metrics['tasks']:
                # Clip negative correlations to 0 (negative correlation means inverted importance)
                scores = [max(0, t['rank_correlation']) for t in importance_metrics['tasks']]
                importance_metrics['overall_preservation'] = float(np.mean(scores))
            else:
                importance_metrics['overall_preservation'] = 0.5

        except Exception as e:
            logger.error(f"Error in feature importance: {e}")
            importance_metrics['overall_preservation'] = 0.5

        return importance_metrics

    def compute_rare_event_preservation(self) -> Dict[str, Any]:
        """
        Measure how well rare events/outliers are preserved
        """
        rare_event_metrics = {
            'numeric_outliers': {},
            'categorical_rare_values': {},
            'overall_rare_event_score': 0.0
        }

        try:
            scores = []

            # Check numeric outliers (using IQR method)
            for col in self.numeric_cols[:5]:
                q1_orig = self.original_df[col].quantile(0.25)
                q3_orig = self.original_df[col].quantile(0.75)
                iqr_orig = q3_orig - q1_orig

                lower_bound = q1_orig - 1.5 * iqr_orig
                upper_bound = q3_orig + 1.5 * iqr_orig

                outlier_rate_orig = (
                    (self.original_df[col] < lower_bound) | (self.original_df[col] > upper_bound)
                ).mean()

                outlier_rate_synth = (
                    (self.synthetic_df[col] < lower_bound) | (self.synthetic_df[col] > upper_bound)
                ).mean()

                # Score based on how close the outlier rates are
                if outlier_rate_orig > 0:
                    similarity = 1 - abs(outlier_rate_orig - outlier_rate_synth) / (outlier_rate_orig + 1e-10)
                else:
                    similarity = 1.0 if outlier_rate_synth == 0 else 0.5

                rare_event_metrics['numeric_outliers'][col] = {
                    'original_outlier_rate': float(outlier_rate_orig),
                    'synthetic_outlier_rate': float(outlier_rate_synth),
                    'preservation_score': float(max(0, similarity))
                }

                scores.append(max(0, similarity))

            # Check categorical rare values (bottom 20%)
            for col in self.categorical_cols[:5]:
                value_counts_orig = self.original_df[col].value_counts(normalize=True)
                value_counts_synth = self.synthetic_df[col].value_counts(normalize=True)

                # Identify rare values (bottom 20% of frequency)
                threshold = value_counts_orig.quantile(0.2)
                rare_values = value_counts_orig[value_counts_orig <= threshold].index.tolist()

                if len(rare_values) > 0:
                    # Check if rare values appear in synthetic data
                    rare_in_synth = sum(1 for v in rare_values if v in value_counts_synth.index)
                    preservation_rate = rare_in_synth / len(rare_values)

                    rare_event_metrics['categorical_rare_values'][col] = {
                        'num_rare_values': len(rare_values),
                        'rare_values_preserved': rare_in_synth,
                        'preservation_rate': float(preservation_rate)
                    }

                    scores.append(preservation_rate)

            rare_event_metrics['overall_rare_event_score'] = float(np.mean(scores)) if scores else 0.5

        except Exception as e:
            logger.error(f"Error in rare event preservation: {e}")
            rare_event_metrics['overall_rare_event_score'] = 0.5

        return rare_event_metrics

    def compute_multivariate_interaction_score(self) -> Dict[str, Any]:
        """
        Measure preservation of complex multivariate interactions (3-way+)
        """
        interaction_metrics = {
            'three_way_interactions': [],
            'overall_interaction_score': 0.0
        }

        try:
            if len(self.numeric_cols) < 3:
                interaction_metrics['overall_interaction_score'] = 0.5
                return interaction_metrics

            scores = []

            # Test 3-way interactions for up to 3 triplets
            num_tests = min(3, len(self.numeric_cols) // 3)
            for i in range(num_tests):
                cols = self.numeric_cols[i*3:(i+1)*3]
                if len(cols) < 3:
                    continue

                # Compute 3-way correlation for original
                orig_data = self.original_df[cols].dropna().values
                synth_data = self.synthetic_df[cols].dropna().values

                if len(orig_data) < 30 or len(synth_data) < 30:
                    continue

                # Compute pairwise distances as a proxy for 3-way interaction
                orig_distances = pdist(orig_data[:min(100, len(orig_data))], metric='euclidean')
                synth_distances = pdist(synth_data[:min(100, len(synth_data))], metric='euclidean')

                # Compare distance distributions
                ks_stat, _ = stats.ks_2samp(orig_distances, synth_distances)
                similarity = 1 - ks_stat

                interaction_metrics['three_way_interactions'].append({
                    'features': cols,
                    'ks_statistic': float(ks_stat),
                    'similarity_score': float(similarity)
                })

                scores.append(similarity)

            interaction_metrics['overall_interaction_score'] = float(np.mean(scores)) if scores else 0.5

        except Exception as e:
            logger.error(f"Error in multivariate interactions: {e}")
            interaction_metrics['overall_interaction_score'] = 0.5

        return interaction_metrics

    def compute_synthetic_detectability(self) -> Dict[str, Any]:
        """
        Measure how easily synthetic data can be distinguished from real data
        Lower detectability = better synthetic data quality
        """
        detectability_metrics = {
            'classifier_accuracy': 0.0,
            'detectability_score': 0.0,
            'interpretation': ''
        }

        try:
            if len(self.numeric_cols) < 2:
                detectability_metrics['detectability_score'] = 0.5
                return detectability_metrics

            # Sample balanced datasets
            sample_size = min(500, len(self.original_df), len(self.synthetic_df))

            orig_sample = self.original_df[self.numeric_cols].dropna().sample(
                n=min(sample_size, len(self.original_df[self.numeric_cols].dropna())),
                random_state=42
            )
            synth_sample = self.synthetic_df[self.numeric_cols].dropna().sample(
                n=min(sample_size, len(self.synthetic_df[self.numeric_cols].dropna())),
                random_state=42
            )

            # Create labels
            X = pd.concat([orig_sample, synth_sample], axis=0)
            y = np.concatenate([np.zeros(len(orig_sample)), np.ones(len(synth_sample))])

            # Train classifier to distinguish real from synthetic
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

            clf = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42)
            clf.fit(X_train, y_train)

            accuracy = clf.score(X_test, y_test)

            # Detectability score (inverse of accuracy - 0.5)
            # If accuracy = 0.5 (random guessing), detectability = 1.0 (perfect, undetectable)
            # If accuracy = 1.0 (perfect classification), detectability = 0.0 (easily detectable)
            detectability_score = 1.0 - abs(accuracy - 0.5) * 2

            detectability_metrics['classifier_accuracy'] = float(accuracy)
            detectability_metrics['detectability_score'] = float(detectability_score)

            if detectability_score >= 0.8:
                detectability_metrics['interpretation'] = 'EXCELLENT - Synthetic data is nearly indistinguishable from real'
            elif detectability_score >= 0.6:
                detectability_metrics['interpretation'] = 'GOOD - Synthetic data has strong similarity to real'
            elif detectability_score >= 0.4:
                detectability_metrics['interpretation'] = 'MODERATE - Some detectability, consider improving generation'
            else:
                detectability_metrics['interpretation'] = 'WEAK - Synthetic data is easily distinguishable'

        except Exception as e:
            logger.error(f"Error in detectability: {e}")
            detectability_metrics['detectability_score'] = 0.5

        return detectability_metrics

    def compute_boundary_preservation(self) -> Dict[str, Any]:
        """
        Check if decision boundaries are preserved using simple decision trees
        """
        boundary_metrics = {
            'boundary_tests': [],
            'overall_boundary_score': 0.0
        }

        try:
            # Test decision boundaries for categorical targets
            for target_col in self.categorical_cols[:2]:
                if self.original_df[target_col].nunique() < 2 or self.original_df[target_col].nunique() > 5:
                    continue

                feature_cols = [c for c in self.numeric_cols if c != target_col][:5]
                if len(feature_cols) < 2:
                    continue

                # Train simple decision tree on real data
                X_real = self.original_df[feature_cols].dropna()
                y_real = self.original_df.loc[X_real.index, target_col].dropna()
                common_idx = X_real.index.intersection(y_real.index)
                X_real = X_real.loc[common_idx]
                y_real = y_real.loc[common_idx]

                if len(X_real) < 50:
                    continue

                le = LabelEncoder()
                y_real_encoded = le.fit_transform(y_real)

                tree_real = DecisionTreeClassifier(max_depth=3, random_state=42)
                tree_real.fit(X_real, y_real_encoded)

                # Test on synthetic data
                X_synth = self.synthetic_df[feature_cols].dropna()
                y_synth = self.synthetic_df.loc[X_synth.index, target_col].dropna()
                common_idx_synth = X_synth.index.intersection(y_synth.index)
                X_synth = X_synth.loc[common_idx_synth]
                y_synth = y_synth.loc[common_idx_synth]

                # Filter to common classes
                common_classes = set(y_real.unique()) & set(y_synth.unique())
                if len(common_classes) < 2:
                    continue

                y_synth_encoded = le.transform(y_synth)

                # Apply real-trained tree to synthetic data
                score_synth = tree_real.score(X_synth, y_synth_encoded)
                score_real = tree_real.score(X_real, y_real_encoded)

                # Boundary preservation = how similar the scores are
                boundary_score = 1.0 - abs(score_real - score_synth)

                boundary_metrics['boundary_tests'].append({
                    'target': target_col,
                    'real_accuracy': float(score_real),
                    'synthetic_accuracy': float(score_synth),
                    'boundary_score': float(boundary_score)
                })

            if boundary_metrics['boundary_tests']:
                scores = [t['boundary_score'] for t in boundary_metrics['boundary_tests']]
                boundary_metrics['overall_boundary_score'] = float(np.mean(scores))
            else:
                boundary_metrics['overall_boundary_score'] = 0.5

        except Exception as e:
            logger.error(f"Error in boundary preservation: {e}")
            boundary_metrics['overall_boundary_score'] = 0.5

        return boundary_metrics

    def compute_manifold_similarity(self) -> Dict[str, Any]:
        """
        Measure if the data manifold (intrinsic structure) is preserved
        Using local density estimation
        """
        manifold_metrics = {
            'density_correlation': 0.0,
            'manifold_score': 0.0
        }

        try:
            if len(self.numeric_cols) < 2:
                manifold_metrics['manifold_score'] = 0.5
                return manifold_metrics

            # Use first few numeric columns
            cols = self.numeric_cols[:min(5, len(self.numeric_cols))]

            # Sample for efficiency
            orig_sample = self.original_df[cols].dropna().sample(
                n=min(200, len(self.original_df[cols].dropna())),
                random_state=42
            ).values

            synth_sample = self.synthetic_df[cols].dropna().sample(
                n=min(200, len(self.synthetic_df[cols].dropna())),
                random_state=42
            ).values

            # Normalize
            scaler = StandardScaler()
            orig_norm = scaler.fit_transform(orig_sample)
            synth_norm = scaler.transform(synth_sample)

            # Compute local densities (average distance to k nearest neighbors)
            k = 10
            orig_distances = squareform(pdist(orig_norm))
            synth_distances = squareform(pdist(synth_norm))

            # Get k-nearest neighbor distances
            orig_knn_distances = np.sort(orig_distances, axis=1)[:, 1:k+1].mean(axis=1)
            synth_knn_distances = np.sort(synth_distances, axis=1)[:, 1:k+1].mean(axis=1)

            # Compare density distributions
            correlation, _ = stats.spearmanr(
                np.sort(orig_knn_distances),
                np.sort(synth_knn_distances)
            )

            manifold_metrics['density_correlation'] = float(correlation)
            manifold_metrics['manifold_score'] = float(max(0, correlation))

        except Exception as e:
            logger.error(f"Error in manifold similarity: {e}")
            manifold_metrics['manifold_score'] = 0.5

        return manifold_metrics

    def _compute_overall_novel_score(self, metrics: Dict[str, Any]) -> float:
        """Compute overall novel quality score"""
        scores = []

        if 'ml_efficacy' in metrics:
            scores.append(np.clip(metrics['ml_efficacy'].get('overall_ml_efficacy', 0.5), 0.0, 1.0))

        if 'feature_importance_preservation' in metrics:
            scores.append(np.clip(metrics['feature_importance_preservation'].get('overall_preservation', 0.5), 0.0, 1.0))

        if 'rare_event_preservation' in metrics:
            scores.append(np.clip(metrics['rare_event_preservation'].get('overall_rare_event_score', 0.5), 0.0, 1.0))

        if 'multivariate_interactions' in metrics:
            scores.append(np.clip(metrics['multivariate_interactions'].get('overall_interaction_score', 0.5), 0.0, 1.0))

        if 'synthetic_detectability' in metrics:
            scores.append(np.clip(metrics['synthetic_detectability'].get('detectability_score', 0.5), 0.0, 1.0))

        if 'boundary_preservation' in metrics:
            scores.append(np.clip(metrics['boundary_preservation'].get('overall_boundary_score', 0.5), 0.0, 1.0))

        if 'manifold_similarity' in metrics:
            scores.append(np.clip(metrics['manifold_similarity'].get('manifold_score', 0.5), 0.0, 1.0))

        overall_score = float(np.mean(scores)) if scores else 0.5
        return float(np.clip(overall_score, 0.0, 1.0))


def compute_novel_quality_metrics(
    original_df: pd.DataFrame,
    synthetic_df: pd.DataFrame,
    target_variables: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Main function to compute all novel quality metrics

    Args:
        original_df: Original dataset
        synthetic_df: Synthetic dataset
        target_variables: Optional list of user-specified target variables
                         Format: [{'column_name': str, 'task_type': 'classification'|'regression'}]

    Returns:
        Dictionary with all novel quality metrics
    """
    nqm = NovelQualityMetrics(original_df, synthetic_df, target_variables=target_variables)
    return nqm.compute_all_novel_metrics()
