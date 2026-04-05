-- Git Intelligence Database Schema (without extension creation)
-- PostgreSQL 16+ with pgvector extension already installed

-- Create git_intelligence schema
CREATE SCHEMA IF NOT EXISTS git_intelligence;

-- Git operations tracking
CREATE TABLE IF NOT EXISTS git_intelligence.git_operations (
    id SERIAL PRIMARY KEY,
    repo_path TEXT NOT NULL,
    operation_type TEXT NOT NULL, -- 'merge', 'rebase', 'cherry-pick', 'commit'
    commit_hash TEXT,
    author_name TEXT,
    author_email TEXT,
    branch_name TEXT,
    target_branch TEXT,
    files_changed INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_deleted INTEGER DEFAULT 0,
    conflict_occurred BOOLEAN DEFAULT FALSE,
    conflicts_resolved INTEGER DEFAULT 0,
    resolution_time_seconds INTEGER,
    operation_success BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conflict patterns for ML learning
CREATE TABLE IF NOT EXISTS git_intelligence.conflict_patterns (
    id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    conflict_type TEXT NOT NULL, -- 'merge', 'rebase', 'cherry-pick', 'deletion'
    pattern_hash TEXT NOT NULL,
    code_pattern TEXT, -- Sample of conflicting code
    frequency INTEGER DEFAULT 1,
    resolution_strategy TEXT,
    success_rate FLOAT DEFAULT 0.0,
    avg_resolution_time INTEGER DEFAULT 0,
    complexity_score FLOAT DEFAULT 0.0,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(pattern_hash)
);

-- Conflict prediction results with validation
CREATE TABLE IF NOT EXISTS git_intelligence.conflict_predictions (
    id SERIAL PRIMARY KEY,
    repo_path TEXT NOT NULL,
    target_branch TEXT NOT NULL,
    source_branch TEXT NOT NULL,
    file_path TEXT NOT NULL,
    predicted_probability FLOAT NOT NULL,
    confidence_score FLOAT NOT NULL,
    prediction_method TEXT NOT NULL,
    features_json JSONB,
    neural_enhanced BOOLEAN DEFAULT FALSE,
    actual_conflict BOOLEAN,
    prediction_accuracy FLOAT,
    resolution_time_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    validated_at TIMESTAMP WITH TIME ZONE
);

-- Feature vectors for ML conflict prediction
CREATE TABLE IF NOT EXISTS git_intelligence.conflict_features (
    id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    feature_vector vector(128),
    conflict_occurred BOOLEAN NOT NULL,
    resolution_strategy TEXT,
    complexity_metrics JSONB,
    author_patterns JSONB,
    temporal_features JSONB,
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Author conflict and merge patterns
CREATE TABLE IF NOT EXISTS git_intelligence.author_patterns (
    author_email TEXT PRIMARY KEY,
    total_commits INTEGER DEFAULT 0,
    total_merges INTEGER DEFAULT 0,
    conflicts_caused INTEGER DEFAULT 0,
    conflicts_resolved INTEGER DEFAULT 0,
    conflict_rate FLOAT DEFAULT 0.0,
    resolution_rate FLOAT DEFAULT 0.0,
    files_frequently_modified TEXT[],
    preferred_merge_strategies TEXT[],
    avg_resolution_time INTEGER DEFAULT 0,
    collaboration_patterns JSONB,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Merge strategy recommendations and outcomes
CREATE TABLE IF NOT EXISTS git_intelligence.merge_recommendations (
    id SERIAL PRIMARY KEY,
    repo_path TEXT NOT NULL,
    source_branch TEXT NOT NULL,
    target_branch TEXT NOT NULL,
    recommended_strategy TEXT NOT NULL,
    confidence_score FLOAT NOT NULL,
    success_probability FLOAT NOT NULL,
    estimated_conflicts INTEGER DEFAULT 0,
    estimated_time_minutes INTEGER DEFAULT 0,
    risk_level TEXT, -- 'low', 'medium', 'high'
    actual_strategy_used TEXT,
    merge_success BOOLEAN,
    actual_conflicts INTEGER,
    actual_time_minutes INTEGER,
    recommendation_accuracy FLOAT,
    user_feedback_score INTEGER, -- 1-5 rating
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Strategy success patterns for learning
CREATE TABLE IF NOT EXISTS git_intelligence.strategy_patterns (
    id SERIAL PRIMARY KEY,
    strategy_type TEXT NOT NULL,
    branch_pattern TEXT,
    author_pattern TEXT,
    file_pattern TEXT,
    repo_context JSONB,
    success_rate FLOAT DEFAULT 0.0,
    avg_merge_time INTEGER DEFAULT 0,
    conflict_rate FLOAT DEFAULT 0.0,
    usage_count INTEGER DEFAULT 1,
    confidence_score FLOAT DEFAULT 0.0,
    last_used TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Code quality and review tracking
CREATE TABLE IF NOT EXISTS git_intelligence.code_reviews (
    id SERIAL PRIMARY KEY,
    repo_path TEXT NOT NULL,
    file_path TEXT NOT NULL,
    commit_hash TEXT,
    review_type TEXT NOT NULL, -- 'commit', 'pr', 'file', 'diff'
    overall_score FLOAT NOT NULL,
    complexity_score FLOAT,
    security_score FLOAT,
    performance_score FLOAT,
    maintainability_score FLOAT,
    documentation_score FLOAT,
    style_consistency_score FLOAT,
    issues_found INTEGER DEFAULT 0,
    critical_issues INTEGER DEFAULT 0,
    high_severity_issues INTEGER DEFAULT 0,
    review_time_ms INTEGER,
    neural_enhanced BOOLEAN DEFAULT FALSE,
    language_detected TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Individual code issues from reviews
CREATE TABLE IF NOT EXISTS git_intelligence.code_issues (
    id SERIAL PRIMARY KEY,
    review_id INTEGER REFERENCES git_intelligence.code_reviews(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    issue_type TEXT NOT NULL, -- 'security', 'performance', 'maintainability', 'style', 'bug'
    severity TEXT NOT NULL, -- 'critical', 'high', 'medium', 'low', 'info'
    line_number INTEGER,
    column_number INTEGER,
    message TEXT NOT NULL,
    suggestion TEXT,
    confidence FLOAT DEFAULT 0.0,
    rule_id TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    resolution_method TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- ML models storage and versioning
CREATE TABLE IF NOT EXISTS git_intelligence.ml_models (
    model_name TEXT PRIMARY KEY,
    model_version TEXT NOT NULL,
    model_type TEXT NOT NULL, -- 'conflict_predictor', 'merge_suggester', 'code_reviewer'
    model_data BYTEA,
    model_accuracy FLOAT,
    training_samples INTEGER,
    validation_samples INTEGER,
    feature_importance JSONB,
    hyperparameters JSONB,
    performance_metrics JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Neural embeddings for code similarity and pattern matching
CREATE TABLE IF NOT EXISTS git_intelligence.code_embeddings (
    id SERIAL PRIMARY KEY,
    file_path TEXT NOT NULL,
    commit_hash TEXT NOT NULL,
    embedding vector(256),
    content_hash TEXT NOT NULL,
    language TEXT,
    embedding_model TEXT DEFAULT 'git_intelligence_v1',
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Pattern learning and recognition
CREATE TABLE IF NOT EXISTS git_intelligence.review_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type TEXT NOT NULL, -- 'security', 'performance', 'quality', 'style'
    pattern_hash TEXT NOT NULL,
    code_snippet TEXT,
    issue_description TEXT,
    fix_suggestion TEXT,
    confidence_score FLOAT DEFAULT 0.0,
    occurrence_count INTEGER DEFAULT 1,
    false_positive_count INTEGER DEFAULT 0,
    true_positive_count INTEGER DEFAULT 0,
    language TEXT,
    file_extensions TEXT[],
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(pattern_hash)
);

-- Code pattern embeddings for neural similarity
CREATE TABLE IF NOT EXISTS git_intelligence.code_pattern_embeddings (
    id SERIAL PRIMARY KEY,
    pattern_type TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    embedding vector(256),
    pattern_data JSONB,
    similarity_threshold FLOAT DEFAULT 0.8,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Branch analysis and health metrics
CREATE TABLE IF NOT EXISTS git_intelligence.branch_analysis (
    id SERIAL PRIMARY KEY,
    repo_path TEXT NOT NULL,
    branch_name TEXT NOT NULL,
    commits_count INTEGER,
    files_changed INTEGER,
    lines_changed INTEGER,
    complexity_score FLOAT,
    merge_readiness_score FLOAT,
    conflict_risk_score FLOAT,
    last_commit_date TIMESTAMP WITH TIME ZONE,
    branch_age_days INTEGER,
    contributors_count INTEGER,
    merge_frequency FLOAT,
    analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance and system metrics
CREATE TABLE IF NOT EXISTS git_intelligence.system_metrics (
    id SERIAL PRIMARY KEY,
    metric_type TEXT NOT NULL, -- 'prediction_accuracy', 'review_time', 'neural_inference'
    metric_name TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_unit TEXT,
    component TEXT, -- 'conflict_predictor', 'merge_suggester', 'code_reviewer'
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User feedback and learning
CREATE TABLE IF NOT EXISTS git_intelligence.user_feedback (
    id SERIAL PRIMARY KEY,
    feedback_type TEXT NOT NULL, -- 'prediction', 'suggestion', 'review'
    reference_id INTEGER NOT NULL,
    reference_table TEXT NOT NULL,
    user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),
    feedback_text TEXT,
    improvement_suggestions TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create comprehensive indexes for performance
CREATE INDEX IF NOT EXISTS idx_git_ops_timestamp ON git_intelligence.git_operations(timestamp);
CREATE INDEX IF NOT EXISTS idx_git_ops_repo_branch ON git_intelligence.git_operations(repo_path, branch_name);
CREATE INDEX IF NOT EXISTS idx_git_ops_operation_type ON git_intelligence.git_operations(operation_type, conflict_occurred);

CREATE INDEX IF NOT EXISTS idx_conflict_patterns_file ON git_intelligence.conflict_patterns(file_path);
CREATE INDEX IF NOT EXISTS idx_conflict_patterns_type ON git_intelligence.conflict_patterns(conflict_type, success_rate);
CREATE INDEX IF NOT EXISTS idx_conflict_patterns_hash ON git_intelligence.conflict_patterns(pattern_hash);

CREATE INDEX IF NOT EXISTS idx_conflict_predictions_branches ON git_intelligence.conflict_predictions(target_branch, source_branch);
CREATE INDEX IF NOT EXISTS idx_conflict_predictions_accuracy ON git_intelligence.conflict_predictions(prediction_accuracy) WHERE actual_conflict IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_conflict_features_vector ON git_intelligence.conflict_features USING ivfflat (feature_vector vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_conflict_features_outcome ON git_intelligence.conflict_features(conflict_occurred);

CREATE INDEX IF NOT EXISTS idx_author_patterns_conflict_rate ON git_intelligence.author_patterns(conflict_rate);
CREATE INDEX IF NOT EXISTS idx_author_patterns_updated ON git_intelligence.author_patterns(last_updated);

CREATE INDEX IF NOT EXISTS idx_merge_recs_branches ON git_intelligence.merge_recommendations(source_branch, target_branch);
CREATE INDEX IF NOT EXISTS idx_merge_recs_accuracy ON git_intelligence.merge_recommendations(recommendation_accuracy) WHERE merge_success IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_strategy_patterns_type ON git_intelligence.strategy_patterns(strategy_type, success_rate);
CREATE INDEX IF NOT EXISTS idx_strategy_patterns_usage ON git_intelligence.strategy_patterns(usage_count, confidence_score);

CREATE INDEX IF NOT EXISTS idx_code_reviews_file ON git_intelligence.code_reviews(file_path);
CREATE INDEX IF NOT EXISTS idx_code_reviews_score ON git_intelligence.code_reviews(overall_score, critical_issues);
CREATE INDEX IF NOT EXISTS idx_code_reviews_timestamp ON git_intelligence.code_reviews(created_at);

CREATE INDEX IF NOT EXISTS idx_code_issues_severity ON git_intelligence.code_issues(severity, issue_type);
CREATE INDEX IF NOT EXISTS idx_code_issues_resolved ON git_intelligence.code_issues(resolved, resolution_method);

CREATE INDEX IF NOT EXISTS idx_code_embeddings_similarity ON git_intelligence.code_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_code_embeddings_hash ON git_intelligence.code_embeddings(content_hash);

CREATE INDEX IF NOT EXISTS idx_review_patterns_type ON git_intelligence.review_patterns(pattern_type, confidence_score);
CREATE INDEX IF NOT EXISTS idx_review_patterns_hash ON git_intelligence.review_patterns(pattern_hash);

CREATE INDEX IF NOT EXISTS idx_pattern_embeddings_similarity ON git_intelligence.code_pattern_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_branch_analysis_readiness ON git_intelligence.branch_analysis(merge_readiness_score, conflict_risk_score);
CREATE INDEX IF NOT EXISTS idx_branch_analysis_timestamp ON git_intelligence.branch_analysis(analysis_timestamp);

CREATE INDEX IF NOT EXISTS idx_system_metrics_type ON git_intelligence.system_metrics(metric_type, component);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON git_intelligence.system_metrics(timestamp);

-- Views for common queries and analytics

-- Conflict prediction accuracy view
CREATE OR REPLACE VIEW git_intelligence.prediction_accuracy_summary AS
SELECT 
    prediction_method,
    COUNT(*) as total_predictions,
    COUNT(*) FILTER (WHERE actual_conflict IS NOT NULL) as validated_predictions,
    AVG(prediction_accuracy) as avg_accuracy,
    AVG(confidence_score) as avg_confidence,
    COUNT(*) FILTER (WHERE predicted_probability > 0.5 AND actual_conflict = true) as true_positives,
    COUNT(*) FILTER (WHERE predicted_probability > 0.5 AND actual_conflict = false) as false_positives,
    COUNT(*) FILTER (WHERE predicted_probability <= 0.5 AND actual_conflict = true) as false_negatives,
    COUNT(*) FILTER (WHERE predicted_probability <= 0.5 AND actual_conflict = false) as true_negatives
FROM git_intelligence.conflict_predictions
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY prediction_method;

-- Merge strategy performance view
CREATE OR REPLACE VIEW git_intelligence.strategy_performance_summary AS
SELECT 
    recommended_strategy,
    COUNT(*) as total_recommendations,
    COUNT(*) FILTER (WHERE merge_success IS NOT NULL) as completed_merges,
    COUNT(*) FILTER (WHERE merge_success = true) as successful_merges,
    AVG(recommendation_accuracy) as avg_accuracy,
    AVG(confidence_score) as avg_confidence,
    AVG(actual_time_minutes) as avg_time_minutes,
    AVG(user_feedback_score) as avg_user_rating
FROM git_intelligence.merge_recommendations
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY recommended_strategy;

-- Code review quality trends view
CREATE OR REPLACE VIEW git_intelligence.code_quality_trends AS
SELECT 
    DATE_TRUNC('day', created_at) as review_date,
    COUNT(*) as reviews_count,
    AVG(overall_score) as avg_quality_score,
    AVG(complexity_score) as avg_complexity,
    AVG(security_score) as avg_security,
    AVG(performance_score) as avg_performance,
    COUNT(*) FILTER (WHERE critical_issues > 0) as reviews_with_critical_issues,
    AVG(issues_found) as avg_issues_per_review
FROM git_intelligence.code_reviews
WHERE created_at > NOW() - INTERVAL '90 days'
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY review_date;

-- Author productivity and quality metrics
CREATE OR REPLACE VIEW git_intelligence.author_productivity_summary AS
SELECT 
    ap.author_email,
    ap.total_commits,
    ap.conflict_rate,
    ap.resolution_rate,
    AVG(cr.overall_score) as avg_code_quality,
    COUNT(cr.id) as reviews_completed,
    AVG(cr.issues_found) as avg_issues_per_review,
    COUNT(cr.id) FILTER (WHERE cr.critical_issues > 0) as reviews_with_critical_issues
FROM git_intelligence.author_patterns ap
LEFT JOIN git_intelligence.git_operations go ON ap.author_email = go.author_email
LEFT JOIN git_intelligence.code_reviews cr ON go.commit_hash = cr.commit_hash
WHERE go.timestamp > NOW() - INTERVAL '30 days'
GROUP BY ap.author_email, ap.total_commits, ap.conflict_rate, ap.resolution_rate;

-- Functions for common operations

-- Function to update author patterns based on new operations
CREATE OR REPLACE FUNCTION git_intelligence.update_author_patterns()
RETURNS void AS $$
BEGIN
    -- Update author statistics from recent git operations
    INSERT INTO git_intelligence.author_patterns (
        author_email, total_commits, total_merges, conflicts_caused, conflicts_resolved
    )
    SELECT 
        author_email,
        COUNT(*) as total_commits,
        COUNT(*) FILTER (WHERE operation_type = 'merge') as total_merges,
        COUNT(*) FILTER (WHERE conflict_occurred = true) as conflicts_caused,
        COUNT(*) FILTER (WHERE conflict_occurred = true AND operation_success = true) as conflicts_resolved
    FROM git_intelligence.git_operations
    WHERE timestamp > NOW() - INTERVAL '90 days'
    GROUP BY author_email
    ON CONFLICT (author_email) DO UPDATE SET
        total_commits = EXCLUDED.total_commits,
        total_merges = EXCLUDED.total_merges,
        conflicts_caused = EXCLUDED.conflicts_caused,
        conflicts_resolved = EXCLUDED.conflicts_resolved,
        conflict_rate = CASE 
            WHEN EXCLUDED.total_merges > 0 THEN EXCLUDED.conflicts_caused::FLOAT / EXCLUDED.total_merges 
            ELSE 0.0 
        END,
        resolution_rate = CASE 
            WHEN EXCLUDED.conflicts_caused > 0 THEN EXCLUDED.conflicts_resolved::FLOAT / EXCLUDED.conflicts_caused 
            ELSE 0.0 
        END,
        last_updated = NOW();
END;
$$ LANGUAGE plpgsql;

-- Function to calculate conflict pattern success rates
CREATE OR REPLACE FUNCTION git_intelligence.update_pattern_success_rates()
RETURNS void AS $$
BEGIN
    -- Update conflict pattern success rates based on actual outcomes
    UPDATE git_intelligence.conflict_patterns cp
    SET success_rate = (
        SELECT COALESCE(AVG(
            CASE WHEN cp2.actual_conflict = false THEN 1.0 ELSE 0.0 END
        ), 0.0)
        FROM git_intelligence.conflict_predictions cp2
        WHERE cp2.file_path = cp.file_path
        AND cp2.actual_conflict IS NOT NULL
        AND cp2.created_at > NOW() - INTERVAL '30 days'
    ),
    avg_resolution_time = (
        SELECT COALESCE(AVG(cp2.resolution_time_seconds), 0)
        FROM git_intelligence.conflict_predictions cp2
        WHERE cp2.file_path = cp.file_path
        AND cp2.resolution_time_seconds IS NOT NULL
        AND cp2.created_at > NOW() - INTERVAL '30 days'
    ),
    last_seen = NOW()
    WHERE cp.last_seen < NOW() - INTERVAL '1 day';
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old data and maintain performance
CREATE OR REPLACE FUNCTION git_intelligence.cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Clean up old git operations (keep 6 months)
    DELETE FROM git_intelligence.git_operations 
    WHERE timestamp < NOW() - INTERVAL '6 months';
    
    -- Clean up old predictions (keep 3 months)
    DELETE FROM git_intelligence.conflict_predictions 
    WHERE created_at < NOW() - INTERVAL '3 months';
    
    -- Clean up old code reviews (keep 1 year)
    DELETE FROM git_intelligence.code_reviews 
    WHERE created_at < NOW() - INTERVAL '1 year';
    
    -- Clean up old embeddings (keep 6 months)
    DELETE FROM git_intelligence.code_embeddings 
    WHERE timestamp < NOW() - INTERVAL '6 months';
    
    -- Update table statistics
    ANALYZE git_intelligence.git_operations;
    ANALYZE git_intelligence.conflict_predictions;
    ANALYZE git_intelligence.code_reviews;
    ANALYZE git_intelligence.code_embeddings;
    
    -- Log cleanup completion
    INSERT INTO git_intelligence.system_metrics 
    (metric_type, metric_name, metric_value, component)
    VALUES ('maintenance', 'cleanup_completed', 1.0, 'database');
END;
$$ LANGUAGE plpgsql;

COMMENT ON SCHEMA git_intelligence IS 'Git Intelligence ML system database schema with neural embeddings support';
COMMENT ON TABLE git_intelligence.git_operations IS 'Tracks all git operations for learning patterns';
COMMENT ON TABLE git_intelligence.conflict_predictions IS 'ML conflict predictions with validation results';
COMMENT ON TABLE git_intelligence.code_reviews IS 'Neural-enhanced code review results';
COMMENT ON TABLE git_intelligence.ml_models IS 'Versioned ML models with performance metrics';
COMMENT ON TABLE git_intelligence.code_embeddings IS 'Neural embeddings for code similarity (pgvector)';