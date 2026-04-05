-- Think Mode Auto-Calibration Database Schema
-- PostgreSQL Schema for Dynamic Think Mode Learning System
-- Integrates with existing claude-postgres Docker container (port 5433)
--
-- ARCHITECT Agent Design: Self-learning calibration architecture
-- DOCKER-INTERNAL Agent: PostgreSQL Docker integration
--
-- Purpose: Auto-calibrate complexity scoring weights based on real user feedback
-- Target: Transform conservative 0.0-0.1 scoring to full 0.0-1.0 range with ML

-- Create schema for think mode calibration
CREATE SCHEMA IF NOT EXISTS think_mode_calibration;

-- Grant permissions to claude_agent user
GRANT ALL PRIVILEGES ON SCHEMA think_mode_calibration TO claude_agent;

-- Set search path to include new schema
SET search_path = think_mode_calibration, public;

-- ================================
-- 1. DECISION TRACKING TABLE
-- ================================
-- Records every think mode decision with feedback for learning

CREATE TABLE decision_tracking (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    task_text TEXT NOT NULL,
    task_hash VARCHAR(64) NOT NULL,  -- MD5 hash for deduplication

    -- Original complexity analysis
    complexity_score REAL NOT NULL,
    decision_made VARCHAR(20) NOT NULL,  -- no_thinking, interleaved, auto
    confidence REAL NOT NULL,
    processing_time_ms REAL NOT NULL,
    npu_accelerated BOOLEAN DEFAULT FALSE,

    -- Feature extraction results
    word_count INTEGER NOT NULL,
    question_count INTEGER NOT NULL,
    technical_terms INTEGER NOT NULL,
    multi_step_indicators INTEGER NOT NULL,
    agent_recommendations TEXT[],  -- Array of recommended agents

    -- Actual outcome feedback (for learning)
    actual_complexity REAL,  -- User feedback or inferred complexity
    decision_correctness REAL,  -- 0.0 = wrong, 1.0 = perfect
    execution_time_ms REAL,  -- Actual Claude execution time
    user_satisfaction REAL,  -- User satisfaction score (optional)

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Embedding for similarity search
    task_embedding VECTOR(256)  -- pgvector for task similarity
);

-- Indexes for performance
CREATE INDEX idx_decision_tracking_task_hash ON decision_tracking(task_hash);
CREATE INDEX idx_decision_tracking_session ON decision_tracking(session_id);
CREATE INDEX idx_decision_tracking_created ON decision_tracking(created_at);
CREATE INDEX idx_decision_tracking_complexity ON decision_tracking(complexity_score);
CREATE INDEX idx_decision_tracking_embedding ON decision_tracking USING ivfflat (task_embedding vector_cosine_ops);

-- ================================
-- 2. WEIGHT EVOLUTION TABLE
-- ================================
-- Tracks how complexity scoring weights evolve through learning

CREATE TABLE weight_evolution (
    id BIGSERIAL PRIMARY KEY,
    version INTEGER NOT NULL,  -- Weight version number

    -- Complexity scoring weights (dynamic calibration targets)
    word_count_weight REAL NOT NULL DEFAULT 0.002,
    technical_terms_weight REAL NOT NULL DEFAULT 0.1,
    multi_step_weight REAL NOT NULL DEFAULT 0.1,
    question_weight REAL NOT NULL DEFAULT 0.1,
    agent_coordination_weight REAL NOT NULL DEFAULT 0.15,

    -- Performance metrics for this weight set
    accuracy_score REAL,  -- 0.0-1.0 decision accuracy
    avg_complexity_score REAL,  -- Average complexity scores produced
    score_distribution JSONB,  -- Distribution of scores (0.0-0.1, 0.1-0.2, etc.)
    confidence_level REAL,  -- Statistical confidence in these weights

    -- Learning metadata
    training_samples INTEGER NOT NULL DEFAULT 0,
    learning_algorithm VARCHAR(50),  -- ML algorithm used for optimization
    optimization_target VARCHAR(50),  -- What we're optimizing for

    -- Deployment tracking
    deployed_at TIMESTAMP WITH TIME ZONE,
    active BOOLEAN DEFAULT FALSE,  -- Currently active weight set
    rollback_reason TEXT,  -- Reason for rollback if deactivated

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ensure only one active weight set
CREATE UNIQUE INDEX idx_weight_evolution_active ON weight_evolution(active) WHERE active = TRUE;

-- ================================
-- 3. CALIBRATION METRICS TABLE
-- ================================
-- Real-time metrics for calibration system performance

CREATE TABLE calibration_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value REAL NOT NULL,
    metric_metadata JSONB,

    -- Aggregation info
    aggregation_period VARCHAR(20),  -- hourly, daily, weekly
    sample_count INTEGER,
    min_value REAL,
    max_value REAL,
    avg_value REAL,

    -- Timing
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for metrics
CREATE INDEX idx_calibration_metrics_name ON calibration_metrics(metric_name);
CREATE INDEX idx_calibration_metrics_period ON calibration_metrics(period_start, period_end);

-- ================================
-- 4. TRAINING DATASETS TABLE
-- ================================
-- Manages ML training datasets for weight optimization

CREATE TABLE training_datasets (
    id BIGSERIAL PRIMARY KEY,
    dataset_name VARCHAR(100) NOT NULL,
    dataset_version INTEGER NOT NULL,

    -- Dataset characteristics
    sample_count INTEGER NOT NULL,
    feature_count INTEGER NOT NULL,
    target_accuracy REAL NOT NULL,

    -- Training data (JSON for flexibility)
    training_features JSONB NOT NULL,
    training_targets JSONB NOT NULL,
    validation_split REAL DEFAULT 0.2,

    -- Performance tracking
    model_accuracy REAL,
    training_time_ms REAL,
    model_metadata JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(dataset_name, dataset_version)
);

-- ================================
-- 5. PERFORMANCE VIEWS
-- ================================
-- Convenient views for analytics and monitoring

-- Real-time calibration performance
CREATE VIEW calibration_performance AS
SELECT
    DATE_TRUNC('hour', created_at) as hour,
    COUNT(*) as decisions_made,
    AVG(complexity_score) as avg_complexity,
    AVG(decision_correctness) as avg_accuracy,
    AVG(processing_time_ms) as avg_processing_time,
    COUNT(*) FILTER (WHERE npu_accelerated) as npu_accelerated_count,
    COUNT(*) FILTER (WHERE decision_made = 'interleaved') as thinking_enabled_count
FROM decision_tracking
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;

-- Weight effectiveness analysis
CREATE VIEW weight_effectiveness AS
SELECT
    we.version,
    we.word_count_weight,
    we.technical_terms_weight,
    we.multi_step_weight,
    we.accuracy_score,
    we.avg_complexity_score,
    we.active,
    COUNT(dt.id) as decisions_count,
    AVG(dt.decision_correctness) as actual_accuracy
FROM weight_evolution we
LEFT JOIN decision_tracking dt ON dt.created_at >= we.deployed_at
    AND dt.created_at < COALESCE(
        (SELECT MIN(we2.deployed_at) FROM weight_evolution we2 WHERE we2.deployed_at > we.deployed_at),
        NOW()
    )
GROUP BY we.version, we.word_count_weight, we.technical_terms_weight,
         we.multi_step_weight, we.accuracy_score, we.avg_complexity_score, we.active
ORDER BY we.version DESC;

-- Complexity score distribution analysis
CREATE VIEW complexity_distribution AS
SELECT
    CASE
        WHEN complexity_score < 0.1 THEN '0.0-0.1'
        WHEN complexity_score < 0.2 THEN '0.1-0.2'
        WHEN complexity_score < 0.3 THEN '0.2-0.3'
        WHEN complexity_score < 0.4 THEN '0.3-0.4'
        WHEN complexity_score < 0.5 THEN '0.4-0.5'
        WHEN complexity_score < 0.6 THEN '0.5-0.6'
        WHEN complexity_score < 0.7 THEN '0.6-0.7'
        WHEN complexity_score < 0.8 THEN '0.7-0.8'
        WHEN complexity_score < 0.9 THEN '0.8-0.9'
        ELSE '0.9-1.0'
    END as complexity_range,
    COUNT(*) as decision_count,
    AVG(decision_correctness) as avg_accuracy,
    AVG(processing_time_ms) as avg_processing_time
FROM decision_tracking
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY complexity_range
ORDER BY complexity_range;

-- ================================
-- 6. INITIAL DATA AND FUNCTIONS
-- ================================

-- Insert initial weight configuration
INSERT INTO weight_evolution (
    version,
    word_count_weight,
    technical_terms_weight,
    multi_step_weight,
    question_weight,
    agent_coordination_weight,
    active,
    learning_algorithm,
    optimization_target,
    deployed_at
) VALUES (
    1,
    0.002,  -- Current conservative weight
    0.1,    -- Current conservative weight
    0.1,    -- Current conservative weight
    0.1,    -- Current conservative weight
    0.15,   -- Current conservative weight
    TRUE,   -- Start as active
    'baseline',
    'accuracy_optimization',
    NOW()
);

-- Function to get current active weights
CREATE OR REPLACE FUNCTION get_current_weights()
RETURNS TABLE(
    word_count_weight REAL,
    technical_terms_weight REAL,
    multi_step_weight REAL,
    question_weight REAL,
    agent_coordination_weight REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        we.word_count_weight,
        we.technical_terms_weight,
        we.multi_step_weight,
        we.question_weight,
        we.agent_coordination_weight
    FROM weight_evolution we
    WHERE we.active = TRUE
    ORDER BY we.deployed_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to deploy new weight configuration
CREATE OR REPLACE FUNCTION deploy_new_weights(
    p_word_count_weight REAL,
    p_technical_terms_weight REAL,
    p_multi_step_weight REAL,
    p_question_weight REAL,
    p_agent_coordination_weight REAL,
    p_learning_algorithm VARCHAR(50) DEFAULT 'ml_optimization'
) RETURNS INTEGER AS $$
DECLARE
    new_version INTEGER;
BEGIN
    -- Deactivate current weights
    UPDATE weight_evolution SET active = FALSE WHERE active = TRUE;

    -- Get next version number
    SELECT COALESCE(MAX(version), 0) + 1 INTO new_version FROM weight_evolution;

    -- Insert new weight configuration
    INSERT INTO weight_evolution (
        version,
        word_count_weight,
        technical_terms_weight,
        multi_step_weight,
        question_weight,
        agent_coordination_weight,
        active,
        learning_algorithm,
        optimization_target,
        deployed_at
    ) VALUES (
        new_version,
        p_word_count_weight,
        p_technical_terms_weight,
        p_multi_step_weight,
        p_question_weight,
        p_agent_coordination_weight,
        TRUE,
        p_learning_algorithm,
        'auto_calibrated_accuracy',
        NOW()
    );

    RETURN new_version;
END;
$$ LANGUAGE plpgsql;

-- ================================
-- 7. MONITORING AND ALERTS
-- ================================

-- Function to check calibration health
CREATE OR REPLACE FUNCTION check_calibration_health()
RETURNS TABLE(
    health_status VARCHAR(20),
    accuracy_score REAL,
    score_distribution_health VARCHAR(20),
    recent_decisions INTEGER,
    recommendations TEXT
) AS $$
DECLARE
    recent_accuracy REAL;
    score_variance REAL;
    recent_count INTEGER;
    health TEXT := 'healthy';
    recommendations TEXT := '';
BEGIN
    -- Check recent accuracy
    SELECT AVG(decision_correctness), COUNT(*)
    INTO recent_accuracy, recent_count
    FROM decision_tracking
    WHERE created_at >= NOW() - INTERVAL '1 hour';

    -- Check score distribution
    SELECT VARIANCE(complexity_score)
    INTO score_variance
    FROM decision_tracking
    WHERE created_at >= NOW() - INTERVAL '24 hours';

    -- Determine health status
    IF recent_accuracy < 0.7 THEN
        health := 'poor';
        recommendations := 'Consider weight recalibration. ';
    ELSIF recent_accuracy < 0.85 THEN
        health := 'fair';
        recommendations := 'Monitor accuracy trends. ';
    END IF;

    IF score_variance < 0.01 THEN
        recommendations := recommendations || 'Complexity scores too conservative, increase weights. ';
    ELSIF score_variance > 0.1 THEN
        recommendations := recommendations || 'Complexity scores too variable, stabilize weights. ';
    END IF;

    RETURN QUERY SELECT
        health,
        COALESCE(recent_accuracy, 0.0),
        CASE
            WHEN score_variance < 0.01 THEN 'conservative'
            WHEN score_variance > 0.1 THEN 'variable'
            ELSE 'healthy'
        END,
        COALESCE(recent_count, 0),
        recommendations;
END;
$$ LANGUAGE plpgsql;

-- ================================
-- 8. SAMPLE DATA FOR TESTING
-- ================================

-- Insert sample decision data for testing calibration
INSERT INTO decision_tracking (
    session_id, task_text, task_hash, complexity_score, decision_made,
    confidence, processing_time_ms, word_count, question_count,
    technical_terms, multi_step_indicators, agent_recommendations,
    actual_complexity, decision_correctness
) VALUES
    ('test_session_1', 'What is 2 + 2?', MD5('What is 2 + 2?'), 0.1, 'no_thinking', 0.9, 45.2, 4, 1, 0, 0, '{}', 0.1, 1.0),
    ('test_session_1', 'Design a microservices architecture with security', MD5('Design a microservices architecture with security'), 0.1, 'no_thinking', 0.9, 67.8, 8, 0, 3, 1, '{security,architecture}', 0.8, 0.0),
    ('test_session_2', 'Debug this complex Python function with multiple issues', MD5('Debug this complex Python function with multiple issues'), 0.1, 'no_thinking', 0.9, 58.3, 9, 0, 2, 1, '{performance}', 0.6, 0.3),
    ('test_session_2', 'Coordinate multiple agents for distributed system implementation', MD5('Coordinate multiple agents for distributed system implementation'), 0.0, 'interleaved', 1.0, 89.1, 9, 0, 3, 2, '{security,architecture,performance}', 0.9, 1.0);

-- Update embeddings (would be populated by actual system)
UPDATE decision_tracking SET task_embedding = ARRAY[random()]::real[]::vector(256);

-- ================================
-- 9. CALIBRATION FUNCTIONS
-- ================================

-- Function to calculate optimal weights based on current data
CREATE OR REPLACE FUNCTION calculate_optimal_weights()
RETURNS TABLE(
    optimal_word_count_weight REAL,
    optimal_technical_terms_weight REAL,
    optimal_multi_step_weight REAL,
    optimal_question_weight REAL,
    optimal_agent_coordination_weight REAL,
    expected_accuracy REAL,
    confidence REAL
) AS $$
DECLARE
    sample_count INTEGER;
    current_accuracy REAL;
BEGIN
    -- Get sample count
    SELECT COUNT(*) INTO sample_count FROM decision_tracking WHERE actual_complexity IS NOT NULL;

    -- Need minimum samples for calibration
    IF sample_count < 10 THEN
        -- Return current weights with low confidence
        RETURN QUERY
        SELECT
            we.word_count_weight,
            we.technical_terms_weight,
            we.multi_step_weight,
            we.question_weight,
            we.agent_coordination_weight,
            0.5::REAL,  -- Low expected accuracy
            0.1::REAL   -- Low confidence
        FROM weight_evolution we
        WHERE we.active = TRUE;
        RETURN;
    END IF;

    -- Calculate current accuracy
    SELECT AVG(decision_correctness) INTO current_accuracy
    FROM decision_tracking
    WHERE actual_complexity IS NOT NULL;

    -- Simple optimization: increase weights where we're too conservative
    -- In production, this would use ML algorithms
    RETURN QUERY
    SELECT
        CASE
            WHEN current_accuracy < 0.8 THEN 0.01::REAL  -- Increase from 0.002
            ELSE 0.005::REAL
        END,
        CASE
            WHEN current_accuracy < 0.8 THEN 0.2::REAL   -- Increase from 0.1
            ELSE 0.15::REAL
        END,
        CASE
            WHEN current_accuracy < 0.8 THEN 0.25::REAL  -- Increase from 0.1
            ELSE 0.2::REAL
        END,
        0.15::REAL,  -- Question weight
        0.3::REAL,   -- Agent coordination weight (increase for multi-agent detection)
        LEAST(current_accuracy + 0.1, 1.0)::REAL,  -- Expected improvement
        CASE
            WHEN sample_count > 100 THEN 0.9::REAL
            WHEN sample_count > 50 THEN 0.7::REAL
            ELSE 0.5::REAL
        END;
END;
$$ LANGUAGE plpgsql;

-- Function to auto-deploy optimized weights
CREATE OR REPLACE FUNCTION auto_deploy_optimized_weights()
RETURNS INTEGER AS $$
DECLARE
    optimal_weights RECORD;
    new_version INTEGER;
    current_accuracy REAL;
BEGIN
    -- Get current accuracy
    SELECT AVG(decision_correctness) INTO current_accuracy
    FROM decision_tracking
    WHERE actual_complexity IS NOT NULL
    AND created_at >= NOW() - INTERVAL '24 hours';

    -- Only auto-deploy if accuracy is below threshold
    IF COALESCE(current_accuracy, 1.0) >= 0.85 THEN
        RETURN -1;  -- No deployment needed
    END IF;

    -- Calculate optimal weights
    SELECT * INTO optimal_weights FROM calculate_optimal_weights();

    -- Deploy new weights
    SELECT deploy_new_weights(
        optimal_weights.optimal_word_count_weight,
        optimal_weights.optimal_technical_terms_weight,
        optimal_weights.optimal_multi_step_weight,
        optimal_weights.optimal_question_weight,
        optimal_weights.optimal_agent_coordination_weight,
        'auto_calibration'
    ) INTO new_version;

    RETURN new_version;
END;
$$ LANGUAGE plpgsql;

-- ================================
-- 10. GRANT PERMISSIONS
-- ================================

-- Grant all permissions to claude_agent
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA think_mode_calibration TO claude_agent;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA think_mode_calibration TO claude_agent;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA think_mode_calibration TO claude_agent;

-- Create indexes for production performance
CLUSTER decision_tracking USING idx_decision_tracking_created;
ANALYZE decision_tracking;
ANALYZE weight_evolution;
ANALYZE calibration_metrics;

-- Display setup completion
SELECT 'Think Mode Auto-Calibration Schema Deployment Complete' as status,
       'PostgreSQL Docker Integration Ready' as integration_status,
       'Dynamic Weight Optimization Enabled' as calibration_status;