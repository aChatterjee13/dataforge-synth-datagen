import { Sparkles, Brain, Target, TrendingUp, Eye, Layers, GitBranch, CheckCircle2, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './Card';
import type { NovelQualityMetrics } from '../types';
import { useState } from 'react';

interface NovelQualityMetricsProps {
  novelMetrics: NovelQualityMetrics;
}

export default function NovelQualityMetricsComponent({ novelMetrics }: NovelQualityMetricsProps) {
  const overallScore = Math.round(novelMetrics.overall_novel_quality_score * 100);
  const [expandedSections, setExpandedSections] = useState({
    mlEfficacy: true,   // Expanded - core metrics
    featureImportance: false,  // Collapsed
    detectability: false,      // Collapsed
    summary: false,            // Collapsed
  });

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Get overall quality level
  const getQualityLevel = () => {
    if (overallScore >= 85) return { level: 'EXCEPTIONAL', color: 'emerald', icon: Sparkles };
    if (overallScore >= 70) return { level: 'EXCELLENT', color: 'blue', icon: CheckCircle2 };
    if (overallScore >= 55) return { level: 'GOOD', color: 'indigo', icon: TrendingUp };
    return { level: 'NEEDS IMPROVEMENT', color: 'yellow', icon: AlertTriangle };
  };

  const qualityLevel = getQualityLevel();
  const QualityIcon = qualityLevel.icon;

  // Color schemes
  const getColorClasses = (color: string) => {
    const schemes = {
      emerald: {
        bg: 'bg-emerald-50',
        border: 'border-emerald-500',
        text: 'text-emerald-800',
        badge: 'bg-emerald-100 text-emerald-800',
        progress: 'bg-emerald-600',
        icon: 'text-emerald-600'
      },
      blue: {
        bg: 'bg-blue-50',
        border: 'border-blue-500',
        text: 'text-blue-800',
        badge: 'bg-blue-100 text-blue-800',
        progress: 'bg-blue-600',
        icon: 'text-blue-600'
      },
      indigo: {
        bg: 'bg-indigo-50',
        border: 'border-indigo-500',
        text: 'text-indigo-800',
        badge: 'bg-indigo-100 text-indigo-800',
        progress: 'bg-indigo-600',
        icon: 'text-indigo-600'
      },
      yellow: {
        bg: 'bg-yellow-50',
        border: 'border-yellow-500',
        text: 'text-yellow-800',
        badge: 'bg-yellow-100 text-yellow-800',
        progress: 'bg-yellow-600',
        icon: 'text-yellow-600'
      }
    };
    return schemes[color as keyof typeof schemes];
  };

  const colors = getColorClasses(qualityLevel.color);

  // Helper to get score color
  const getScoreColor = (score: number) => {
    if (score >= 0.85) return 'text-emerald-600';
    if (score >= 0.70) return 'text-blue-600';
    if (score >= 0.55) return 'text-indigo-600';
    return 'text-yellow-600';
  };

  // Helper to render progress bar
  const ProgressBar = ({ score, label }: { score: number; label: string }) => {
    const percent = Math.round(score * 100);
    const color = getScoreColor(score);
    return (
      <div className="mb-4">
        <div className="flex justify-between mb-1">
          <span className="text-sm font-medium text-gray-700">{label}</span>
          <span className={`text-sm font-bold ${color}`}>{percent}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div
            className={`h-2.5 rounded-full ${color.replace('text-', 'bg-')}`}
            style={{ width: `${percent}%` }}
          />
        </div>
      </div>
    );
  };

  return (
    <Card className="mb-8">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <Sparkles className={`h-6 w-6 mr-3 ${colors.icon}`} />
            <CardTitle>Novel Quality Metrics</CardTitle>
          </div>
          <span className={`text-4xl font-bold ${colors.text}`}>{overallScore}%</span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Overall Novel Quality Score */}
          <div className={`p-4 rounded-lg border-l-4 ${colors.bg} ${colors.border}`}>
            <div className="flex items-center gap-3">
              <QualityIcon className={`h-6 w-6 ${colors.icon}`} />
              <span className={`px-3 py-1 rounded-full text-sm font-bold ${colors.badge}`}>
                {qualityLevel.level}
              </span>
              <p className={`text-sm ${colors.text} flex-1`}>
                {overallScore >= 85
                  ? 'Exceptional quality - production ready'
                  : overallScore >= 70
                  ? 'Excellent quality for ML applications'
                  : overallScore >= 55
                  ? 'Good quality for development'
                  : 'Room for improvement'}
              </p>
            </div>
          </div>

          {/* ML Efficacy Score */}
          {novelMetrics.ml_efficacy && (
            <div className="bg-white border-2 border-purple-200 rounded-lg p-4">
              <div
                className="flex items-center justify-between cursor-pointer mb-4"
                onClick={() => toggleSection('mlEfficacy')}
              >
                <div className="flex items-center gap-3">
                  <Brain className="h-6 w-6 text-purple-600" />
                  <h3 className="text-lg font-bold text-gray-900">ML Efficacy</h3>
                  <span className="text-2xl font-bold text-purple-600">
                    {Math.round(novelMetrics.ml_efficacy.overall_ml_efficacy * 100)}%
                  </span>
                </div>
                {expandedSections.mlEfficacy ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </div>
              {expandedSections.mlEfficacy && (
              <div>

              <ProgressBar
                score={novelMetrics.ml_efficacy.overall_ml_efficacy}
                label="Overall ML Efficacy"
              />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
                {/* Classification Tasks */}
                {novelMetrics.ml_efficacy.classification_tasks.length > 0 && (
                  <div className="bg-purple-50 p-4 rounded-lg">
                    <h4 className="font-semibold text-purple-900 mb-3 flex items-center">
                      <Target className="h-4 w-4 mr-2" />
                      Classification Tasks ({novelMetrics.ml_efficacy.classification_tasks.length})
                    </h4>
                    <div className="space-y-3">
                      {novelMetrics.ml_efficacy.classification_tasks.map((task, idx) => (
                        <div key={idx} className="bg-white p-3 rounded border border-purple-200">
                          <div className="flex justify-between items-start mb-2">
                            <span className="text-sm font-medium text-gray-800">
                              Target: {task.target_column}
                            </span>
                            <span
                              className={`px-2 py-1 rounded text-xs font-bold ${
                                task.interpretation === 'EXCELLENT'
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : task.interpretation === 'GOOD'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-yellow-100 text-yellow-800'
                              }`}
                            >
                              {task.interpretation}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div>
                              <span className="text-gray-600">TRTR (Real): </span>
                              <span className="font-bold text-blue-600">
                                {((task.trtr_accuracy || 0) * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div>
                              <span className="text-gray-600">TSTR (Synth): </span>
                              <span className="font-bold text-purple-600">
                                {((task.tstr_accuracy || 0) * 100).toFixed(1)}%
                              </span>
                            </div>
                          </div>
                          <div className="mt-2 text-xs">
                            <span className="text-gray-600">Efficacy: </span>
                            <span className={`font-bold ${getScoreColor(task.efficacy_score)}`}>
                              {(task.efficacy_score * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Regression Tasks */}
                {novelMetrics.ml_efficacy.regression_tasks.length > 0 && (
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <h4 className="font-semibold text-blue-900 mb-3 flex items-center">
                      <TrendingUp className="h-4 w-4 mr-2" />
                      Regression Tasks ({novelMetrics.ml_efficacy.regression_tasks.length})
                    </h4>
                    <div className="space-y-3">
                      {novelMetrics.ml_efficacy.regression_tasks.map((task, idx) => (
                        <div key={idx} className="bg-white p-3 rounded border border-blue-200">
                          <div className="flex justify-between items-start mb-2">
                            <span className="text-sm font-medium text-gray-800">
                              Target: {task.target_column}
                            </span>
                            <span
                              className={`px-2 py-1 rounded text-xs font-bold ${
                                task.interpretation === 'EXCELLENT'
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : task.interpretation === 'GOOD'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-yellow-100 text-yellow-800'
                              }`}
                            >
                              {task.interpretation}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div>
                              <span className="text-gray-600">TRTR R²: </span>
                              <span className="font-bold text-blue-600">
                                {((task.trtr_r2 || 0) * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div>
                              <span className="text-gray-600">TSTR R²: </span>
                              <span className="font-bold text-purple-600">
                                {((task.tstr_r2 || 0) * 100).toFixed(1)}%
                              </span>
                            </div>
                          </div>
                          <div className="mt-2 text-xs">
                            <span className="text-gray-600">Efficacy: </span>
                            <span className={`font-bold ${getScoreColor(task.efficacy_score)}`}>
                              {(task.efficacy_score * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              </div>
              )}
            </div>
          )}

          {/* Feature Importance Preservation */}
          {novelMetrics.feature_importance_preservation && (
            <div className="bg-white border-2 border-indigo-200 rounded-lg p-4">
              <div
                className="flex items-center justify-between cursor-pointer mb-4"
                onClick={() => toggleSection('featureImportance')}
              >
                <div className="flex items-center gap-3">
                  <GitBranch className="h-6 w-6 text-indigo-600" />
                  <h3 className="text-lg font-bold text-gray-900">Feature Importance</h3>
                  <span className="text-2xl font-bold text-indigo-600">
                    {Math.round(novelMetrics.feature_importance_preservation.overall_preservation * 100)}%
                  </span>
                </div>
                {expandedSections.featureImportance ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </div>
              {expandedSections.featureImportance && (
              <div>

              <ProgressBar
                score={novelMetrics.feature_importance_preservation.overall_preservation}
                label="Overall Feature Importance Preservation"
              />

              {novelMetrics.feature_importance_preservation.tasks.length > 0 && (
                <div className="mt-6 space-y-4">
                  {novelMetrics.feature_importance_preservation.tasks.map((task, idx) => (
                    <div key={idx} className="bg-indigo-50 p-4 rounded-lg">
                      <div className="flex justify-between items-start mb-3">
                        <span className="font-medium text-indigo-900">Target: {task.target}</span>
                        <div className="text-right text-sm">
                          <div className="text-gray-600">
                            Rank Correlation:{' '}
                            <span className={`font-bold ${getScoreColor(task.rank_correlation)}`}>
                              {(task.rank_correlation * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="font-semibold text-gray-700 mb-1">Top Features (Real):</p>
                          <ul className="space-y-1">
                            {task.top_features_real.map((feature, i) => (
                              <li key={i} className="flex items-center gap-2">
                                <span className="text-blue-600 font-bold">{i + 1}.</span>
                                <span className="text-gray-800">{feature}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <p className="font-semibold text-gray-700 mb-1">Top Features (Synthetic):</p>
                          <ul className="space-y-1">
                            {task.top_features_synthetic.map((feature, i) => (
                              <li key={i} className="flex items-center gap-2">
                                <span className="text-purple-600 font-bold">{i + 1}.</span>
                                <span className="text-gray-800">{feature}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              </div>
              )}
            </div>
          )}

          {/* Synthetic Detectability */}
          {novelMetrics.synthetic_detectability && (
            <div className="bg-white border-2 border-teal-200 rounded-lg p-4">
              <div
                className="flex items-center justify-between cursor-pointer mb-4"
                onClick={() => toggleSection('detectability')}
              >
                <div className="flex items-center gap-3">
                  <Eye className="h-6 w-6 text-teal-600" />
                  <h3 className="text-lg font-bold text-gray-900">Detectability</h3>
                  <span className="text-2xl font-bold text-teal-600">
                    {(novelMetrics.synthetic_detectability.detectability_score * 100).toFixed(0)}%
                  </span>
                </div>
                {expandedSections.detectability ? (
                  <ChevronUp className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
              </div>
              {expandedSections.detectability && (
              <div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-4">
                <div className="bg-teal-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600 mb-1">Classifier Accuracy</p>
                  <p className="text-3xl font-bold text-teal-600">
                    {(novelMetrics.synthetic_detectability.classifier_accuracy * 100).toFixed(1)}%
                  </p>
                  <p className="text-xs text-gray-600 mt-2">
                    Accuracy of classifier distinguishing real from synthetic (50% = random guessing)
                  </p>
                </div>
                <div className={`p-4 rounded-lg ${colors.bg}`}>
                  <p className="text-sm text-gray-600 mb-1">Detectability Score</p>
                  <p className={`text-3xl font-bold ${colors.text}`}>
                    {(novelMetrics.synthetic_detectability.detectability_score * 100).toFixed(1)}%
                  </p>
                  <p className={`text-xs mt-2 font-medium ${colors.text}`}>
                    {novelMetrics.synthetic_detectability.interpretation}
                  </p>
                </div>
              </div>

              </div>
              )}
            </div>
          )}

          {/* Grid of Other Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Rare Event Preservation */}
            {novelMetrics.rare_event_preservation && (
              <div className="bg-white border-2 border-orange-200 rounded-lg p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Layers className="h-5 w-5 text-orange-600" />
                  <h4 className="font-bold text-gray-900">Rare Events</h4>
                </div>
                <div className="text-center">
                  <div className={`text-4xl font-bold ${getScoreColor(novelMetrics.rare_event_preservation.overall_rare_event_score)}`}>
                    {(novelMetrics.rare_event_preservation.overall_rare_event_score * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            )}

            {/* Multivariate Interactions */}
            {novelMetrics.multivariate_interactions && (
              <div className="bg-white border-2 border-pink-200 rounded-lg p-5">
                <div className="flex items-center gap-2 mb-3">
                  <GitBranch className="h-5 w-5 text-pink-600" />
                  <h4 className="font-bold text-gray-900">3-Way Interactions</h4>
                </div>
                <div className="text-center">
                  <div className={`text-4xl font-bold ${getScoreColor(novelMetrics.multivariate_interactions.overall_interaction_score)}`}>
                    {(novelMetrics.multivariate_interactions.overall_interaction_score * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            )}

            {/* Boundary Preservation */}
            {novelMetrics.boundary_preservation && (
              <div className="bg-white border-2 border-cyan-200 rounded-lg p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Target className="h-5 w-5 text-cyan-600" />
                  <h4 className="font-bold text-gray-900">Decision Boundaries</h4>
                </div>
                <div className="text-center">
                  <div className={`text-4xl font-bold ${getScoreColor(novelMetrics.boundary_preservation.overall_boundary_score)}`}>
                    {(novelMetrics.boundary_preservation.overall_boundary_score * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Manifold Similarity */}
          {novelMetrics.manifold_similarity && (
            <div className="bg-gradient-to-r from-violet-50 to-purple-50 p-5 rounded-lg border border-violet-200">
              <div className="flex items-center gap-2 mb-3">
                <Layers className="h-5 w-5 text-violet-600" />
                <h4 className="font-bold text-gray-900">Data Manifold Similarity</h4>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-600 mb-1">Density Correlation</p>
                  <p className={`text-2xl font-bold ${getScoreColor(novelMetrics.manifold_similarity.density_correlation)}`}>
                    {(novelMetrics.manifold_similarity.density_correlation * 100).toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-600 mb-1">Manifold Score</p>
                  <p className={`text-2xl font-bold ${getScoreColor(novelMetrics.manifold_similarity.manifold_score)}`}>
                    {(novelMetrics.manifold_similarity.manifold_score * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Summary Interpretation */}
          <div className="bg-gray-50 p-4 rounded-lg border-2 border-gray-200">
            <h4
              className="font-bold text-gray-900 mb-3 flex items-center justify-between cursor-pointer"
              onClick={() => toggleSection('summary')}
            >
              <span>What Do These Metrics Mean?</span>
              {expandedSections.summary ? (
                <ChevronUp className="h-4 w-4 text-gray-500" />
              ) : (
                <ChevronDown className="h-4 w-4 text-gray-500" />
              )}
            </h4>
            {expandedSections.summary && (
            <div className="space-y-2 text-sm text-gray-700">
              <p>
                <strong>ML Efficacy:</strong> Tests if ML models trained on synthetic data perform like real-trained models.
              </p>
              <p>
                <strong>Feature Importance:</strong> Ensures important features remain important - preserving ML interpretability.
              </p>
              <p>
                <strong>Rare Events:</strong> Validates that outliers aren't lost - critical for fraud/anomaly detection.
              </p>
              <p>
                <strong>Detectability:</strong> Lower scores = indistinguishable from real - ideal for privacy.
              </p>
            </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
