import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Settings, Play, Brain, CheckSquare, Square, Info, Sparkles, Lightbulb, ChevronDown, ChevronUp, Columns, Filter, Save, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/Card';
import { Button } from '../components/Button';
import TimeGANConfig from '../components/TimeGANConfig';
import ConditionBuilder from '../components/ConditionBuilder';
import { generateSynthetic, listPresets, savePreset, getModelRecommendation } from '../services/api';
import { getApiErrorMessage } from '../lib/utils';
import { ModelType, UseCase, SmoteStrategy, type GenerationConfig, type PotentialTarget, type TargetVariable, type TimeSeriesInfo, type Preset, type ModelRecommendation, type ColumnConfig, type GenerationCondition } from '../types';

// ============================================================================
// MODEL INFO METADATA
// ============================================================================

interface ModelInfo {
  value: ModelType;
  label: string;
  description: string;
  category: 'statistical' | 'transformer_diffusion' | 'timeseries' | 'privacy' | 'llm';
  trainingTime: 'Fast' | 'Moderate' | 'Slow' | 'Instant';
  qualityLevel: 'Moderate' | 'High' | 'Very High' | 'State-of-Art';
  useCases: ('ml_training' | 'prototyping')[];
  isNew: boolean;
  showEpochs: boolean;
}

const MODEL_INFO: ModelInfo[] = [
  {
    value: ModelType.AUTO, label: 'Auto-Detect', description: 'Automatically selects the best model for your data',
    category: 'statistical', trainingTime: 'Moderate', qualityLevel: 'High',
    useCases: ['ml_training', 'prototyping'], isNew: false, showEpochs: true,
  },
  {
    value: ModelType.CTGAN, label: 'CTGAN', description: 'Conditional GAN for tabular data with complex distributions',
    category: 'statistical', trainingTime: 'Moderate', qualityLevel: 'High',
    useCases: ['ml_training'], isNew: false, showEpochs: true,
  },
  {
    value: ModelType.COPULA_GAN, label: 'CopulaGAN', description: 'Combines copulas with GANs for better correlation modeling',
    category: 'statistical', trainingTime: 'Moderate', qualityLevel: 'High',
    useCases: ['ml_training'], isNew: true, showEpochs: true,
  },
  {
    value: ModelType.GAUSSIAN_COPULA, label: 'Gaussian Copula', description: 'Fastest model, great for small datasets and quick previews',
    category: 'statistical', trainingTime: 'Fast', qualityLevel: 'Moderate',
    useCases: ['ml_training'], isNew: false, showEpochs: false,
  },
  {
    value: ModelType.TVAE, label: 'TVAE', description: 'Variational autoencoder optimized for mixed data types',
    category: 'statistical', trainingTime: 'Moderate', qualityLevel: 'High',
    useCases: ['ml_training'], isNew: false, showEpochs: true,
  },
  {
    value: ModelType.BAYESIAN_NETWORK, label: 'Bayesian Network', description: 'Interpretable model that captures causal relationships',
    category: 'statistical', trainingTime: 'Fast', qualityLevel: 'Moderate',
    useCases: ['ml_training'], isNew: true, showEpochs: false,
  },
  {
    value: ModelType.TAB_DDPM, label: 'TabDDPM', description: 'Diffusion model delivering state-of-the-art fidelity',
    category: 'transformer_diffusion', trainingTime: 'Slow', qualityLevel: 'State-of-Art',
    useCases: ['ml_training'], isNew: true, showEpochs: true,
  },
  {
    value: ModelType.REALTABFORMER, label: 'REaLTabFormer', description: 'GPT-2 based transformer for tabular generation',
    category: 'transformer_diffusion', trainingTime: 'Slow', qualityLevel: 'Very High',
    useCases: ['ml_training'], isNew: true, showEpochs: true,
  },
  {
    value: ModelType.CTAB_GAN_PLUS, label: 'CTAB-GAN+', description: 'GAN optimized for downstream ML task utility',
    category: 'transformer_diffusion', trainingTime: 'Slow', qualityLevel: 'Very High',
    useCases: ['ml_training'], isNew: true, showEpochs: true,
  },
  {
    value: ModelType.TIMEGAN, label: 'TimeGAN', description: 'Preserves temporal dynamics in sequential data',
    category: 'timeseries', trainingTime: 'Slow', qualityLevel: 'High',
    useCases: ['ml_training'], isNew: false, showEpochs: true,
  },
  {
    value: ModelType.DGAN, label: 'DGAN (DoppelGANger)', description: 'Time-series + metadata generation for large datasets',
    category: 'timeseries', trainingTime: 'Slow', qualityLevel: 'High',
    useCases: ['ml_training'], isNew: true, showEpochs: true,
  },
  {
    value: ModelType.DP_CTGAN, label: 'DP-CTGAN', description: 'Differential privacy baked into GAN training',
    category: 'privacy', trainingTime: 'Moderate', qualityLevel: 'Moderate',
    useCases: ['ml_training'], isNew: true, showEpochs: true,
  },
  {
    value: ModelType.LLM_ROW_GEN, label: 'LLM Row Generator', description: 'GPT-based generation for fast, semantically coherent data',
    category: 'llm', trainingTime: 'Fast', qualityLevel: 'Moderate',
    useCases: ['prototyping'], isNew: true, showEpochs: false,
  },
];

const CATEGORY_LABELS: Record<string, string> = {
  statistical: 'Statistical',
  transformer_diffusion: 'Transformer / Diffusion',
  timeseries: 'Time-Series',
  privacy: 'Privacy-Native',
  llm: 'LLM',
};

const SPEED_COLORS: Record<string, string> = {
  Fast: 'bg-green-100 text-green-800',
  Moderate: 'bg-yellow-100 text-yellow-800',
  Slow: 'bg-red-100 text-red-800',
  Instant: 'bg-blue-100 text-blue-800',
};

const QUALITY_COLORS: Record<string, string> = {
  Moderate: 'bg-gray-100 text-gray-800',
  High: 'bg-blue-100 text-blue-800',
  'Very High': 'bg-purple-100 text-purple-800',
  'State-of-Art': 'bg-amber-100 text-amber-800',
};

function getTimeEstimate(model: ModelType, epochs: number, numRows: number): string {
  if (model === ModelType.LLM_ROW_GEN) {
    const batches = Math.ceil(numRows / 50);
    return `~${batches * 5}-${batches * 15} seconds (${batches} API calls)`;
  }
  if (model === ModelType.GAUSSIAN_COPULA || model === ModelType.BAYESIAN_NETWORK) {
    return '< 30 seconds';
  }
  if (model === ModelType.TAB_DDPM || model === ModelType.REALTABFORMER || model === ModelType.CTAB_GAN_PLUS) {
    return `${Math.ceil(epochs / 50)} - ${Math.ceil(epochs / 20)} minutes`;
  }
  return `${Math.ceil(epochs / 100)} - ${Math.ceil(epochs / 50)} minutes`;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function Configure() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [config, setConfig] = useState<GenerationConfig>({
    model_type: ModelType.AUTO,
    num_rows: 1000,
    epochs: 300,
    batch_size: 500,
    sequence_length: 24,
    datetime_column: '',
    use_case: UseCase.ML_TRAINING,
  });

  // Use Case
  const [useCase, setUseCase] = useState<string>(UseCase.ML_TRAINING);

  // ML Target Variable Selection
  const [potentialTargets, setPotentialTargets] = useState<{
    classification: PotentialTarget[];
    regression: PotentialTarget[];
  } | null>(null);
  const [selectedTargets, setSelectedTargets] = useState<TargetVariable[]>([]);

  // Time-Series Detection
  const [timeseriesInfo, setTimeseriesInfo] = useState<TimeSeriesInfo | null>(null);
  const [isTimeSeries, setIsTimeSeries] = useState(false);

  // Presets (Feature 5)
  const [presets, setPresets] = useState<Preset[]>([]);
  const [savePresetName, setSavePresetName] = useState('');
  const [showSavePreset, setShowSavePreset] = useState(false);

  // Model Recommendation (Feature 6)
  const [recommendation, setRecommendation] = useState<ModelRecommendation | null>(null);

  // Column Config (Feature 7)
  const [columnConfigs, setColumnConfigs] = useState<ColumnConfig[]>([]);
  const [columnTypes, setColumnTypes] = useState<Record<string, string>>({});
  const [showColumnConfig, setShowColumnConfig] = useState(false);

  // Conditional Generation (Feature 10)
  const [conditions, setConditions] = useState<GenerationCondition[]>([]);
  const [showConditions, setShowConditions] = useState(false);

  // SMOTE
  const [showSmote, setShowSmote] = useState(false);

  // Load potential targets and time-series info from sessionStorage
  useEffect(() => {
    if (jobId) {
      const storedTargets = sessionStorage.getItem(`targets_${jobId}`);
      if (storedTargets) {
        try {
          setPotentialTargets(JSON.parse(storedTargets));
        } catch (err) {
          console.error('Failed to parse stored targets:', err);
        }
      }

      const storedTimeseries = sessionStorage.getItem(`timeseries_${jobId}`);
      if (storedTimeseries) {
        try {
          const tsInfo: TimeSeriesInfo = JSON.parse(storedTimeseries);
          setTimeseriesInfo(tsInfo);
          setIsTimeSeries(true);
          if (tsInfo.suggested_datetime_col) {
            setConfig(prev => ({
              ...prev,
              datetime_column: tsInfo.suggested_datetime_col || '',
              model_type: ModelType.TIMEGAN,
            }));
          }
        } catch (err) {
          console.error('Failed to parse stored time-series info:', err);
        }
      }

      const storedCols = sessionStorage.getItem(`column_types_${jobId}`);
      if (storedCols) {
        try {
          setColumnTypes(JSON.parse(storedCols));
        } catch {}
      }

      getModelRecommendation(jobId, useCase).then(setRecommendation).catch(() => {});
      listPresets().then(setPresets).catch(() => {});
    }
  }, [jobId]);

  // Re-fetch recommendation when use case changes
  useEffect(() => {
    if (jobId) {
      getModelRecommendation(jobId, useCase).then(setRecommendation).catch(() => {});
    }
  }, [useCase, jobId]);

  const handleUseCaseChange = (newUseCase: string) => {
    setUseCase(newUseCase);
    setConfig(prev => ({
      ...prev,
      use_case: newUseCase as any,
    }));
    if (newUseCase === UseCase.PROTOTYPING) {
      setConfig(prev => ({ ...prev, model_type: ModelType.LLM_ROW_GEN }));
    } else if (config.model_type === ModelType.LLM_ROW_GEN) {
      setConfig(prev => ({ ...prev, model_type: ModelType.AUTO }));
    }
  };

  const toggleTarget = (name: string, taskType: 'classification' | 'regression') => {
    const existing = selectedTargets.find(t => t.column_name === name);
    if (existing) {
      setSelectedTargets(prev => prev.filter(t => t.column_name !== name));
    } else {
      setSelectedTargets(prev => [...prev, { column_name: name, task_type: taskType, enabled: true }]);
    }
  };

  // Filter models based on use case and time-series
  const getVisibleModels = () => {
    return MODEL_INFO.filter(m => {
      if (useCase === UseCase.PROTOTYPING && !m.useCases.includes('prototyping') && m.value !== ModelType.AUTO) {
        return false;
      }
      if (useCase === UseCase.ML_TRAINING && m.category === 'llm') {
        return false;
      }
      if (m.category === 'timeseries' && !isTimeSeries && m.value !== ModelType.TIMEGAN) {
        // Show TimeGAN always (user might know), hide DGAN unless time-series detected
        return false;
      }
      return true;
    });
  };

  // Group visible models by category
  const getGroupedModels = () => {
    const visible = getVisibleModels();
    const groups: Record<string, ModelInfo[]> = {};
    for (const m of visible) {
      const cat = m.category;
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(m);
    }
    return groups;
  };

  const selectedModelInfo = MODEL_INFO.find(m => m.value === config.model_type);
  const showEpochsBatchSize = selectedModelInfo?.showEpochs !== false;

  const handleGenerate = async () => {
    if (!jobId) return;
    setGenerating(true);
    setError(null);
    try {
      const finalConfig: GenerationConfig = {
        ...config,
        ml_target_variables: selectedTargets.length > 0 ? selectedTargets : undefined,
        column_configs: columnConfigs.length > 0 ? columnConfigs : undefined,
        conditions: conditions.length > 0 ? conditions : undefined,
      };
      await generateSynthetic(jobId, finalConfig);
      navigate(`/generate/${jobId}`);
    } catch (err: unknown) {
      setError(getApiErrorMessage(err));
      setGenerating(false);
    }
  };

  // Get categorical/low-cardinality columns for SMOTE target
  const smoteTargetColumns = Object.entries(columnTypes)
    .filter(([_, type]) => type === 'object' || type === 'category' || type === 'bool')
    .map(([col]) => col);

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Configure Generation</h1>
        <p className="text-gray-600">Customize your synthetic data generation parameters</p>
      </div>

      {/* ================================================================
          USE CASE SELECTOR
          ================================================================ */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>What is your use case?</CardTitle>
          <CardDescription>This determines which models are recommended and available</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div
              onClick={() => handleUseCaseChange(UseCase.ML_TRAINING)}
              className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                useCase === UseCase.ML_TRAINING
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-blue-300'
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <Brain className="h-5 w-5 text-blue-600" />
                <span className="font-semibold text-gray-900">ML Training / Testing</span>
              </div>
              <p className="text-xs text-gray-600">
                Statistical fidelity is critical. Models preserve distributions, correlations, and relationships.
              </p>
            </div>
            <div
              onClick={() => handleUseCaseChange(UseCase.PROTOTYPING)}
              className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                useCase === UseCase.PROTOTYPING
                  ? 'border-purple-500 bg-purple-50'
                  : 'border-gray-200 hover:border-purple-300'
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="h-5 w-5 text-purple-600" />
                <span className="font-semibold text-gray-900">Prototyping / Demo Data</span>
              </div>
              <p className="text-xs text-gray-600">
                Semantic accuracy is sufficient. LLM generates realistic-looking data faster.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ================================================================
          MODEL RECOMMENDATION
          ================================================================ */}
      {recommendation && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center">
              <Lightbulb className="h-5 w-5 mr-2 text-yellow-500" />
              Model Recommendation
              <span className="ml-2 text-xs px-2 py-1 bg-yellow-100 text-yellow-800 rounded">
                {Math.round(recommendation.confidence * 100)}% confidence
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between mb-3">
              <div>
                <span className="text-lg font-bold text-gray-900 uppercase">{recommendation.recommended_model}</span>
                <div className="mt-1 space-y-1">
                  {recommendation.reasons.map((r, i) => (
                    <div key={i} className="text-sm text-gray-600 flex items-start">
                      <Sparkles className="h-3 w-3 text-yellow-500 mr-1.5 mt-0.5 flex-shrink-0" />
                      {r}
                    </div>
                  ))}
                </div>
              </div>
              <Button
                size="sm"
                onClick={() => setConfig(prev => ({ ...prev, model_type: recommendation.recommended_model as ModelType }))}
              >
                Apply
              </Button>
            </div>
            {recommendation.alternatives.length > 0 && (
              <div className="text-xs text-gray-500 border-t pt-2 mt-2">
                <span className="font-medium">Alternatives: </span>
                {recommendation.alternatives.map((a, i) => (
                  <span key={i}>{a.model} ({a.reason}){i < recommendation.alternatives.length - 1 ? ' | ' : ''}</span>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ================================================================
          MODEL SELECTION (Grouped Card Grid)
          ================================================================ */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center">
            <Settings className="h-6 w-6 mr-2" />
            Model Selection
          </CardTitle>
          <CardDescription>Choose a synthesis model for your data</CardDescription>
        </CardHeader>
        <CardContent>
          {Object.entries(getGroupedModels()).map(([category, models]) => (
            <div key={category} className="mb-4 last:mb-0">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                {CATEGORY_LABELS[category] || category}
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {models.map((m) => (
                  <div
                    key={m.value}
                    onClick={() => setConfig(prev => ({ ...prev, model_type: m.value }))}
                    className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                      config.model_type === m.value
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm text-gray-900">{m.label}</span>
                      {m.isNew && (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 bg-emerald-100 text-emerald-700 rounded">NEW</span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mb-2">{m.description}</p>
                    <div className="flex gap-1.5">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${SPEED_COLORS[m.trainingTime]}`}>
                        {m.trainingTime}
                      </span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${QUALITY_COLORS[m.qualityLevel]}`}>
                        {m.qualityLevel}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* ================================================================
          GENERATION PARAMETERS
          ================================================================ */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <Settings className="h-6 w-6 mr-2" />
            Generation Parameters
          </CardTitle>
          <CardDescription>
            Adjust the settings below to control the synthetic data generation process
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Preset Dropdown (Feature 5) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Load Preset
            </label>
            <div className="flex gap-2">
              <select
                onChange={(e) => {
                  const preset = presets.find(p => p.id === parseInt(e.target.value));
                  if (preset) {
                    const c = preset.config as Record<string, unknown>;
                    setConfig(prev => ({
                      ...prev,
                      model_type: (c.model_type as ModelType) || prev.model_type,
                      num_rows: (c.num_rows as number) || prev.num_rows,
                      epochs: (c.epochs as number) || prev.epochs,
                      batch_size: (c.batch_size as number) || prev.batch_size,
                      enable_privacy: (c.enable_privacy as boolean) || false,
                      privacy_epsilon: (c.privacy_epsilon as number) || 1.0,
                    }));
                    if (c.use_case) {
                      setUseCase(c.use_case as string);
                    }
                  }
                }}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                defaultValue=""
              >
                <option value="" disabled>Select a preset...</option>
                {presets.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.name} {p.is_builtin ? '(built-in)' : ''} {p.description ? `- ${p.description}` : ''}
                  </option>
                ))}
              </select>
              <Button variant="outline" size="sm" onClick={() => setShowSavePreset(!showSavePreset)}>
                <Save className="h-4 w-4" />
              </Button>
            </div>
            {showSavePreset && (
              <div className="mt-2 flex gap-2">
                <input
                  type="text"
                  placeholder="Preset name"
                  value={savePresetName}
                  onChange={(e) => setSavePresetName(e.target.value)}
                  className="flex-1 px-3 py-1.5 border border-gray-300 rounded-md text-sm"
                />
                <Button
                  size="sm"
                  onClick={async () => {
                    if (!savePresetName.trim()) return;
                    try {
                      await savePreset(savePresetName, '', config as unknown as Record<string, unknown>);
                      const updated = await listPresets();
                      setPresets(updated);
                      setSavePresetName('');
                      setShowSavePreset(false);
                    } catch (err) {
                      console.error('Failed to save preset:', err);
                    }
                  }}
                >
                  Save
                </Button>
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Number of Rows to Generate
            </label>
            <input
              type="number"
              min="100"
              max="100000"
              step="100"
              value={config.num_rows}
              onChange={(e) => setConfig({ ...config, num_rows: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Generate between 100 and 100,000 synthetic rows
            </p>
          </div>

          {showEpochsBatchSize && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Training Epochs
                </label>
                <input
                  type="number"
                  min="50"
                  max="1000"
                  step="50"
                  value={config.epochs}
                  onChange={(e) => setConfig({ ...config, epochs: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  More epochs = better quality but longer training time (recommended: 300)
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Batch Size
                </label>
                <input
                  type="number"
                  min="100"
                  max="2000"
                  step="100"
                  value={config.batch_size}
                  onChange={(e) => setConfig({ ...config, batch_size: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Affects training speed and memory usage (recommended: 500)
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* ================================================================
          LLM CONFIGURATION (visible only when LLM_ROW_GEN selected)
          ================================================================ */}
      {config.model_type === ModelType.LLM_ROW_GEN && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center">
              <Sparkles className="h-5 w-5 mr-2 text-purple-600" />
              LLM Configuration
            </CardTitle>
            <CardDescription>Configure the LLM-based row generator</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">LLM Model</label>
              <select
                value={config.gpt_model || 'gpt-4o-mini'}
                onChange={(e) => setConfig({ ...config, gpt_model: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="gpt-4o-mini">GPT-4o-mini (Fastest, cheapest)</option>
                <option value="gpt-4o">GPT-4o (Best quality)</option>
                <option value="gpt-4">GPT-4 (Legacy)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rows per Batch: {config.llm_row_gen_batch_size || 50}
              </label>
              <input
                type="range"
                min="10"
                max="200"
                step="10"
                value={config.llm_row_gen_batch_size || 50}
                onChange={(e) => setConfig({ ...config, llm_row_gen_batch_size: parseInt(e.target.value) })}
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">
                Each batch makes one API call. Estimated: ~{Math.ceil(config.num_rows / (config.llm_row_gen_batch_size || 50))} API calls for {config.num_rows} rows
              </p>
            </div>
            <div className="bg-purple-50 p-3 rounded-lg border border-purple-200">
              <div className="flex items-start gap-2">
                <Info className="h-4 w-4 text-purple-600 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-purple-800">
                  Requires an OpenAI API key set in Settings or as OPENAI_API_KEY environment variable.
                  LLM-generated data is suitable for prototyping and demos but does not preserve statistical properties for ML training.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ================================================================
          SMOTE AUGMENTATION (Collapsible, opt-in)
          ================================================================ */}
      {Object.keys(columnTypes).length > 0 && smoteTargetColumns.length > 0 && (
        <Card className="mt-6">
          <CardHeader
            className="cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => setShowSmote(!showSmote)}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center">
                <AlertTriangle className="h-5 w-5 mr-2 text-orange-500" />
                SMOTE Oversampling
                <span className="ml-2 text-xs font-normal px-2 py-1 bg-orange-100 text-orange-800 rounded">Optional</span>
              </CardTitle>
              {showSmote ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
            </div>
            <CardDescription>Post-processing to balance class distributions (use with caution)</CardDescription>
          </CardHeader>
          {showSmote && (
            <CardContent className="space-y-4">
              {/* Warning Banner */}
              <div className="bg-orange-50 p-4 rounded-lg border border-orange-200">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-5 w-5 text-orange-600 mt-0.5 flex-shrink-0" />
                  <div className="text-sm text-orange-900">
                    <p className="font-medium mb-1">Use with caution</p>
                    <p>
                      SMOTE interpolates between existing samples to balance classes. This may distort complex statistical
                      relationships and class distribution patterns. Only enable if class imbalance is your primary concern.
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="enable-smote"
                  checked={config.enable_smote || false}
                  onChange={(e) => setConfig({ ...config, enable_smote: e.target.checked })}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <label htmlFor="enable-smote" className="text-sm font-medium text-gray-700">
                  Enable SMOTE post-processing
                </label>
              </div>

              {config.enable_smote && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Target Column</label>
                    <select
                      value={config.smote_target_column || ''}
                      onChange={(e) => setConfig({ ...config, smote_target_column: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="" disabled>Select target column...</option>
                      {smoteTargetColumns.map(col => (
                        <option key={col} value={col}>{col}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Sampling Strategy</label>
                    <select
                      value={config.smote_strategy || SmoteStrategy.MINORITY}
                      onChange={(e) => setConfig({ ...config, smote_strategy: e.target.value as any })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value={SmoteStrategy.MINORITY}>Minority (oversample smallest class)</option>
                      <option value={SmoteStrategy.NOT_MINORITY}>Not Minority (oversample all except largest)</option>
                      <option value={SmoteStrategy.NOT_MAJORITY}>Not Majority (oversample all except majority)</option>
                      <option value={SmoteStrategy.ALL}>All (balance all classes equally)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      k-Neighbors: {config.smote_k_neighbors || 5}
                    </label>
                    <input
                      type="range"
                      min="1"
                      max="20"
                      value={config.smote_k_neighbors || 5}
                      onChange={(e) => setConfig({ ...config, smote_k_neighbors: parseInt(e.target.value) })}
                      className="w-full"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Number of nearest neighbors for interpolation (lower = more conservative)
                    </p>
                  </div>
                </>
              )}
            </CardContent>
          )}
        </Card>
      )}

      {/* ================================================================
          ML EFFICACY EVALUATION
          ================================================================ */}
      {potentialTargets && (potentialTargets.classification.length > 0 || potentialTargets.regression.length > 0) && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center">
              <Brain className="h-6 w-6 mr-2 text-purple-600" />
              ML Efficacy Evaluation
              <span className="ml-2 text-xs font-normal px-2 py-1 bg-purple-100 text-purple-800 rounded">Optional</span>
            </CardTitle>
            <CardDescription>
              Select target variables to evaluate how well ML models perform on synthetic data compared to real data
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {potentialTargets.classification.length > 0 && (
              <div>
                <h3 className="font-semibold text-gray-900 mb-3 flex items-center">
                  <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                  Classification Targets
                </h3>
                <div className="space-y-2">
                  {potentialTargets.classification.map((target) => {
                    const isSelected = selectedTargets.some(t => t.column_name === target.name);
                    return (
                      <div
                        key={target.name}
                        onClick={() => toggleTarget(target.name, 'classification')}
                        className={`flex items-start gap-3 p-3 border-2 rounded-lg cursor-pointer transition-all ${
                          isSelected
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50/50'
                        }`}
                      >
                        {isSelected ? (
                          <CheckSquare className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                        ) : (
                          <Square className="h-5 w-5 text-gray-400 mt-0.5 flex-shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-medium text-gray-900">{target.name}</span>
                            <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-800 rounded">{target.reason}</span>
                          </div>
                          <div className="text-xs text-gray-600 mt-1">
                            {target.unique_values} {target.unique_values === 2 ? 'class' : 'classes'} • {target.null_percentage}% missing
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {potentialTargets.regression.length > 0 && (
              <div>
                <h3 className="font-semibold text-gray-900 mb-3 flex items-center">
                  <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                  Regression Targets
                </h3>
                <div className="space-y-2">
                  {potentialTargets.regression.map((target) => {
                    const isSelected = selectedTargets.some(t => t.column_name === target.name);
                    return (
                      <div
                        key={target.name}
                        onClick={() => toggleTarget(target.name, 'regression')}
                        className={`flex items-start gap-3 p-3 border-2 rounded-lg cursor-pointer transition-all ${
                          isSelected
                            ? 'border-green-500 bg-green-50'
                            : 'border-gray-200 hover:border-green-300 hover:bg-green-50/50'
                        }`}
                      >
                        {isSelected ? (
                          <CheckSquare className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                        ) : (
                          <Square className="h-5 w-5 text-gray-400 mt-0.5 flex-shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-medium text-gray-900">{target.name}</span>
                            <span className="text-xs px-2 py-0.5 bg-green-100 text-green-800 rounded">Continuous</span>
                          </div>
                          <div className="text-xs text-gray-600 mt-1">
                            {target.unique_values.toLocaleString()} unique values • {target.null_percentage}% missing
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
              <div className="flex items-start gap-2">
                <Info className="h-5 w-5 text-purple-600 mt-0.5 flex-shrink-0" />
                <div className="text-sm text-purple-900">
                  <p className="font-medium mb-1">What is ML Efficacy?</p>
                  <p>
                    We train ML models (Random Forest) on both real and synthetic data, then test on real data.
                    <strong> TSTR efficacy</strong> (Train Synthetic, Test Real) shows how well models trained on synthetic data perform.
                    High efficacy (&gt;80%) means your synthetic data is production-ready for ML training.
                  </p>
                </div>
              </div>
            </div>

            {selectedTargets.length > 0 && (
              <div className="text-sm font-medium text-purple-800 bg-purple-50 px-4 py-2 rounded-lg border border-purple-200">
                {selectedTargets.length} target variable{selectedTargets.length > 1 ? 's' : ''} selected for ML efficacy evaluation
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ================================================================
          TIMEGAN / DGAN CONFIGURATION
          ================================================================ */}
      {(isTimeSeries || config.model_type === ModelType.TIMEGAN || config.model_type === ModelType.DGAN) && timeseriesInfo && (
        <div className="mt-6">
          <TimeGANConfig
            timeseriesInfo={timeseriesInfo}
            sequenceLength={config.sequence_length || 24}
            datetimeColumn={config.datetime_column || ''}
            onSequenceLengthChange={(value) => setConfig({ ...config, sequence_length: value })}
            onDatetimeColumnChange={(value) => setConfig({ ...config, datetime_column: value })}
          />
        </div>
      )}

      {/* ================================================================
          COLUMN CONFIGURATION
          ================================================================ */}
      {Object.keys(columnTypes).length > 0 && (
        <Card className="mt-6">
          <CardHeader
            className="cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => setShowColumnConfig(!showColumnConfig)}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center">
                <Columns className="h-5 w-5 mr-2 text-indigo-600" />
                Column Configuration
                <span className="ml-2 text-xs font-normal px-2 py-1 bg-indigo-100 text-indigo-800 rounded">Optional</span>
              </CardTitle>
              {showColumnConfig ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
            </div>
            <CardDescription>Configure how each column is handled during generation</CardDescription>
          </CardHeader>
          {showColumnConfig && (
            <CardContent>
              <div className="space-y-2">
                {Object.entries(columnTypes).map(([col, type]) => {
                  const existing = columnConfigs.find(c => c.column_name === col);
                  const role = existing?.role || 'normal';
                  return (
                    <div key={col} className="flex items-center gap-3 p-2 bg-gray-50 rounded">
                      <span className="flex-1 font-medium text-sm text-gray-900">{col}</span>
                      <span className="text-xs px-2 py-0.5 bg-gray-200 rounded">{type}</span>
                      <select
                        value={role}
                        onChange={(e) => {
                          const newRole = e.target.value as ColumnConfig['role'];
                          setColumnConfigs(prev => {
                            const filtered = prev.filter(c => c.column_name !== col);
                            if (newRole !== 'normal') {
                              filtered.push({ column_name: col, role: newRole });
                            }
                            return filtered;
                          });
                        }}
                        className="px-2 py-1 border border-gray-300 rounded text-sm"
                      >
                        <option value="normal">Normal</option>
                        <option value="pii">PII (Anonymize)</option>
                        <option value="id">ID (Auto-detect)</option>
                        <option value="skip">Skip (Exclude)</option>
                      </select>
                    </div>
                  );
                })}
              </div>
              {columnConfigs.length > 0 && (
                <p className="mt-3 text-xs text-indigo-700 bg-indigo-50 px-3 py-2 rounded">
                  {columnConfigs.filter(c => c.role === 'skip').length} skipped,{' '}
                  {columnConfigs.filter(c => c.role === 'pii').length} anonymized,{' '}
                  {columnConfigs.filter(c => c.role === 'id').length} ID columns
                </p>
              )}
            </CardContent>
          )}
        </Card>
      )}

      {/* ================================================================
          CONDITIONAL GENERATION
          ================================================================ */}
      {Object.keys(columnTypes).length > 0 && (
        <Card className="mt-6">
          <CardHeader
            className="cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => setShowConditions(!showConditions)}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center">
                <Filter className="h-5 w-5 mr-2 text-orange-600" />
                Conditional Generation
                <span className="ml-2 text-xs font-normal px-2 py-1 bg-orange-100 text-orange-800 rounded">Optional</span>
              </CardTitle>
              {showConditions ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
            </div>
            <CardDescription>Filter generated data to match specific conditions (what-if scenarios)</CardDescription>
          </CardHeader>
          {showConditions && (
            <CardContent>
              <ConditionBuilder
                columns={Object.keys(columnTypes)}
                conditions={conditions}
                onConditionsChange={setConditions}
              />
            </CardContent>
          )}
        </Card>
      )}

      {/* ================================================================
          GENERATE BUTTON
          ================================================================ */}
      <Card className="mt-6">
        <CardContent className="pt-6">
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          )}

          <div>
            <Button
              onClick={handleGenerate}
              disabled={generating}
              className="w-full"
              size="lg"
            >
              {generating ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Starting Generation...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Start Generation
                </>
              )}
            </Button>
          </div>

          <div className="text-center text-sm text-gray-500 mt-2">
            <p>Estimated time: {getTimeEstimate(config.model_type, config.epochs, config.num_rows)}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
