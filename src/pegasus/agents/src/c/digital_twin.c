/*
 * Digital Twin System - Real-time Predictive Operations
 * <10ms synchronization with physical agents
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <pthread.h>
#include <math.h>
#include <time.h>
#include <immintrin.h>
#include <sys/mman.h>
#include <sys/time.h>
#include <unistd.h>
#include <errno.h>

#define MAX_TWINS 1024
#define MAX_SENSORS 4096
#define MAX_ACTUATORS 2048
#define SYNC_INTERVAL_MS 10
#define PREDICTION_HORIZON_MS 5000
#define STATE_VECTOR_SIZE 256
#define HISTORY_BUFFER_SIZE 10000

// Twin types
typedef enum {
    TWIN_AGENT,
    TWIN_INFRASTRUCTURE,
    TWIN_NETWORK,
    TWIN_WORKLOAD,
    TWIN_ENVIRONMENT
} twin_type_t;

// Sensor types
typedef enum {
    SENSOR_CPU,
    SENSOR_MEMORY,
    SENSOR_NETWORK,
    SENSOR_DISK,
    SENSOR_TEMPERATURE,
    SENSOR_POWER,
    SENSOR_LATENCY,
    SENSOR_THROUGHPUT,
    SENSOR_ERROR_RATE,
    SENSOR_CUSTOM
} sensor_type_t;

// Prediction models
typedef enum {
    MODEL_KALMAN,
    MODEL_LSTM,
    MODEL_GRU,
    MODEL_ARIMA,
    MODEL_PROPHET,
    MODEL_ENSEMBLE
} prediction_model_t;

// Sensor data structure
typedef struct __attribute__((aligned(64))) {
    uint32_t sensor_id;
    sensor_type_t type;
    double value;
    double min_value;
    double max_value;
    uint64_t timestamp_ns;
    double confidence;
    bool is_anomaly;
} sensor_data_t;

// State vector for Kalman filter
typedef struct {
    double state[STATE_VECTOR_SIZE];
    double covariance[STATE_VECTOR_SIZE][STATE_VECTOR_SIZE];
    double process_noise[STATE_VECTOR_SIZE][STATE_VECTOR_SIZE];
    double measurement_noise[STATE_VECTOR_SIZE][STATE_VECTOR_SIZE];
    uint64_t last_update_ns;
} kalman_state_t;

// Digital twin instance
typedef struct {
    uint32_t twin_id;
    char name[128];
    twin_type_t type;
    
    // Current state
    sensor_data_t* sensors[MAX_SENSORS];
    uint32_t sensor_count;
    double state_vector[STATE_VECTOR_SIZE];
    
    // Historical data
    sensor_data_t* history_buffer;
    uint32_t history_index;
    uint32_t history_count;
    
    // Prediction models
    kalman_state_t* kalman;
    void* lstm_model;  // Placeholder for LSTM model
    prediction_model_t active_model;
    
    // Predicted state
    double predicted_state[STATE_VECTOR_SIZE];
    double prediction_confidence;
    uint64_t prediction_timestamp_ns;
    
    // Synchronization
    pthread_mutex_t state_lock;
    pthread_cond_t sync_cond;
    uint64_t last_sync_ns;
    double sync_latency_ms;
    
    // Anomaly detection
    double anomaly_threshold;
    uint32_t anomaly_count;
    bool is_anomalous;
    
    // Control actions
    void (*control_callback)(struct digital_twin*, double* actions);
    double control_actions[32];
    
    bool is_active;
} digital_twin_t;

// Twin registry
typedef struct {
    digital_twin_t* twins[MAX_TWINS];
    uint32_t twin_count;
    pthread_rwlock_t registry_lock;
} twin_registry_t;

// Simulation engine
typedef struct {
    pthread_t simulation_thread;
    pthread_t sync_thread;
    pthread_t prediction_thread;
    bool running;
    uint64_t simulation_time_ns;
    double time_scale;  // 1.0 = real-time, 2.0 = 2x speed
} simulation_engine_t;

// Main digital twin system
typedef struct {
    twin_registry_t* registry;
    simulation_engine_t* simulator;
    
    // Performance metrics
    _Atomic uint64_t total_syncs;
    _Atomic uint64_t sync_failures;
    _Atomic double avg_sync_latency_ms;
    _Atomic double max_sync_latency_ms;
    _Atomic uint64_t predictions_made;
    _Atomic uint64_t anomalies_detected;
    
    // Configuration
    uint32_t sync_interval_ms;
    uint32_t prediction_horizon_ms;
    double anomaly_sensitivity;
    
    FILE* log_file;
} digital_twin_system_t;

static digital_twin_system_t* g_dt_system = NULL;

// High-precision timestamp
static inline uint64_t get_timestamp_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000000000ULL + ts.tv_nsec;
}

// AVX-512 vectorized state update
static void vectorized_state_update(double* state, double* update, uint32_t size) {
    uint32_t vec_size = size / 8;  // 8 doubles per AVX-512 register
    
    for (uint32_t i = 0; i < vec_size; i++) {
        __m512d s = _mm512_load_pd(&state[i * 8]);
        __m512d u = _mm512_load_pd(&update[i * 8]);
        __m512d result = _mm512_add_pd(s, u);
        _mm512_store_pd(&state[i * 8], result);
    }
    
    // Handle remaining elements
    for (uint32_t i = vec_size * 8; i < size; i++) {
        state[i] += update[i];
    }
}

// Kalman filter prediction
static void kalman_predict(kalman_state_t* kalman, double* predicted_state, 
                           double dt_seconds) {
    // State transition matrix (simplified for demo)
    double F[STATE_VECTOR_SIZE][STATE_VECTOR_SIZE];
    memset(F, 0, sizeof(F));
    for (int i = 0; i < STATE_VECTOR_SIZE; i++) {
        F[i][i] = 1.0;  // Identity matrix
        if (i < STATE_VECTOR_SIZE / 2) {
            F[i][i + STATE_VECTOR_SIZE / 2] = dt_seconds;  // Position-velocity coupling
        }
    }
    
    // Predict state: x = F * x
    double temp_state[STATE_VECTOR_SIZE] = {0};
    for (int i = 0; i < STATE_VECTOR_SIZE; i++) {
        for (int j = 0; j < STATE_VECTOR_SIZE; j++) {
            temp_state[i] += F[i][j] * kalman->state[j];
        }
    }
    memcpy(predicted_state, temp_state, sizeof(temp_state));
    
    // Update covariance: P = F * P * F' + Q
    double temp_cov[STATE_VECTOR_SIZE][STATE_VECTOR_SIZE];
    
    // P * F'
    for (int i = 0; i < STATE_VECTOR_SIZE; i++) {
        for (int j = 0; j < STATE_VECTOR_SIZE; j++) {
            temp_cov[i][j] = 0;
            for (int k = 0; k < STATE_VECTOR_SIZE; k++) {
                temp_cov[i][j] += kalman->covariance[i][k] * F[j][k];
            }
        }
    }
    
    // F * (P * F')
    for (int i = 0; i < STATE_VECTOR_SIZE; i++) {
        for (int j = 0; j < STATE_VECTOR_SIZE; j++) {
            kalman->covariance[i][j] = kalman->process_noise[i][j];
            for (int k = 0; k < STATE_VECTOR_SIZE; k++) {
                kalman->covariance[i][j] += F[i][k] * temp_cov[k][j];
            }
        }
    }
}

// Kalman filter update with measurement
static void kalman_update(kalman_state_t* kalman, double* measurement) {
    // Simplified measurement model (H = Identity for demo)
    double innovation[STATE_VECTOR_SIZE];
    double K[STATE_VECTOR_SIZE][STATE_VECTOR_SIZE];  // Kalman gain
    
    // Calculate innovation: y = z - H * x
    for (int i = 0; i < STATE_VECTOR_SIZE; i++) {
        innovation[i] = measurement[i] - kalman->state[i];
    }
    
    // Calculate Kalman gain: K = P * H' * (H * P * H' + R)^-1
    // Simplified for diagonal R
    for (int i = 0; i < STATE_VECTOR_SIZE; i++) {
        for (int j = 0; j < STATE_VECTOR_SIZE; j++) {
            K[i][j] = kalman->covariance[i][j] / 
                     (kalman->covariance[j][j] + kalman->measurement_noise[j][j]);
        }
    }
    
    // Update state: x = x + K * y
    for (int i = 0; i < STATE_VECTOR_SIZE; i++) {
        for (int j = 0; j < STATE_VECTOR_SIZE; j++) {
            kalman->state[i] += K[i][j] * innovation[j];
        }
    }
    
    // Update covariance: P = (I - K * H) * P
    double temp[STATE_VECTOR_SIZE][STATE_VECTOR_SIZE];
    memcpy(temp, kalman->covariance, sizeof(temp));
    
    for (int i = 0; i < STATE_VECTOR_SIZE; i++) {
        for (int j = 0; j < STATE_VECTOR_SIZE; j++) {
            kalman->covariance[i][j] = temp[i][j];
            for (int k = 0; k < STATE_VECTOR_SIZE; k++) {
                kalman->covariance[i][j] -= K[i][k] * temp[k][j];
            }
        }
    }
}

// Anomaly detection using statistical methods
static bool detect_anomaly(digital_twin_t* twin, sensor_data_t* sensor) {
    if (twin->history_count < 100) {
        return false;  // Not enough data
    }
    
    // Calculate mean and standard deviation from history
    double sum = 0, sum_sq = 0;
    uint32_t count = twin->history_count < 1000 ? twin->history_count : 1000;
    
    for (uint32_t i = 0; i < count; i++) {
        uint32_t idx = (twin->history_index - i + HISTORY_BUFFER_SIZE) % HISTORY_BUFFER_SIZE;
        double value = twin->history_buffer[idx].value;
        sum += value;
        sum_sq += value * value;
    }
    
    double mean = sum / count;
    double variance = (sum_sq / count) - (mean * mean);
    double std_dev = sqrt(variance);
    
    // Z-score test
    double z_score = fabs(sensor->value - mean) / (std_dev + 1e-10);
    
    return z_score > twin->anomaly_threshold;
}

// Synchronize twin with physical counterpart
static void synchronize_twin(digital_twin_t* twin) {
    uint64_t start_ns = get_timestamp_ns();
    
    pthread_mutex_lock(&twin->state_lock);
    
    // Collect sensor data
    for (uint32_t i = 0; i < twin->sensor_count; i++) {
        sensor_data_t* sensor = twin->sensors[i];
        
        // Simulate sensor reading (would be actual hardware interface)
        sensor->value = twin->state_vector[i] + 
                       ((double)rand() / RAND_MAX - 0.5) * 0.1;
        sensor->timestamp_ns = start_ns;
        
        // Check for anomalies
        if (detect_anomaly(twin, sensor)) {
            sensor->is_anomaly = true;
            twin->anomaly_count++;
            atomic_fetch_add(&g_dt_system->anomalies_detected, 1);
        }
        
        // Update state vector
        twin->state_vector[i] = sensor->value;
        
        // Store in history
        twin->history_buffer[twin->history_index] = *sensor;
        twin->history_index = (twin->history_index + 1) % HISTORY_BUFFER_SIZE;
        if (twin->history_count < HISTORY_BUFFER_SIZE) {
            twin->history_count++;
        }
    }
    
    // Update Kalman filter if active
    if (twin->active_model == MODEL_KALMAN && twin->kalman) {
        kalman_update(twin->kalman, twin->state_vector);
    }
    
    uint64_t end_ns = get_timestamp_ns();
    twin->sync_latency_ms = (end_ns - start_ns) / 1000000.0;
    twin->last_sync_ns = end_ns;
    
    // Update global metrics
    atomic_fetch_add(&g_dt_system->total_syncs, 1);
    
    double current_avg = atomic_load(&g_dt_system->avg_sync_latency_ms);
    atomic_store(&g_dt_system->avg_sync_latency_ms, 
                current_avg * 0.95 + twin->sync_latency_ms * 0.05);
    
    double current_max = atomic_load(&g_dt_system->max_sync_latency_ms);
    if (twin->sync_latency_ms > current_max) {
        atomic_store(&g_dt_system->max_sync_latency_ms, twin->sync_latency_ms);
    }
    
    pthread_cond_signal(&twin->sync_cond);
    pthread_mutex_unlock(&twin->state_lock);
}

// Predict future state
static void predict_future_state(digital_twin_t* twin) {
    pthread_mutex_lock(&twin->state_lock);
    
    uint64_t current_ns = get_timestamp_ns();
    double dt_seconds = g_dt_system->prediction_horizon_ms / 1000.0;
    
    switch (twin->active_model) {
        case MODEL_KALMAN:
            if (twin->kalman) {
                kalman_predict(twin->kalman, twin->predicted_state, dt_seconds);
                twin->prediction_confidence = 0.9;  // High confidence for Kalman
            }
            break;
            
        case MODEL_ARIMA:
            // Simple linear extrapolation for demo
            for (int i = 0; i < STATE_VECTOR_SIZE; i++) {
                if (twin->history_count > 1) {
                    uint32_t idx1 = (twin->history_index - 1 + HISTORY_BUFFER_SIZE) % 
                                   HISTORY_BUFFER_SIZE;
                    uint32_t idx2 = (twin->history_index - 2 + HISTORY_BUFFER_SIZE) % 
                                   HISTORY_BUFFER_SIZE;
                    double trend = twin->history_buffer[idx1].value - 
                                  twin->history_buffer[idx2].value;
                    twin->predicted_state[i] = twin->state_vector[i] + trend * dt_seconds * 10;
                } else {
                    twin->predicted_state[i] = twin->state_vector[i];
                }
            }
            twin->prediction_confidence = 0.7;
            break;
            
        default:
            // Copy current state as prediction
            memcpy(twin->predicted_state, twin->state_vector, 
                   sizeof(double) * STATE_VECTOR_SIZE);
            twin->prediction_confidence = 0.5;
            break;
    }
    
    twin->prediction_timestamp_ns = current_ns + 
                                   g_dt_system->prediction_horizon_ms * 1000000ULL;
    
    atomic_fetch_add(&g_dt_system->predictions_made, 1);
    
    // Check if control action needed
    if (twin->control_callback) {
        // Simple control logic: if predicted state exceeds thresholds
        bool needs_control = false;
        for (int i = 0; i < STATE_VECTOR_SIZE; i++) {
            if (twin->predicted_state[i] > 0.9 || twin->predicted_state[i] < 0.1) {
                needs_control = true;
                break;
            }
        }
        
        if (needs_control) {
            twin->control_callback(twin, twin->control_actions);
        }
    }
    
    pthread_mutex_unlock(&twin->state_lock);
}

// Synchronization thread
static void* sync_thread(void* arg) {
    simulation_engine_t* sim = (simulation_engine_t*)arg;
    
    while (sim->running) {
        uint64_t start_ns = get_timestamp_ns();
        
        pthread_rwlock_rdlock(&g_dt_system->registry->registry_lock);
        
        // Synchronize all active twins
        for (uint32_t i = 0; i < g_dt_system->registry->twin_count; i++) {
            digital_twin_t* twin = g_dt_system->registry->twins[i];
            if (twin->is_active) {
                synchronize_twin(twin);
            }
        }
        
        pthread_rwlock_unlock(&g_dt_system->registry->registry_lock);
        
        // Sleep to maintain sync interval
        uint64_t elapsed_ns = get_timestamp_ns() - start_ns;
        uint64_t sleep_ns = g_dt_system->sync_interval_ms * 1000000ULL;
        
        if (elapsed_ns < sleep_ns) {
            usleep((sleep_ns - elapsed_ns) / 1000);
        } else {
            atomic_fetch_add(&g_dt_system->sync_failures, 1);
        }
    }
    
    return NULL;
}

// Prediction thread
static void* prediction_thread(void* arg) {
    simulation_engine_t* sim = (simulation_engine_t*)arg;
    
    while (sim->running) {
        pthread_rwlock_rdlock(&g_dt_system->registry->registry_lock);
        
        // Update predictions for all twins
        for (uint32_t i = 0; i < g_dt_system->registry->twin_count; i++) {
            digital_twin_t* twin = g_dt_system->registry->twins[i];
            if (twin->is_active) {
                predict_future_state(twin);
            }
        }
        
        pthread_rwlock_unlock(&g_dt_system->registry->registry_lock);
        
        usleep(100000);  // 100ms between predictions
    }
    
    return NULL;
}

// Initialize digital twin system
int digital_twin_init(void) {
    g_dt_system = calloc(1, sizeof(digital_twin_system_t));
    if (!g_dt_system) {
        return -1;
    }
    
    // Initialize registry
    g_dt_system->registry = calloc(1, sizeof(twin_registry_t));
    pthread_rwlock_init(&g_dt_system->registry->registry_lock, NULL);
    
    // Initialize simulation engine
    g_dt_system->simulator = calloc(1, sizeof(simulation_engine_t));
    g_dt_system->simulator->running = true;
    g_dt_system->simulator->time_scale = 1.0;
    
    // Set default configuration
    g_dt_system->sync_interval_ms = SYNC_INTERVAL_MS;
    g_dt_system->prediction_horizon_ms = PREDICTION_HORIZON_MS;
    g_dt_system->anomaly_sensitivity = 3.0;  // 3 standard deviations
    
    // Open log file
    g_dt_system->log_file = fopen("digital_twin.log", "w");
    
    // Start threads
    pthread_create(&g_dt_system->simulator->sync_thread, NULL, 
                   sync_thread, g_dt_system->simulator);
    pthread_create(&g_dt_system->simulator->prediction_thread, NULL, 
                   prediction_thread, g_dt_system->simulator);
    
    return 0;
}

// Create new digital twin
digital_twin_t* digital_twin_create(const char* name, twin_type_t type) {
    digital_twin_t* twin = calloc(1, sizeof(digital_twin_t));
    if (!twin) {
        return NULL;
    }
    
    pthread_rwlock_wrlock(&g_dt_system->registry->registry_lock);
    
    twin->twin_id = g_dt_system->registry->twin_count;
    strncpy(twin->name, name, sizeof(twin->name) - 1);
    twin->type = type;
    
    // Allocate history buffer
    twin->history_buffer = calloc(HISTORY_BUFFER_SIZE, sizeof(sensor_data_t));
    
    // Initialize Kalman filter
    twin->kalman = calloc(1, sizeof(kalman_state_t));
    // Initialize with small process and measurement noise
    for (int i = 0; i < STATE_VECTOR_SIZE; i++) {
        twin->kalman->process_noise[i][i] = 0.01;
        twin->kalman->measurement_noise[i][i] = 0.1;
        twin->kalman->covariance[i][i] = 1.0;
    }
    twin->active_model = MODEL_KALMAN;
    
    // Set default anomaly threshold
    twin->anomaly_threshold = g_dt_system->anomaly_sensitivity;
    
    pthread_mutex_init(&twin->state_lock, NULL);
    pthread_cond_init(&twin->sync_cond, NULL);
    
    twin->is_active = true;
    
    // Add to registry
    g_dt_system->registry->twins[g_dt_system->registry->twin_count++] = twin;
    
    pthread_rwlock_unlock(&g_dt_system->registry->registry_lock);
    
    return twin;
}

// Add sensor to twin
int digital_twin_add_sensor(digital_twin_t* twin, sensor_type_t type, 
                           double min_val, double max_val) {
    if (twin->sensor_count >= MAX_SENSORS) {
        return -1;
    }
    
    sensor_data_t* sensor = calloc(1, sizeof(sensor_data_t));
    sensor->sensor_id = twin->sensor_count;
    sensor->type = type;
    sensor->min_value = min_val;
    sensor->max_value = max_val;
    sensor->value = (min_val + max_val) / 2.0;  // Initialize to midpoint
    
    pthread_mutex_lock(&twin->state_lock);
    twin->sensors[twin->sensor_count++] = sensor;
    pthread_mutex_unlock(&twin->state_lock);
    
    return 0;
}

// Get twin state
void digital_twin_get_state(digital_twin_t* twin, double* state_out, 
                           double* predicted_out) {
    pthread_mutex_lock(&twin->state_lock);
    
    if (state_out) {
        memcpy(state_out, twin->state_vector, sizeof(double) * STATE_VECTOR_SIZE);
    }
    
    if (predicted_out) {
        memcpy(predicted_out, twin->predicted_state, sizeof(double) * STATE_VECTOR_SIZE);
    }
    
    pthread_mutex_unlock(&twin->state_lock);
}

// Get system statistics
void digital_twin_get_stats(uint64_t* total_syncs, double* avg_latency_ms,
                           uint64_t* predictions, uint64_t* anomalies) {
    if (total_syncs) {
        *total_syncs = atomic_load(&g_dt_system->total_syncs);
    }
    if (avg_latency_ms) {
        *avg_latency_ms = atomic_load(&g_dt_system->avg_sync_latency_ms);
    }
    if (predictions) {
        *predictions = atomic_load(&g_dt_system->predictions_made);
    }
    if (anomalies) {
        *anomalies = atomic_load(&g_dt_system->anomalies_detected);
    }
}

// Shutdown digital twin system
void digital_twin_shutdown(void) {
    g_dt_system->simulator->running = false;
    
    // Wait for threads
    pthread_join(g_dt_system->simulator->sync_thread, NULL);
    pthread_join(g_dt_system->simulator->prediction_thread, NULL);
    
    // Cleanup twins
    pthread_rwlock_wrlock(&g_dt_system->registry->registry_lock);
    
    for (uint32_t i = 0; i < g_dt_system->registry->twin_count; i++) {
        digital_twin_t* twin = g_dt_system->registry->twins[i];
        
        // Free sensors
        for (uint32_t j = 0; j < twin->sensor_count; j++) {
            free(twin->sensors[j]);
        }
        
        // Free buffers
        free(twin->history_buffer);
        free(twin->kalman);
        
        pthread_mutex_destroy(&twin->state_lock);
        pthread_cond_destroy(&twin->sync_cond);
        
        free(twin);
    }
    
    pthread_rwlock_unlock(&g_dt_system->registry->registry_lock);
    pthread_rwlock_destroy(&g_dt_system->registry->registry_lock);
    
    // Close log
    if (g_dt_system->log_file) {
        fclose(g_dt_system->log_file);
    }
    
    free(g_dt_system->registry);
    free(g_dt_system->simulator);
    free(g_dt_system);
    g_dt_system = NULL;
}

// Example control callback
static void example_control_callback(digital_twin_t* twin, double* actions) {
    printf("Control action triggered for twin: %s\n", twin->name);
    
    // Simple proportional control
    for (int i = 0; i < 32; i++) {
        if (twin->predicted_state[i] > 0.8) {
            actions[i] = -0.1;  // Reduce
        } else if (twin->predicted_state[i] < 0.2) {
            actions[i] = 0.1;   // Increase
        } else {
            actions[i] = 0.0;   // No action
        }
    }
}

// Demo function
// int main_disabled(int argc, char** argv) {
    printf("Digital Twin System - <10ms Synchronization\n");
    printf("============================================\n\n");
    
    // Initialize system
    if (digital_twin_init() != 0) {
        fprintf(stderr, "Failed to initialize digital twin system\n");
        return 1;
    }
    
    // Create agent twins
    digital_twin_t* web_twin = digital_twin_create("web-agent", TWIN_AGENT);
    digital_twin_t* db_twin = digital_twin_create("database-agent", TWIN_AGENT);
    digital_twin_t* net_twin = digital_twin_create("network", TWIN_NETWORK);
    
    // Add sensors
    digital_twin_add_sensor(web_twin, SENSOR_CPU, 0.0, 100.0);
    digital_twin_add_sensor(web_twin, SENSOR_MEMORY, 0.0, 100.0);
    digital_twin_add_sensor(web_twin, SENSOR_LATENCY, 0.0, 1000.0);
    digital_twin_add_sensor(web_twin, SENSOR_THROUGHPUT, 0.0, 10000.0);
    
    digital_twin_add_sensor(db_twin, SENSOR_CPU, 0.0, 100.0);
    digital_twin_add_sensor(db_twin, SENSOR_DISK, 0.0, 100.0);
    digital_twin_add_sensor(db_twin, SENSOR_LATENCY, 0.0, 100.0);
    
    digital_twin_add_sensor(net_twin, SENSOR_NETWORK, 0.0, 10000.0);
    digital_twin_add_sensor(net_twin, SENSOR_ERROR_RATE, 0.0, 1.0);
    
    // Set control callback
    web_twin->control_callback = example_control_callback;
    
    printf("Created 3 digital twins with sensors\n");
    printf("Starting synchronization and prediction...\n\n");
    
    // Run for demonstration
    for (int i = 0; i < 10; i++) {
        sleep(1);
        
        // Get statistics
        uint64_t syncs, predictions, anomalies;
        double avg_latency;
        digital_twin_get_stats(&syncs, &avg_latency, &predictions, &anomalies);
        
        printf("Iteration %d: Syncs=%lu, Avg Latency=%.2fms, Predictions=%lu, Anomalies=%lu\n",
               i + 1, syncs, avg_latency, predictions, anomalies);
        
        // Check sync latency target
        if (avg_latency < 10.0) {
            printf("✓ Meeting <10ms sync target (%.2fms)\n", avg_latency);
        }
    }
    
    printf("\nDigital twin demonstration complete\n");
    
    // Shutdown
    digital_twin_shutdown();
    
    return 0;
}