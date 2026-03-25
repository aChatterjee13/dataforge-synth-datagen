import { Shield, AlertCircle, CheckCircle, Info, Eye, FileWarning, ChevronDown, ChevronUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './Card';
import { useState } from 'react';

interface PrivacyMetrics {
  privacy_score?: number;
  avg_distance_to_closest?: number;
  exact_matches?: number;
  exact_match_rate?: number;
  epsilon?: number;
  delta?: number;
  privacy_level?: string;
  privacy_description?: string;
}

interface PrivacyOverviewProps {
  privacyMetrics: PrivacyMetrics;
  privacyScore: number;
}

export default function PrivacyOverview({ privacyMetrics, privacyScore }: PrivacyOverviewProps) {
  const privacyPercent = Math.round(privacyScore * 100);
  const [expandedSections, setExpandedSections] = useState({
    metrics: true,
    strengths: true,
    considerations: true,
    reidentification: false,
    terminology: false,
    useCases: false,
  });

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Determine privacy level
  const getPrivacyLevel = () => {
    if (privacyPercent >= 85) return { level: 'EXCELLENT', color: 'green', icon: CheckCircle };
    if (privacyPercent >= 70) return { level: 'STRONG', color: 'blue', icon: Shield };
    if (privacyPercent >= 50) return { level: 'MODERATE', color: 'yellow', icon: AlertCircle };
    return { level: 'WEAK', color: 'red', icon: FileWarning };
  };

  const privacyLevel = getPrivacyLevel();
  const PrivacyIcon = privacyLevel.icon;

  // Get color classes
  const getColorClasses = (color: string) => {
    const classes = {
      green: {
        bg: 'bg-green-50',
        border: 'border-green-500',
        text: 'text-green-800',
        badge: 'bg-green-100 text-green-800',
        icon: 'text-green-600'
      },
      blue: {
        bg: 'bg-blue-50',
        border: 'border-blue-500',
        text: 'text-blue-800',
        badge: 'bg-blue-100 text-blue-800',
        icon: 'text-blue-600'
      },
      yellow: {
        bg: 'bg-yellow-50',
        border: 'border-yellow-500',
        text: 'text-yellow-800',
        badge: 'bg-yellow-100 text-yellow-800',
        icon: 'text-yellow-600'
      },
      red: {
        bg: 'bg-red-50',
        border: 'border-red-500',
        text: 'text-red-800',
        badge: 'bg-red-100 text-red-800',
        icon: 'text-red-600'
      }
    };
    return classes[color as keyof typeof classes];
  };

  const colors = getColorClasses(privacyLevel.color);

  // Privacy interpretations
  const getPrivacyInterpretation = () => {
    if (privacyPercent >= 85) {
      return {
        summary: 'Your synthetic data demonstrates excellent privacy protection with very low re-identification risk.',
        details: [
          'Synthetic records are substantially different from original data',
          'Minimal risk of linking synthetic data back to real individuals',
          'Safe for public sharing and external collaboration',
          'Suitable for use in production environments with sensitive data'
        ],
        risks: [
          'Standard best practices still apply (access control, monitoring)',
          'Consider additional anonymization for highly sensitive domains'
        ]
      };
    } else if (privacyPercent >= 70) {
      return {
        summary: 'Your synthetic data shows strong privacy protection with low re-identification risk.',
        details: [
          'Synthetic records are sufficiently different from original data',
          'Low probability of matching synthetic data to real individuals',
          'Appropriate for internal sharing and controlled external use',
          'Good balance between utility and privacy'
        ],
        risks: [
          'Review use cases to ensure alignment with privacy requirements',
          'Implement standard data governance practices',
          'Monitor for potential privacy concerns in production'
        ]
      };
    } else if (privacyPercent >= 50) {
      return {
        summary: 'Your synthetic data provides moderate privacy protection. Additional safeguards may be needed for sensitive applications.',
        details: [
          'Some synthetic records may resemble original data',
          'Moderate risk of re-identification in certain scenarios',
          'Suitable for internal development and testing',
          'May require additional privacy measures for external sharing'
        ],
        risks: [
          'Not recommended for public data release without review',
          'Consider increasing privacy parameters (epsilon, noise)',
          'Evaluate sensitivity of underlying data before deployment',
          'Implement strict access controls and usage policies'
        ]
      };
    } else {
      return {
        summary: 'Your synthetic data shows limited privacy protection. Significant improvements are recommended before deployment.',
        details: [
          'Synthetic records may be too similar to original data',
          'Higher risk of re-identification or attribute disclosure',
          'Limited protection against linkage attacks',
          'Use with caution and only in controlled environments'
        ],
        risks: [
          'DO NOT use for public data sharing or external release',
          'Increase model training epochs for better generalization',
          'Apply stronger differential privacy mechanisms',
          'Consider using CTGAN or TVAE for better privacy-utility tradeoff',
          'Review original data preprocessing and feature engineering'
        ]
      };
    }
  };

  const interpretation = getPrivacyInterpretation();

  // Format metrics for display
  const avgDistance = privacyMetrics.avg_distance_to_closest ?? 0;
  const exactMatches = privacyMetrics.exact_matches ?? 0;
  const exactMatchRate = (privacyMetrics.exact_match_rate ?? 0) * 100;

  // Explain what the metrics mean
  const metricExplanations = {
    privacyScore: {
      title: 'Privacy Score',
      value: `${privacyPercent}%`,
      explanation: 'Composite metric measuring overall privacy protection. Scores above 70% indicate strong privacy guarantees.',
      technical: 'Based on normalized distance to closest record (DCR) in feature space. Higher scores mean synthetic records are more distinct from original data.'
    },
    dcr: {
      title: 'Average Distance to Closest Record (DCR)',
      value: avgDistance.toFixed(3),
      explanation: 'Measures how different synthetic records are from the nearest original record. Higher values indicate better privacy.',
      technical: 'Calculated using normalized Euclidean distance across all numeric features. Values > 2.0 indicate strong separation between synthetic and original data.'
    },
    exactMatches: {
      title: 'Near-Exact Matches',
      value: `${exactMatches} (${exactMatchRate.toFixed(2)}%)`,
      explanation: 'Count of synthetic records that are nearly identical to original records. Lower is better.',
      technical: 'Records with normalized distance < 0.01 are flagged as potential privacy risks. In well-generated synthetic data, this should be near zero.'
    }
  };

  return (
    <Card className="mb-8">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <Shield className={`h-6 w-6 mr-3 ${colors.icon}`} />
            <CardTitle>Privacy Analysis</CardTitle>
          </div>
          <span className={`text-4xl font-bold ${colors.text}`}>{privacyPercent}%</span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Privacy Level Badge */}
          <div className={`p-4 rounded-lg border-l-4 ${colors.bg} ${colors.border}`}>
            <div className="flex items-center gap-3">
              <PrivacyIcon className={`h-6 w-6 ${colors.icon}`} />
              <span className={`px-3 py-1 rounded-full text-sm font-bold ${colors.badge}`}>
                {privacyLevel.level}
              </span>
              <p className={`text-sm ${colors.text} flex-1`}>
                {interpretation.summary}
              </p>
            </div>
          </div>

          {/* Key Privacy Metrics */}
          <div>
            <h3
              className="text-lg font-semibold text-gray-900 mb-4 flex items-center justify-between cursor-pointer hover:bg-gray-50 p-2 rounded transition-colors"
              onClick={() => toggleSection('metrics')}
            >
              <div className="flex items-center">
                <Info className="h-5 w-5 mr-2 text-indigo-600" />
                Privacy Metrics
              </div>
              {expandedSections.metrics ? (
                <ChevronUp className="h-4 w-4 text-gray-500" />
              ) : (
                <ChevronDown className="h-4 w-4 text-gray-500" />
              )}
            </h3>
            {expandedSections.metrics && <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {Object.entries(metricExplanations).map(([key, metric]) => (
                <div key={key} className="bg-white p-5 rounded-lg border-2 border-gray-200 hover:border-indigo-300 transition-colors">
                  <div className="mb-3">
                    <div className="text-sm font-medium text-gray-600 mb-1">{metric.title}</div>
                    <div className="text-3xl font-bold text-indigo-600">{metric.value}</div>
                  </div>
                  <div className="space-y-2">
                    <div className="bg-blue-50 p-3 rounded">
                      <p className="text-xs font-medium text-blue-900 mb-1">What it means:</p>
                      <p className="text-xs text-blue-800">{metric.explanation}</p>
                    </div>
                    <div className="bg-gray-50 p-3 rounded">
                      <p className="text-xs font-medium text-gray-900 mb-1">Technical details:</p>
                      <p className="text-xs text-gray-700">{metric.technical}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>}
          </div>

          {/* Privacy Strengths */}
          <div className="bg-green-50 p-4 rounded-lg border border-green-200">
            <h4
              className="font-semibold text-green-900 mb-3 flex items-center justify-between cursor-pointer"
              onClick={() => toggleSection('strengths')}
            >
              <div className="flex items-center">
                <CheckCircle className="h-5 w-5 mr-2" />
                Privacy Strengths
              </div>
              {expandedSections.strengths ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </h4>
            {expandedSections.strengths && (
            <ul className="space-y-2">
              {interpretation.details.map((detail, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span className="text-sm text-green-800">{detail}</span>
                </li>
              ))}
            </ul>
            )}
          </div>

          {/* Privacy Considerations & Risks */}
          <div className={`${interpretation.risks.length > 2 ? 'bg-orange-50 border-orange-200' : 'bg-blue-50 border-blue-200'} p-4 rounded-lg border`}>
            <h4
              className={`font-semibold mb-3 flex items-center justify-between cursor-pointer ${interpretation.risks.length > 2 ? 'text-orange-900' : 'text-blue-900'}`}
              onClick={() => toggleSection('considerations')}
            >
              <div className="flex items-center">
                <Eye className="h-5 w-5 mr-2" />
                {interpretation.risks.length > 2 ? 'Considerations' : 'Best Practices'}
              </div>
              {expandedSections.considerations ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </h4>
            {expandedSections.considerations && (
            <ul className="space-y-2">
              {interpretation.risks.map((risk, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className={`mt-0.5 ${interpretation.risks.length > 2 ? 'text-orange-600' : 'text-blue-600'}`}>
                    {interpretation.risks.length > 2 ? '⚠' : '→'}
                  </span>
                  <span className={`text-sm ${interpretation.risks.length > 2 ? 'text-orange-800' : 'text-blue-800'}`}>
                    {risk}
                  </span>
                </li>
              ))}
            </ul>
            )}
          </div>

          {/* Understanding Re-identification Risk - Collapsed by default */}
          <div className="bg-gradient-to-r from-purple-50 to-indigo-50 p-4 rounded-lg border border-purple-200">
            <h4
              className="font-semibold text-purple-900 mb-3 flex items-center justify-between cursor-pointer"
              onClick={() => toggleSection('reidentification')}
            >
              <div className="flex items-center">
                <AlertCircle className="h-5 w-5 mr-2 text-purple-600" />
                Re-identification Risk
              </div>
              {expandedSections.reidentification ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </h4>
            {expandedSections.reidentification && (
            <div className="space-y-3 text-sm text-purple-900">
              <p>
                <strong>What is re-identification?</strong> The process of matching synthetic data records back to real individuals in the original dataset.
              </p>
              <p>
                <strong>How we measure it:</strong> We calculate the distance between each synthetic record and its nearest neighbor in the original dataset.
                Larger distances indicate lower re-identification risk because synthetic records are statistically distinct from any real individual.
              </p>
              <p>
                <strong>Your result:</strong> With a privacy score of <strong>{privacyPercent}%</strong> and average DCR of <strong>{avgDistance.toFixed(3)}</strong>,
                {privacyPercent >= 70
                  ? ' your synthetic data provides strong protection against re-identification attacks.'
                  : privacyPercent >= 50
                  ? ' your synthetic data provides moderate protection, suitable for internal use with appropriate safeguards.'
                  : ' additional privacy measures are recommended before deploying this synthetic data.'}
              </p>
              {exactMatches > 0 && (
                <div className="bg-yellow-100 p-3 rounded border border-yellow-300 mt-3">
                  <p className="text-yellow-900">
                    <strong>⚠ Note:</strong> {exactMatches} synthetic record{exactMatches > 1 ? 's are' : ' is'} nearly identical to original records
                    ({exactMatchRate.toFixed(2)}%). This may indicate potential privacy leakage. Consider increasing model training epochs or applying stronger
                    differential privacy mechanisms.
                  </p>
                </div>
              )}
            </div>
            )}
          </div>

          {/* Privacy Terminology - Collapsed by default */}
          <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
            <h4
              className="font-semibold text-gray-900 mb-4 flex items-center justify-between cursor-pointer"
              onClick={() => toggleSection('terminology')}
            >
              <span>Privacy Terminology</span>
              {expandedSections.terminology ? (
                <ChevronUp className="h-4 w-4 text-gray-500" />
              ) : (
                <ChevronDown className="h-4 w-4 text-gray-500" />
              )}
            </h4>
            {expandedSections.terminology && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <p className="font-medium text-gray-900 mb-1">Distance to Closest Record (DCR)</p>
                <p className="text-gray-700">Minimum Euclidean distance between a synthetic record and any original record in normalized feature space.</p>
              </div>
              <div>
                <p className="font-medium text-gray-900 mb-1">Re-identification Risk</p>
                <p className="text-gray-700">Probability that a synthetic record can be matched back to a specific individual in the original dataset.</p>
              </div>
              <div>
                <p className="font-medium text-gray-900 mb-1">Attribute Disclosure</p>
                <p className="text-gray-700">Risk of inferring sensitive attributes about individuals even without direct re-identification.</p>
              </div>
              <div>
                <p className="font-medium text-gray-900 mb-1">Differential Privacy (DP)</p>
                <p className="text-gray-700">Mathematical privacy guarantee ensuring individual records cannot be distinguished in the synthetic data.</p>
              </div>
            </div>
            )}
          </div>

          {/* Recommended Use Cases Based on Privacy Level - Collapsed by default */}
          <div className="border-t-2 border-gray-200 pt-4">
            <h4
              className="font-semibold text-gray-900 mb-4 text-lg flex items-center justify-between cursor-pointer"
              onClick={() => toggleSection('useCases')}
            >
              <span>Appropriate Use Cases</span>
              {expandedSections.useCases ? (
                <ChevronUp className="h-4 w-4 text-gray-500" />
              ) : (
                <ChevronDown className="h-4 w-4 text-gray-500" />
              )}
            </h4>
            {expandedSections.useCases && (
              privacyPercent >= 85 ? (
              <div className="space-y-2 text-sm">
                <p className="flex items-start gap-2">
                  <CheckCircle className="h-4 w-4 mt-0.5 text-green-600" />
                  <span>✓ Public data sharing and open datasets</span>
                </p>
                <p className="flex items-start gap-2">
                  <CheckCircle className="h-4 w-4 mt-0.5 text-green-600" />
                  <span>✓ External collaboration with third parties</span>
                </p>
                <p className="flex items-start gap-2">
                  <CheckCircle className="h-4 w-4 mt-0.5 text-green-600" />
                  <span>✓ Production ML model training and validation</span>
                </p>
                <p className="flex items-start gap-2">
                  <CheckCircle className="h-4 w-4 mt-0.5 text-green-600" />
                  <span>✓ Publishing in research papers and public forums</span>
                </p>
              </div>
            ) : privacyPercent >= 70 ? (
              <div className="space-y-2 text-sm">
                <p className="flex items-start gap-2">
                  <CheckCircle className="h-4 w-4 mt-0.5 text-blue-600" />
                  <span>✓ Internal development and testing environments</span>
                </p>
                <p className="flex items-start gap-2">
                  <CheckCircle className="h-4 w-4 mt-0.5 text-blue-600" />
                  <span>✓ ML model development with access controls</span>
                </p>
                <p className="flex items-start gap-2">
                  <CheckCircle className="h-4 w-4 mt-0.5 text-blue-600" />
                  <span>✓ Controlled external sharing with NDAs</span>
                </p>
                <p className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 mt-0.5 text-yellow-600" />
                  <span>⚠ Public sharing (requires additional review)</span>
                </p>
              </div>
            ) : privacyPercent >= 50 ? (
              <div className="space-y-2 text-sm">
                <p className="flex items-start gap-2">
                  <CheckCircle className="h-4 w-4 mt-0.5 text-yellow-600" />
                  <span>✓ Internal testing and development only</span>
                </p>
                <p className="flex items-start gap-2">
                  <CheckCircle className="h-4 w-4 mt-0.5 text-yellow-600" />
                  <span>✓ Algorithm prototyping and experimentation</span>
                </p>
                <p className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 mt-0.5 text-orange-600" />
                  <span>⚠ External sharing (NOT recommended without additional safeguards)</span>
                </p>
                <p className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 mt-0.5 text-orange-600" />
                  <span>⚠ Production use (requires strict access controls)</span>
                </p>
              </div>
            ) : (
              <div className="space-y-2 text-sm">
                <p className="flex items-start gap-2">
                  <FileWarning className="h-4 w-4 mt-0.5 text-red-600" />
                  <span>✗ Public data sharing - NOT RECOMMENDED</span>
                </p>
                <p className="flex items-start gap-2">
                  <FileWarning className="h-4 w-4 mt-0.5 text-red-600" />
                  <span>✗ External collaboration - NOT RECOMMENDED</span>
                </p>
                <p className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 mt-0.5 text-orange-600" />
                  <span>⚠ Internal testing only - with extreme caution and limited access</span>
                </p>
                <p className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 mt-0.5 text-orange-600" />
                  <span>⚠ Recommend regenerating with stronger privacy parameters</span>
                </p>
              </div>
            )
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
