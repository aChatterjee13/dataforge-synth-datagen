export const ModelType = {
  CTGAN: 'ctgan',
  GAUSSIAN_COPULA: 'gaussian_copula',
  TVAE: 'tvae',
  TIMEGAN: 'timegan',
  COPULA_GAN: 'copula_gan',
  TAB_DDPM: 'tab_ddpm',
  BAYESIAN_NETWORK: 'bayesian_network',
  CTAB_GAN_PLUS: 'ctab_gan_plus',
  REALTABFORMER: 'realtabformer',
  DGAN: 'dgan',
  DP_CTGAN: 'dp_ctgan',
  LLM_ROW_GEN: 'llm_row_gen',
  GPT_PDF: 'gpt_pdf',
  GPT_API_TEST: 'gpt_api_test',
  GPT_DATA_TEST: 'gpt_data_test',
  PII_MASK: 'pii_mask',
  LOG_SYNTH: 'log_synth',
  CDC_GEN: 'cdc_gen',
  GRAPH_SYNTH: 'graph_synth',
  AUTO: 'auto'
} as const;

export type ModelType = typeof ModelType[keyof typeof ModelType];

export const UseCase = {
  ML_TRAINING: 'ml_training',
  PROTOTYPING: 'prototyping',
} as const;

export type UseCase = typeof UseCase[keyof typeof UseCase];

export const SmoteStrategy = {
  MINORITY: 'minority',
  NOT_MINORITY: 'not minority',
  NOT_MAJORITY: 'not majority',
  ALL: 'all',
} as const;

export type SmoteStrategy = typeof SmoteStrategy[keyof typeof SmoteStrategy];

export const DataType = {
  STRUCTURED: 'structured',
  UNSTRUCTURED: 'unstructured',
  API_TESTING: 'api_testing',
  DATA_TESTING: 'data_testing',
  PII_MASKING: 'pii_masking',
  LOG_SYNTHESIS: 'log_synthesis',
  CDC_TESTING: 'cdc_testing',
  GRAPH_SYNTHESIS: 'graph_synthesis',
  MULTI_TABLE: 'multi_table'
} as const;

export type DataType = typeof DataType[keyof typeof DataType];

export const JobStatus = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed'
} as const;

export type JobStatus = typeof JobStatus[keyof typeof JobStatus];

export interface TargetVariable {
  column_name: string;
  task_type: 'classification' | 'regression';
  enabled: boolean;
}

export interface ColumnConfig {
  column_name: string;
  role: 'normal' | 'skip' | 'id' | 'pii';
  force_type?: string;
}

export interface GenerationCondition {
  column: string;
  operator: 'eq' | 'ne' | 'gt' | 'lt' | 'gte' | 'lte';
  value: string | number;
}

export interface GenerationConfig {
  model_type: ModelType;
  num_rows: number;
  epochs: number;
  batch_size: number;
  ml_target_variables?: TargetVariable[];
  privacy_level?: number;
  // Time-series specific
  sequence_length?: number;
  datetime_column?: string;
  // Unstructured data (PDF) specific
  data_type?: DataType;
  num_pdfs?: number;
  gpt_model?: string;
  gpt_api_key?: string;
  gpt_endpoint?: string;
  // API Testing specific
  test_categories?: string[];
  output_format?: string;
  base_url?: string;
  // Data Testing specific
  num_rows_per_table?: number;
  sql_dialect?: string;
  generate_violations?: boolean;
  generate_performance?: boolean;
  // Column-level config (Feature 7)
  column_configs?: ColumnConfig[];
  // Conditional generation (Feature 10)
  conditions?: GenerationCondition[];
  // Webhook (Feature 8)
  webhook_url?: string;
  // Privacy extras
  enable_privacy?: boolean;
  privacy_epsilon?: number;
  // PII Masking config
  pii_column_strategies?: Record<string, string>;
  // Log Synthesis config
  num_log_lines?: number;
  log_time_range_hours?: number;
  log_error_rate?: number;
  // CDC Testing config
  cdc_event_count?: number;
  cdc_insert_ratio?: number;
  cdc_update_ratio?: number;
  cdc_delete_ratio?: number;
  cdc_output_format?: string;
  cdc_time_range_hours?: number;
  // Graph Synthesis config
  graph_model?: string;
  graph_target_nodes?: number;
  graph_target_edges?: number;
  graph_output_format?: string;
  graph_mode?: 'generate' | 'augment';
  graph_additional_nodes?: number;
  graph_additional_edges?: number;
  // Use case (Model Zoo)
  use_case?: UseCase;
  // SMOTE augmentation
  enable_smote?: boolean;
  smote_target_column?: string;
  smote_strategy?: SmoteStrategy;
  smote_k_neighbors?: number;
  // LLM Row Generator
  llm_row_gen_batch_size?: number;
}

export interface PotentialTarget {
  name: string;
  type: string;
  unique_values: number;
  null_percentage: number;
  reason: string;
}

export interface TimeSeriesInfo {
  datetime_columns: string[];
  confidence: number;
  temporal_features: string[];
  suggested_datetime_col: string | null;
}

export interface PDFInfo {
  total_pages: number;
  total_words: number;
  content_type: string;
  avg_words_per_page: number;
}

export interface UploadResponse {
  job_id: string;
  filename: string;
  rows: number;
  columns: number;
  column_types: Record<string, string>;
  sample_data?: Record<string, unknown>[];
  potential_targets?: {
    classification: PotentialTarget[];
    regression: PotentialTarget[];
  };
  is_timeseries?: boolean;
  timeseries_info?: TimeSeriesInfo;
  // Unstructured data (PDF) specific
  data_type?: DataType;
  pdf_count?: number;
  pdf_info?: PDFInfo[];
  message: string;
}

export interface GenerateResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface CDCSchemaUploadResponse {
  job_id: string;
  filename: string;
  schema_info: Record<string, unknown>;
  message: string;
}

export interface PDFListItem {
  filename: string;
  size: number;
  download_url: string;
}

export interface PDFListResponse {
  job_id: string;
  total_pdfs: number;
  pdfs: PDFListItem[];
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  progress: number;
  message: string;
  model_type?: string;
  created_at: string;
  completed_at?: string;
  error?: string;
}

interface HistogramData {
  bins: number[];
  original: number[];
  synthetic: number[];
}

interface CategoryData {
  categories: string[];
  original: number[];
  synthetic: number[];
}

interface ColumnMetrics {
  column_type: 'numeric' | 'categorical';
  quality_score: number;
  // Numeric metrics
  ks_statistic?: number;
  ks_pvalue?: number;
  original_mean?: number;
  synthetic_mean?: number;
  original_std?: number;
  synthetic_std?: number;
  mean_diff?: number;
  std_diff?: number;
  std_ratio?: number;
  kl_divergence?: number;
  js_divergence?: number;
  distribution_overlap?: number;
  histogram_data?: HistogramData;
  // Categorical metrics
  chi2_statistic?: number;
  category_data?: CategoryData;
}

interface RelationshipTest {
  feature_1: string;
  feature_2: string;
  test_type: 't-test' | 'chi-square';
  original_statistic: number;
  original_pvalue: number;
  synthetic_statistic: number;
  synthetic_pvalue: number;
  original_reject_null: boolean;
  synthetic_reject_null: boolean;
  hypothesis_consistent: boolean;
}

interface RelationshipTests {
  numeric_pairs: RelationshipTest[];
  categorical_pairs: RelationshipTest[];
  mixed_pairs: RelationshipTest[];
}

interface StatisticalMeasures {
  means?: {
    original: Record<string, number>;
    synthetic: Record<string, number>;
  };
  std_devs?: {
    original: Record<string, number>;
    synthetic: Record<string, number>;
  };
  correlations?: {
    original: Record<string, Record<string, number>>;
    synthetic: Record<string, Record<string, number>>;
  };
  covariances?: {
    original: Record<string, Record<string, number>>;
    synthetic: Record<string, Record<string, number>>;
  };
  correlation_difference?: number;
  covariance_difference?: number;
}

interface StructuralSimilarity {
  schema_validation: {
    column_count_match: boolean;
    original_column_count: number;
    synthetic_column_count: number;
    missing_columns: string[];
    extra_columns: string[];
    column_names_match: boolean;
    type_match_score: number;
    data_type_matches: Record<string, {
      original: string;
      synthetic: string;
      matches: boolean;
    }>;
  };
  missing_patterns: {
    column_wise_comparison: Record<string, {
      original_missing_pct: number;
      synthetic_missing_pct: number;
      difference: number;
      similarity_score: number;
    }>;
    overall_missing_pattern_score: number;
  };
  value_ranges: {
    numeric_columns: Record<string, {
      original_min: number;
      original_max: number;
      synthetic_min: number;
      synthetic_max: number;
      within_bounds: boolean;
      range_preservation_score: number;
    }>;
    overall_range_score: number;
  };
  cardinality: {
    categorical_columns: Record<string, {
      original_unique_count: number;
      synthetic_unique_count: number;
      category_preservation_rate: number;
      cardinality_ratio: number;
      similarity_score: number;
      missing_categories: string[];
      new_categories: string[];
    }>;
    overall_cardinality_score: number;
  };
  data_quality: {
    overall_null_rate_original: number;
    overall_null_rate_synthetic: number;
    row_count_original: number;
    row_count_synthetic: number;
    null_rate_similarity_score: number;
  };
  overall_structural_score: number;
  summary: {
    schema_score: number;
    missing_pattern_score: number;
    value_range_score: number;
    cardinality_score: number;
    data_quality_score: number;
  };
}

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

interface MLEfficacyTask {
  target_column: string;
  task_type: 'classification' | 'regression';
  trtr_accuracy?: number;
  tstr_accuracy?: number;
  trtr_r2?: number;
  tstr_r2?: number;
  efficacy_score: number;
  interpretation: string;
}

interface FeatureImportanceTask {
  target: string;
  rank_correlation: number;
  cosine_similarity: number;
  top_features_real: string[];
  top_features_synthetic: string[];
}

interface NovelQualityMetrics {
  overall_novel_quality_score: number;
  ml_efficacy?: {
    overall_ml_efficacy: number;
    classification_tasks: MLEfficacyTask[];
    regression_tasks: MLEfficacyTask[];
  };
  feature_importance_preservation?: {
    overall_preservation: number;
    tasks: FeatureImportanceTask[];
  };
  rare_event_preservation?: {
    overall_rare_event_score: number;
    numeric_outliers: Record<string, {
      original_outlier_rate: number;
      synthetic_outlier_rate: number;
      preservation_score: number;
    }>;
    categorical_rare_values: Record<string, {
      num_rare_values: number;
      rare_values_preserved: number;
      preservation_rate: number;
    }>;
  };
  multivariate_interactions?: {
    overall_interaction_score: number;
    three_way_interactions: Array<{
      features: string[];
      ks_statistic: number;
      similarity_score: number;
    }>;
  };
  synthetic_detectability?: {
    classifier_accuracy: number;
    detectability_score: number;
    interpretation: string;
  };
  boundary_preservation?: {
    overall_boundary_score: number;
    boundary_tests: Array<{
      target: string;
      real_accuracy: number;
      synthetic_accuracy: number;
      boundary_score: number;
    }>;
  };
  manifold_similarity?: {
    density_correlation: number;
    manifold_score: number;
  };
}

export interface ValidationMetrics {
  quality_score: number;
  statistical_similarity: {
    correlation_preservation: number;
    avg_column_quality: number;
    num_columns_evaluated: number;
  };
  correlation_preservation: number;
  privacy_score: number;
  privacy_metrics?: PrivacyMetrics;
  structural_similarity?: StructuralSimilarity;
  novel_quality_metrics?: NovelQualityMetrics;
  column_metrics: Record<string, ColumnMetrics>;
  relationship_tests: RelationshipTests;
  statistical_measures: StatisticalMeasures;
}

export interface ValidationResponse {
  job_id: string;
  metrics: ValidationMetrics;
  assessment_summary: string;
  charts: {
    column_quality: Record<string, number>;
    correlation_matrices: {
      original: Record<string, Record<string, number>>;
      synthetic: Record<string, Record<string, number>>;
    };
  };
}

export interface JobListItem {
  job_id: string;
  filename: string;
  status: JobStatus;
  created_at: string;
  rows_original: number;
  rows_generated?: number;
  model_type?: string;
  quality_score?: number;
}

export type {
  HistogramData,
  CategoryData,
  ColumnMetrics,
  RelationshipTest,
  RelationshipTests,
  StatisticalMeasures,
  StructuralSimilarity,
  PrivacyMetrics,
  NovelQualityMetrics,
  MLEfficacyTask,
  FeatureImportanceTask
};


// ============================================================================
// API TESTING TYPES
// ============================================================================

export interface APISpecInfo {
  title: string;
  version: string;
  total_endpoints: number;
  methods?: Record<string, number>;
  tags?: string[];
  base_url: string;
  has_security: boolean;
  schema_count: number;
  relationships: number;
}

export interface APITestResultsResponse {
  job_id: string;
  summary: {
    total_tests: number;
    total_flows: number;
    endpoints_covered: number;
    output_format: string;
  };
  endpoint_coverage: Array<{ endpoint: string; test_count: number }>;
  category_counts: Record<string, number>;
  sample_tests: Array<{
    name: string;
    category: string;
    method: string;
    path: string;
    description: string;
    request?: Record<string, unknown>;
    expected?: { status_code: number; response_contains?: string[]; response_not_contains?: string[] };
  }>;
  sample_flows?: Array<{
    name: string;
    category: string;
    description: string;
    steps: Array<{ step: number; action: string; method: string; path: string; expected_status: number }>;
  }>;
  spec_info?: Record<string, unknown>;
}


// ============================================================================
// DATA TESTING TYPES
// ============================================================================

export interface DBSchemaInfo {
  total_tables: number;
  total_columns: number;
  total_foreign_keys: number;
  table_names?: string[];
  dependency_order?: string[];
  tables_summary?: Record<string, {
    columns: number;
    primary_keys: string[];
    foreign_key_count: number;
  }>;
}

export interface DBTestResultsResponse {
  job_id: string;
  summary: {
    total_tables: number;
    total_inserts: number;
    total_violations: number;
    dialect: string;
    validation_score: number;
  };
  table_details: Record<string, {
    insert_count: number;
    violation_count: number;
    columns: number;
    foreign_keys: string[];
  }>;
  sample_inserts?: Record<string, string[]>;
  sample_violations?: Record<string, Array<{
    name: string;
    constraint_type: string;
    description: string;
    sql: string;
    expected_error: string;
  }>>;
  validation?: {
    total: number;
    successful: number;
    failed: number;
    errors: string[];
    validation_score: number;
  };
  dependency_order?: string[];
}


// ============================================================================
// PRESET TYPES (Feature 5)
// ============================================================================

export interface Preset {
  id: number;
  name: string;
  description?: string;
  config: Record<string, unknown>;
  is_builtin: boolean;
  created_at?: string;
}


// ============================================================================
// MODEL RECOMMENDATION (Feature 6)
// ============================================================================

export interface ModelRecommendation {
  recommended_model: string;
  confidence: number;
  reasons: string[];
  alternatives: Array<{ model: string; reason: string }>;
  dataset_summary?: Record<string, unknown>;
}


// ============================================================================
// API KEY TYPES (Feature 8)
// ============================================================================

export interface APIKeyItem {
  id: number;
  name: string;
  key_preview: string;
  created_at: string;
  last_used?: string;
}

export interface APIKeyCreateResponse {
  id: number;
  name: string;
  key: string;
  created_at: string;
}


// ============================================================================
// MULTI-TABLE TYPES (Feature 9)
// ============================================================================

export interface TableRelationship {
  parent_table: string;
  parent_column: string;
  child_table: string;
  child_column: string;
}

export interface MultiTableConfig {
  relationships: TableRelationship[];
  num_rows: number;
  epochs: number;
}

export interface MultiTableUploadResponse {
  job_id: string;
  tables: Record<string, { rows: number; columns: number; column_types: Record<string, string>; filename?: string }>;
  message: string;
}


// ============================================================================
// DRIFT DETECTION TYPES (Feature 11)
// ============================================================================

export interface ColumnDriftResult {
  column_name: string;
  column_type: string;
  drift_score: number;
  p_value: number;
  test_used: string;
  alert_level: 'green' | 'yellow' | 'red';
  details?: Record<string, unknown>;
}

export interface DriftResult {
  overall_drift_score: number;
  columns: ColumnDriftResult[];
  summary: string;
  alert_counts: { green: number; yellow: number; red: number };
  concept_drift?: ConceptDriftResult;
}

// Concept Drift Types
export interface PredictionDriftResult {
  task_type: 'classification' | 'regression';
  baseline_score: number;
  snapshot_score: number;
  accuracy_drop: number;
  drift_detected: boolean;
  alert_level: 'green' | 'yellow' | 'red';
  model_used: string;
}

export interface FeatureImportanceItem {
  feature_name: string;
  importance: number;
}

export interface FeatureImportanceShiftResult {
  rank_correlation: number;
  cosine_similarity: number;
  importance_drift_score: number;
  baseline_top_features: FeatureImportanceItem[];
  snapshot_top_features: FeatureImportanceItem[];
  alert_level: 'green' | 'yellow' | 'red';
}

export interface ConditionalFeatureResult {
  feature_name: string;
  conditional_drift_score: number;
  alert_level: 'green' | 'yellow' | 'red';
  bin_details?: Array<Record<string, unknown>>;
}

export interface ConditionalDistributionShiftResult {
  features: ConditionalFeatureResult[];
  overall_conditional_drift_score: number;
  most_drifted_features: string[];
}

export interface ConceptDriftResult {
  target_column: string;
  task_type: string;
  overall_concept_drift_score: number;
  concept_drift_detected: boolean;
  prediction_drift: PredictionDriftResult;
  feature_importance_shift: FeatureImportanceShiftResult;
  conditional_distribution_shift: ConditionalDistributionShiftResult;
  summary: string;
}

export interface DriftColumnInfo {
  name: string;
  type: 'numeric' | 'categorical';
}


// ============================================================================
// STREAMING / PREVIEW TYPES (Feature 12)
// ============================================================================

export interface PreviewData {
  job_id: string;
  rows_generated: number;
  total_requested: number;
  sample_data: Record<string, unknown>[];
  is_complete: boolean;
}


// ============================================================================
// PII MASKING TYPES
// ============================================================================

export interface PIIColumnDetection {
  column_name: string;
  pii_type: string;
  pii_category: 'direct' | 'indirect';
  confidence: number;
  sample_values: string[];
  suggested_strategy: string;
}

export interface PIIUploadResponse {
  job_id: string;
  filename: string;
  rows: number;
  columns: number;
  detected_pii_columns: PIIColumnDetection[];
  non_pii_columns: string[];
}

export interface PIIResultsResponse {
  job_id: string;
  summary: Record<string, unknown>;
  column_reports: Array<{
    column_name: string;
    pii_type: string;
    strategy: string;
    confidence: number;
    before_samples: string[];
    after_samples: string[];
  }>;
  privacy_assessment: Record<string, unknown>;
}


// ============================================================================
// LOG SYNTHESIS TYPES
// ============================================================================

export interface LogFormatInfo {
  detected_format: string;
  total_lines: number;
  fields: string[];
  sample_lines: string[];
  distributions: Record<string, unknown>;
}

export interface LogUploadResponse {
  job_id: string;
  filename: string;
  format_info: LogFormatInfo;
}

export interface LogResultsResponse {
  job_id: string;
  summary: {
    format: string;
    original_lines: number;
    generated_lines: number;
    time_range_hours: number;
    error_rate: number;
  };
  analysis: Record<string, unknown>;
  sample_logs: string[];
}


// ============================================================================
// CDC TESTING TYPES
// ============================================================================

export interface CDCResultsResponse {
  job_id: string;
  summary: {
    total_events: number;
    inserts: number;
    updates: number;
    deletes: number;
    tables_affected: number;
    output_format: string;
    time_range_hours: number;
  };
  event_distribution: Record<string, number>;
  sample_events: Array<{
    operation: string;
    table: string;
    timestamp: string;
    before: Record<string, unknown> | null;
    after: Record<string, unknown> | null;
  }>;
}


// ============================================================================
// GRAPH SYNTHESIS TYPES
// ============================================================================

export interface GraphStatsInfo {
  nodes: number;
  edges: number;
  density: number;
  avg_degree: number;
  clustering_coefficient: number;
  connected_components: number;
  is_directed: boolean;
}

export interface GraphUploadResponse {
  job_id: string;
  filename: string;
  graph_stats: GraphStatsInfo;
}

export interface GraphVisualizationNode {
  id: string;
  x: number;
  y: number;
  degree: number;
}

export interface GraphVisualizationLink {
  source: string;
  target: string;
}

export interface GraphVisualizationData {
  nodes: GraphVisualizationNode[];
  links: GraphVisualizationLink[];
  subsampled: boolean;
  total_nodes: number;
  total_edges: number;
}

export interface GraphResultsResponse {
  job_id: string;
  summary: {
    model_used: string;
    original_nodes: number;
    original_edges: number;
    synthetic_nodes: number;
    synthetic_edges: number;
    overall_match_score: number;
    output_format: string;
    mode?: 'generate' | 'augment';
    nodes_added?: number;
    edges_added?: number;
  };
  original_stats: Record<string, unknown>;
  synthetic_stats: Record<string, unknown>;
  comparison: Record<string, {
    original: number;
    synthetic: number;
    ratio: number;
    match_score: number;
  }>;
  graph_data?: {
    original: GraphVisualizationData;
    synthetic: GraphVisualizationData;
  };
}
