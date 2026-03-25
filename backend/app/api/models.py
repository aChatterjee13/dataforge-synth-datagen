from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime

class DataType(str, Enum):
    STRUCTURED = "structured"  # Tabular data (CSV, Excel)
    UNSTRUCTURED = "unstructured"  # PDFs, text documents
    API_TESTING = "api_testing"  # OpenAPI/Swagger specs
    DATA_TESTING = "data_testing"  # Database schemas
    PII_MASKING = "pii_masking"  # PII detection & anonymization
    LOG_SYNTHESIS = "log_synthesis"  # Log & event data synthesis
    CDC_TESTING = "cdc_testing"  # CDC pipeline testing
    GRAPH_SYNTHESIS = "graph_synthesis"  # Graph / network data

class ModelType(str, Enum):
    CTGAN = "ctgan"
    GAUSSIAN_COPULA = "gaussian_copula"
    TVAE = "tvae"
    TIMEGAN = "timegan"  # PyTorch implementation
    COPULA_GAN = "copula_gan"  # SDV CopulaGAN
    TAB_DDPM = "tab_ddpm"  # Diffusion-based (synthcity)
    BAYESIAN_NETWORK = "bayesian_network"  # Interpretable statistical (synthcity)
    CTAB_GAN_PLUS = "ctab_gan_plus"  # ML-utility optimized GAN (synthcity)
    REALTABFORMER = "realtabformer"  # GPT-2 based tabular transformer
    DGAN = "dgan"  # DoppelGANger time-series (gretel-synthetics)
    DP_CTGAN = "dp_ctgan"  # Differentially-private CTGAN (smartnoise-synth)
    LLM_ROW_GEN = "llm_row_gen"  # LLM-based row generation (prototyping)
    GPT_PDF = "gpt_pdf"  # GPT-based PDF generation
    GPT_API_TEST = "gpt_api_test"  # GPT-based API test generation
    GPT_DATA_TEST = "gpt_data_test"  # GPT-based DB test data generation
    PII_MASK = "pii_mask"  # PII masking / anonymization
    LOG_SYNTH = "log_synth"  # Log & event data synthesis
    CDC_GEN = "cdc_gen"  # CDC event generation
    GRAPH_SYNTH = "graph_synth"  # Graph / network data synthesis
    AUTO = "auto"

class UseCase(str, Enum):
    ML_TRAINING = "ml_training"
    PROTOTYPING = "prototyping"

class SmoteStrategy(str, Enum):
    MINORITY = "minority"
    NOT_MINORITY = "not minority"
    NOT_MAJORITY = "not majority"
    ALL = "all"

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class PrivacyMechanism(str, Enum):
    NONE = "none"
    LAPLACE = "laplace"
    GAUSSIAN = "gaussian"
    DP_SGD = "dp_sgd"

class TargetVariable(BaseModel):
    """Configuration for ML efficacy target variable"""
    column_name: str = Field(description="Name of the target column")
    task_type: str = Field(description="'classification' or 'regression'")
    enabled: bool = Field(default=True, description="Whether to evaluate this target")

class ColumnConfig(BaseModel):
    """Column-level configuration (Feature 7)"""
    column_name: str
    role: str = Field(default="normal", description="Column role: normal, skip, id, pii")
    force_type: Optional[str] = Field(default=None, description="Force column type override")

class GenerationCondition(BaseModel):
    """Condition for conditional generation (Feature 10)"""
    column: str
    operator: str = Field(description="Operator: eq, ne, gt, lt, gte, lte")
    value: Any

class GenerationConfig(BaseModel):
    class Config:
        # Allow extra fields and be lenient with validation
        extra = "ignore"

    data_type: DataType = Field(default=DataType.STRUCTURED, description="Type of data to generate")
    model_type: ModelType = Field(default=ModelType.AUTO, description="Type of model to use")

    # Structured data config (allow 0 for PDF/unstructured generation)
    num_rows: int = Field(default=1000, ge=0, le=100000, description="Number of rows to generate")
    epochs: int = Field(default=300, ge=0, le=1000, description="Training epochs")
    batch_size: int = Field(default=500, ge=0, description="Batch size for training")

    # ML Efficacy configuration
    ml_target_variables: Optional[List[TargetVariable]] = Field(
        default=None,
        description="Target variables for ML efficacy evaluation"
    )

    # Privacy configuration
    enable_privacy: bool = Field(default=False, description="Enable differential privacy")
    privacy_epsilon: float = Field(default=1.0, ge=0.01, le=10.0, description="Privacy budget (epsilon)")
    privacy_delta: float = Field(default=1e-5, gt=0.0, le=1e-3, description="Privacy delta parameter")
    privacy_mechanism: PrivacyMechanism = Field(default=PrivacyMechanism.GAUSSIAN, description="Privacy mechanism to use")

    # Time-series configuration
    sequence_length: int = Field(default=24, gt=1, le=100, description="Sequence length for time-series")
    datetime_column: Optional[str] = Field(default=None, description="Name of datetime column for time-series")

    # Unstructured data config (PDFs)
    num_pdfs: int = Field(default=5, gt=0, le=100, description="Number of PDFs to generate")
    gpt_model: str = Field(default="gpt-4", description="GPT model to use")
    gpt_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    gpt_endpoint: Optional[str] = Field(default=None, description="Custom GPT endpoint")

    # API Testing config
    test_categories: Optional[List[str]] = Field(default=None, description="Test categories to generate")
    output_format: str = Field(default="postman", description="Output format (postman or json)")
    base_url: Optional[str] = Field(default=None, description="Base URL for API tests")

    # Data Testing config
    num_rows_per_table: int = Field(default=100, ge=1, le=10000, description="Rows per table")
    sql_dialect: str = Field(default="postgresql", description="Target SQL dialect")
    generate_violations: bool = Field(default=True, description="Generate constraint violation tests")
    generate_performance: bool = Field(default=False, description="Generate performance test data")

    # Column-level configuration (Feature 7)
    column_configs: Optional[List[ColumnConfig]] = Field(default=None, description="Per-column configuration")

    # Conditional generation (Feature 10)
    conditions: Optional[List[GenerationCondition]] = Field(default=None, description="Conditions for conditional generation")

    # Webhook callback (Feature 8)
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL to call on completion")

    # PII Masking config
    pii_column_strategies: Optional[Dict[str, str]] = Field(default=None, description="Column name -> masking strategy (synthetic/hash/redact/generalize)")

    # Log Synthesis config
    num_log_lines: int = Field(default=1000, ge=1, le=100000, description="Number of log lines to generate")
    log_time_range_hours: int = Field(default=24, ge=1, le=8760, description="Time range in hours for log timestamps")
    log_error_rate: float = Field(default=0.05, ge=0.0, le=1.0, description="Proportion of error-level log entries")

    # CDC Testing config
    cdc_event_count: int = Field(default=500, ge=1, le=50000, description="Number of CDC events to generate")
    cdc_insert_ratio: float = Field(default=0.5, ge=0.0, le=1.0, description="Proportion of INSERT events")
    cdc_update_ratio: float = Field(default=0.3, ge=0.0, le=1.0, description="Proportion of UPDATE events")
    cdc_delete_ratio: float = Field(default=0.2, ge=0.0, le=1.0, description="Proportion of DELETE events")
    cdc_output_format: str = Field(default="debezium", description="CDC output format: debezium, sql, csv")
    cdc_time_range_hours: int = Field(default=24, ge=1, le=8760, description="Time range in hours for CDC timestamps")

    # Graph Synthesis config
    graph_model: str = Field(default="auto", description="Graph model: auto, barabasi_albert, erdos_renyi, watts_strogatz, stochastic_block")
    graph_target_nodes: int = Field(default=100, ge=10, le=100000, description="Target number of nodes")
    graph_target_edges: Optional[int] = Field(default=None, description="Target number of edges (auto-calculated if None)")
    graph_output_format: str = Field(default="csv", description="Output format: csv, json, graphml, gexf")
    graph_mode: str = Field(default="generate", description="'generate' or 'augment'")
    graph_additional_nodes: int = Field(default=0, ge=0, le=100000, description="Number of nodes to add in augment mode")
    graph_additional_edges: int = Field(default=0, ge=0, le=500000, description="Number of edges to add in augment mode")

    # Use case selection (Model Zoo)
    use_case: UseCase = Field(default=UseCase.ML_TRAINING, description="Use case: ml_training or prototyping")

    # SMOTE augmentation (opt-in)
    enable_smote: bool = Field(default=False, description="Enable SMOTE oversampling post-processing")
    smote_target_column: Optional[str] = Field(default=None, description="Target column for SMOTE class balancing")
    smote_strategy: SmoteStrategy = Field(default=SmoteStrategy.MINORITY, description="SMOTE sampling strategy")
    smote_k_neighbors: int = Field(default=5, ge=1, le=20, description="Number of nearest neighbors for SMOTE")

    # LLM Row Generator config
    llm_row_gen_batch_size: int = Field(default=50, ge=10, le=200, description="Rows per LLM API call")

class PotentialTarget(BaseModel):
    """Information about a potential ML target variable"""
    name: str
    type: str
    unique_values: int
    null_percentage: float
    reason: str

class TimeSeriesInfo(BaseModel):
    """Information about detected time-series characteristics"""
    datetime_columns: List[str]
    confidence: float
    temporal_features: List[str]
    suggested_datetime_col: Optional[str]

class PDFInfo(BaseModel):
    """Information about uploaded PDF"""
    total_pages: int
    total_words: int
    content_type: str
    avg_words_per_page: float

class UploadResponse(BaseModel):
    job_id: str
    filename: str
    data_type: DataType = Field(default=DataType.STRUCTURED)

    # Structured data fields
    rows: Optional[int] = Field(default=0)
    columns: Optional[int] = Field(default=0)
    column_types: Optional[Dict[str, str]] = Field(default=None)
    sample_data: Optional[List[Dict[str, Any]]] = Field(default=None, description="First 10 rows as list of dicts (Feature 2)")
    potential_targets: Optional[Dict[str, List[PotentialTarget]]] = Field(
        default=None,
        description="Detected potential target variables for classification and regression"
    )
    is_timeseries: Optional[bool] = Field(default=False, description="Whether time-series patterns were detected")
    timeseries_info: Optional[TimeSeriesInfo] = Field(default=None, description="Time-series detection details")

    # Unstructured data fields (PDFs)
    pdf_count: Optional[int] = Field(default=0, description="Number of PDFs uploaded")
    pdf_info: Optional[List[PDFInfo]] = Field(default=None, description="Information about uploaded PDFs")

    message: str

class GenerateRequest(BaseModel):
    job_id: str
    config: GenerationConfig

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: float = Field(ge=0.0, le=100.0)
    message: str
    model_type: Optional[str] = Field(default=None, description="Type of model used")
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

class ValidationMetrics(BaseModel):
    quality_score: float = Field(ge=0.0, le=1.0, description="Overall quality score")
    statistical_similarity: Dict[str, float]
    correlation_preservation: float = Field(ge=0.0, le=1.0)
    privacy_score: float = Field(ge=0.0, le=1.0)
    structural_similarity: Optional[Dict[str, Any]] = Field(default=None, description="Structural similarity metrics")
    privacy_metrics: Optional[Dict[str, Any]] = Field(default=None, description="Differential privacy metrics")
    novel_quality_metrics: Optional[Dict[str, Any]] = Field(default=None, description="Novel ML-based quality metrics")
    column_metrics: Dict[str, Dict[str, Any]]
    relationship_tests: Dict[str, Any]
    statistical_measures: Dict[str, Any]

class ValidationResponse(BaseModel):
    job_id: str
    metrics: ValidationMetrics
    assessment_summary: str
    charts: Dict[str, Any]

class JobListItem(BaseModel):
    job_id: str
    filename: str
    status: JobStatus
    created_at: datetime
    rows_original: int
    rows_generated: Optional[int] = None
    model_type: Optional[str] = None
    quality_score: Optional[float] = None

class JobListResponse(BaseModel):
    jobs: List[JobListItem]
    total: int


# ============================================================================
# API TESTING MODELS
# ============================================================================

class APISpecInfo(BaseModel):
    title: str = ""
    version: str = ""
    total_endpoints: int = 0
    methods: Optional[Dict[str, int]] = None
    tags: Optional[List[str]] = None
    base_url: str = ""
    has_security: bool = False
    schema_count: int = 0
    relationships: int = 0

class APITestResultsResponse(BaseModel):
    job_id: str
    summary: Dict[str, Any]
    endpoint_coverage: List[Dict[str, Any]]
    category_counts: Dict[str, int]
    sample_tests: List[Dict[str, Any]]
    sample_flows: Optional[List[Dict[str, Any]]] = None
    spec_info: Optional[Dict[str, Any]] = None


# ============================================================================
# DATA TESTING MODELS
# ============================================================================

class DBSchemaInfo(BaseModel):
    total_tables: int = 0
    total_columns: int = 0
    total_foreign_keys: int = 0
    table_names: Optional[List[str]] = None
    dependency_order: Optional[List[str]] = None
    tables_summary: Optional[Dict[str, Any]] = None

class DBTestResultsResponse(BaseModel):
    job_id: str
    summary: Dict[str, Any]
    table_details: Dict[str, Any]
    sample_inserts: Optional[Dict[str, List[str]]] = None
    sample_violations: Optional[Dict[str, Any]] = None
    validation: Optional[Dict[str, Any]] = None
    dependency_order: Optional[List[str]] = None


# ============================================================================
# PRESET MODELS (Feature 5)
# ============================================================================

class PresetCreate(BaseModel):
    name: str = Field(description="Preset name")
    description: Optional[str] = Field(default=None, description="Preset description")
    config: Dict[str, Any] = Field(description="Generation configuration as JSON")

class PresetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    config: Dict[str, Any]
    is_builtin: bool = False
    created_at: Optional[datetime] = None


# ============================================================================
# MODEL RECOMMENDATION (Feature 6)
# ============================================================================

class ModelRecommendation(BaseModel):
    recommended_model: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: List[str]
    alternatives: List[Dict[str, Any]] = Field(default_factory=list)
    dataset_summary: Optional[Dict[str, Any]] = None


# ============================================================================
# API KEY MODELS (Feature 8)
# ============================================================================

class APIKeyCreate(BaseModel):
    name: str = Field(description="Name for the API key")

class APIKeyResponse(BaseModel):
    id: int
    name: str
    key_preview: str = Field(description="Masked key preview (first 8 chars)")
    created_at: datetime
    last_used: Optional[datetime] = None

class APIKeyCreateResponse(BaseModel):
    id: int
    name: str
    key: str = Field(description="The full API key (shown only once)")
    created_at: datetime


# ============================================================================
# MULTI-TABLE MODELS (Feature 9)
# ============================================================================

class TableRelationship(BaseModel):
    parent_table: str
    parent_column: str
    child_table: str
    child_column: str

class MultiTableConfig(BaseModel):
    relationships: List[TableRelationship]
    num_rows: int = Field(default=1000, ge=100, le=100000)
    epochs: int = Field(default=300, ge=50, le=1000)

class MultiTableUploadResponse(BaseModel):
    job_id: str
    tables: Dict[str, Dict[str, Any]] = Field(description="Table name -> {rows, columns, column_types}")
    message: str


# ============================================================================
# DRIFT DETECTION MODELS (Feature 11)
# ============================================================================

class ColumnDriftResult(BaseModel):
    column_name: str
    column_type: str
    drift_score: float = Field(ge=0.0, le=1.0)
    p_value: float
    test_used: str
    alert_level: str = Field(description="green, yellow, or red")
    details: Optional[Dict[str, Any]] = None

class PredictionDriftResult(BaseModel):
    task_type: str = Field(description="classification or regression")
    baseline_score: float = Field(description="Model accuracy/R2 on baseline")
    snapshot_score: float = Field(description="Model accuracy/R2 on snapshot")
    accuracy_drop: float = Field(description="baseline_score - snapshot_score")
    drift_detected: bool
    alert_level: str = Field(description="green, yellow, or red")
    model_used: str = Field(default="RandomForest")

class FeatureImportanceItem(BaseModel):
    feature_name: str
    importance: float

class FeatureImportanceShiftResult(BaseModel):
    rank_correlation: float = Field(description="Spearman rank correlation of importances")
    cosine_similarity: float
    importance_drift_score: float = Field(ge=0.0, le=1.0)
    baseline_top_features: List[FeatureImportanceItem]
    snapshot_top_features: List[FeatureImportanceItem]
    alert_level: str = Field(description="green, yellow, or red")

class ConditionalFeatureResult(BaseModel):
    feature_name: str
    conditional_drift_score: float = Field(ge=0.0, le=1.0)
    alert_level: str = Field(description="green, yellow, or red")
    bin_details: Optional[List[Dict[str, Any]]] = None

class ConditionalDistributionShiftResult(BaseModel):
    features: List[ConditionalFeatureResult]
    overall_conditional_drift_score: float = Field(ge=0.0, le=1.0)
    most_drifted_features: List[str]

class ConceptDriftResult(BaseModel):
    target_column: str
    task_type: str
    overall_concept_drift_score: float = Field(ge=0.0, le=1.0)
    concept_drift_detected: bool
    prediction_drift: PredictionDriftResult
    feature_importance_shift: FeatureImportanceShiftResult
    conditional_distribution_shift: ConditionalDistributionShiftResult
    summary: str

class DriftDetectionResponse(BaseModel):
    overall_drift_score: float = Field(ge=0.0, le=1.0)
    columns: List[ColumnDriftResult]
    summary: str
    alert_counts: Dict[str, int]
    concept_drift: Optional[ConceptDriftResult] = None


# ============================================================================
# STREAMING / PREVIEW MODELS (Feature 12)
# ============================================================================

class PreviewData(BaseModel):
    job_id: str
    rows_generated: int
    total_requested: int
    sample_data: List[Dict[str, Any]]
    is_complete: bool


# ============================================================================
# PII MASKING MODELS
# ============================================================================

class PIIColumnDetection(BaseModel):
    column_name: str
    pii_type: str = Field(description="Type of PII: email, ssn, phone, credit_card, ip, name, address, date_of_birth, age, gender, salary, occupation, etc.")
    pii_category: str = Field(default="direct", description="direct (uniquely identifies) or indirect (quasi-identifier)")
    confidence: float = Field(ge=0.0, le=1.0)
    sample_values: List[str] = Field(default_factory=list)
    suggested_strategy: str = Field(default="synthetic", description="synthetic, hash, redact, generalize")

class PIIUploadResponse(BaseModel):
    job_id: str
    filename: str
    rows: int
    columns: int
    detected_pii_columns: List[PIIColumnDetection]
    non_pii_columns: List[str]

class PIIResultsResponse(BaseModel):
    job_id: str
    summary: Dict[str, Any]
    column_reports: List[Dict[str, Any]]
    privacy_assessment: Dict[str, Any]


# ============================================================================
# LOG SYNTHESIS MODELS
# ============================================================================

class LogFormatInfo(BaseModel):
    detected_format: str = Field(description="apache, nginx, syslog, json, csv, unknown")
    total_lines: int
    fields: List[str]
    sample_lines: List[str]
    distributions: Dict[str, Any] = Field(default_factory=dict)

class LogUploadResponse(BaseModel):
    job_id: str
    filename: str
    format_info: LogFormatInfo

class LogResultsResponse(BaseModel):
    job_id: str
    summary: Dict[str, Any]
    analysis: Dict[str, Any]
    sample_logs: List[str]


# ============================================================================
# CDC TESTING MODELS
# ============================================================================

class CDCResultsResponse(BaseModel):
    job_id: str
    summary: Dict[str, Any]
    event_distribution: Dict[str, int]
    sample_events: List[Dict[str, Any]]


# ============================================================================
# GRAPH SYNTHESIS MODELS
# ============================================================================

class GraphStatsInfo(BaseModel):
    nodes: int
    edges: int
    density: float
    avg_degree: float
    clustering_coefficient: float
    connected_components: int
    is_directed: bool

class GraphUploadResponse(BaseModel):
    job_id: str
    filename: str
    graph_stats: GraphStatsInfo

class GraphVisualizationData(BaseModel):
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    links: List[Dict[str, Any]] = Field(default_factory=list)
    subsampled: bool = False
    total_nodes: int = 0
    total_edges: int = 0

class GraphResultsResponse(BaseModel):
    job_id: str
    summary: Dict[str, Any]
    original_stats: Dict[str, Any]
    synthetic_stats: Dict[str, Any]
    comparison: Dict[str, Any]
    graph_data: Optional[Dict[str, GraphVisualizationData]] = Field(default=None, description="Node-link data with positions for visualization")
