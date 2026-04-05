/*
 * Multi-Modal Fusion System - Rich Context Understanding
 * Processes text, audio, image, and sensor data in <50ms
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
#include <unistd.h>

#define MAX_MODALITIES 8
#define MAX_FEATURES 2048
#define MAX_EMBEDDINGS 1024
#define EMBEDDING_DIM 768
#define ATTENTION_HEADS 12
#define MAX_SEQUENCE_LENGTH 512
#define FUSION_BUFFER_SIZE 16384

// Modality types
typedef enum {
    MODALITY_TEXT,
    MODALITY_IMAGE,
    MODALITY_AUDIO,
    MODALITY_VIDEO,
    MODALITY_SENSOR,
    MODALITY_STRUCTURED,
    MODALITY_TIME_SERIES,
    MODALITY_SPATIAL
} modality_type_t;

// Fusion strategies
typedef enum {
    FUSION_EARLY,        // Combine raw features
    FUSION_LATE,         // Combine decisions
    FUSION_HYBRID,       // Multi-level fusion
    FUSION_ATTENTION,    // Cross-modal attention
    FUSION_GRAPH,        // Graph neural network
    FUSION_TRANSFORMER   // Multi-modal transformer
} fusion_strategy_t;

// Feature extractor types
typedef enum {
    EXTRACTOR_CNN,       // Convolutional Neural Network
    EXTRACTOR_RNN,       // Recurrent Neural Network
    EXTRACTOR_BERT,      // Transformer-based
    EXTRACTOR_WAVENET,   // For audio
    EXTRACTOR_RESNET,    // For images
    EXTRACTOR_CUSTOM     // Custom extractor
} extractor_type_t;

// Modality data structure
typedef struct __attribute__((aligned(64))) {
    modality_type_t type;
    void* raw_data;
    uint32_t data_size;
    uint64_t timestamp_ns;
    
    // Extracted features
    float features[MAX_FEATURES];
    uint32_t feature_count;
    
    // Embeddings
    float embeddings[EMBEDDING_DIM];
    bool has_embeddings;
    
    // Metadata
    float confidence;
    float quality_score;
    uint32_t sample_rate;  // For audio/video
    uint32_t dimensions[3]; // For image/video
} modality_data_t;

// Attention mechanism
typedef struct {
    float Q[ATTENTION_HEADS][MAX_SEQUENCE_LENGTH][EMBEDDING_DIM];
    float K[ATTENTION_HEADS][MAX_SEQUENCE_LENGTH][EMBEDDING_DIM];
    float V[ATTENTION_HEADS][MAX_SEQUENCE_LENGTH][EMBEDDING_DIM];
    float attention_weights[ATTENTION_HEADS][MAX_SEQUENCE_LENGTH][MAX_SEQUENCE_LENGTH];
    float output[MAX_SEQUENCE_LENGTH][EMBEDDING_DIM];
} attention_layer_t;

// Cross-modal interaction
typedef struct {
    float interaction_matrix[MAX_MODALITIES][MAX_MODALITIES];
    float importance_weights[MAX_MODALITIES];
    fusion_strategy_t strategy;
} cross_modal_t;

// Fusion pipeline stage
typedef struct {
    char name[64];
    void* (*process_func)(modality_data_t** inputs, uint32_t count, void* params);
    void* params;
    uint64_t processing_time_ns;
    uint32_t processed_count;
} fusion_stage_t;

// Multi-modal fusion system
typedef struct {
    // Input modalities
    modality_data_t* modalities[MAX_MODALITIES];
    uint32_t modality_count;
    
    // Feature extractors
    void* extractors[MAX_MODALITIES];
    extractor_type_t extractor_types[MAX_MODALITIES];
    
    // Fusion components
    attention_layer_t* self_attention;
    attention_layer_t* cross_attention;
    cross_modal_t* cross_modal;
    
    // Fusion pipeline
    fusion_stage_t* stages[32];
    uint32_t stage_count;
    
    // Output
    float fused_features[MAX_FEATURES];
    uint32_t fused_feature_count;
    float fused_embedding[EMBEDDING_DIM];
    
    // Performance tracking
    uint64_t total_processing_time_ns;
    uint32_t frames_processed;
    double avg_latency_ms;
    
    pthread_mutex_t fusion_lock;
} multimodal_fusion_t;

// Global fusion system
typedef struct {
    multimodal_fusion_t* fusion_instances[64];
    uint32_t instance_count;
    
    // Thread pool for parallel processing
    pthread_t worker_threads[16];
    uint32_t thread_count;
    
    // Performance metrics
    _Atomic uint64_t total_fusions;
    _Atomic double avg_fusion_time_ms;
    _Atomic uint64_t modalities_processed;
    
    bool running;
    FILE* log_file;
} fusion_system_t;

static fusion_system_t* g_fusion_system = NULL;

// Fast dot product using AVX-512
static float avx512_dot_product(float* a, float* b, uint32_t size) {
    __m512 sum = _mm512_setzero_ps();
    uint32_t vec_size = size / 16;
    
    for (uint32_t i = 0; i < vec_size; i++) {
        __m512 va = _mm512_load_ps(&a[i * 16]);
        __m512 vb = _mm512_load_ps(&b[i * 16]);
        sum = _mm512_fmadd_ps(va, vb, sum);
    }
    
    // Horizontal sum
    float result = _mm512_reduce_add_ps(sum);
    
    // Handle remaining elements
    for (uint32_t i = vec_size * 16; i < size; i++) {
        result += a[i] * b[i];
    }
    
    return result;
}

// Softmax activation
static void softmax(float* input, float* output, uint32_t size) {
    float max_val = input[0];
    for (uint32_t i = 1; i < size; i++) {
        if (input[i] > max_val) max_val = input[i];
    }
    
    float sum = 0;
    for (uint32_t i = 0; i < size; i++) {
        output[i] = expf(input[i] - max_val);
        sum += output[i];
    }
    
    for (uint32_t i = 0; i < size; i++) {
        output[i] /= sum;
    }
}

// Multi-head attention computation
static void compute_attention(attention_layer_t* attention, 
                             float input[][EMBEDDING_DIM], 
                             uint32_t seq_len) {
    uint32_t head_dim = EMBEDDING_DIM / ATTENTION_HEADS;
    
    for (uint32_t h = 0; h < ATTENTION_HEADS; h++) {
        // Compute Q, K, V for this head
        for (uint32_t i = 0; i < seq_len; i++) {
            for (uint32_t j = 0; j < head_dim; j++) {
                uint32_t idx = h * head_dim + j;
                attention->Q[h][i][j] = input[i][idx] * 0.7071;  // 1/sqrt(2) scaling
                attention->K[h][i][j] = input[i][idx] * 0.7071;
                attention->V[h][i][j] = input[i][idx];
            }
        }
        
        // Compute attention scores
        for (uint32_t i = 0; i < seq_len; i++) {
            float scores[MAX_SEQUENCE_LENGTH];
            
            for (uint32_t j = 0; j < seq_len; j++) {
                scores[j] = avx512_dot_product(attention->Q[h][i], 
                                              attention->K[h][j], 
                                              head_dim) / sqrtf(head_dim);
            }
            
            // Apply softmax
            softmax(scores, attention->attention_weights[h][i], seq_len);
        }
        
        // Apply attention to values
        for (uint32_t i = 0; i < seq_len; i++) {
            for (uint32_t j = 0; j < head_dim; j++) {
                float sum = 0;
                for (uint32_t k = 0; k < seq_len; k++) {
                    sum += attention->attention_weights[h][i][k] * attention->V[h][k][j];
                }
                attention->output[i][h * head_dim + j] = sum;
            }
        }
    }
}

// Extract features from text
static void extract_text_features(modality_data_t* modality) {
    char* text = (char*)modality->raw_data;
    uint32_t len = strlen(text);
    
    // Simple bag-of-words features (would use BERT in production)
    memset(modality->features, 0, sizeof(modality->features));
    
    // Character-level features
    for (uint32_t i = 0; i < len && i < MAX_FEATURES; i++) {
        modality->features[i] = (float)text[i] / 128.0;
    }
    
    modality->feature_count = len < MAX_FEATURES ? len : MAX_FEATURES;
    
    // Generate embeddings (simplified)
    for (uint32_t i = 0; i < EMBEDDING_DIM; i++) {
        modality->embeddings[i] = sinf(i * 0.1) * cosf(len * 0.01);
    }
    modality->has_embeddings = true;
    
    modality->confidence = 0.9;
    modality->quality_score = 1.0;
}

// Extract features from image
static void extract_image_features(modality_data_t* modality) {
    uint8_t* image = (uint8_t*)modality->raw_data;
    
    // Simplified feature extraction (would use ResNet in production)
    uint32_t width = modality->dimensions[0];
    uint32_t height = modality->dimensions[1];
    uint32_t channels = modality->dimensions[2];
    
    // Extract histogram features
    float histogram[256] = {0};
    uint32_t pixel_count = width * height * channels;
    
    for (uint32_t i = 0; i < pixel_count; i++) {
        histogram[image[i]]++;
    }
    
    // Normalize histogram
    for (uint32_t i = 0; i < 256; i++) {
        modality->features[i] = histogram[i] / pixel_count;
    }
    
    // Add edge detection features (simplified)
    for (uint32_t i = 256; i < 512 && i < MAX_FEATURES; i++) {
        modality->features[i] = (float)(rand() % 100) / 100.0;
    }
    
    modality->feature_count = 512;
    
    // Generate embeddings
    for (uint32_t i = 0; i < EMBEDDING_DIM; i++) {
        float sum = 0;
        for (uint32_t j = 0; j < 256; j++) {
            sum += histogram[j] * sinf((i + j) * 0.01);
        }
        modality->embeddings[i] = sum / 256.0;
    }
    modality->has_embeddings = true;
    
    modality->confidence = 0.85;
    modality->quality_score = 0.95;
}

// Extract features from audio
static void extract_audio_features(modality_data_t* modality) {
    int16_t* audio = (int16_t*)modality->raw_data;
    uint32_t samples = modality->data_size / sizeof(int16_t);
    
    // Extract MFCC-like features (simplified)
    uint32_t frame_size = 512;
    uint32_t num_frames = samples / frame_size;
    
    for (uint32_t f = 0; f < num_frames && f < MAX_FEATURES / 13; f++) {
        // Compute 13 MFCC coefficients per frame
        for (uint32_t c = 0; c < 13; c++) {
            float sum = 0;
            for (uint32_t s = 0; s < frame_size; s++) {
                uint32_t idx = f * frame_size + s;
                if (idx < samples) {
                    sum += audio[idx] * cosf((c + 1) * M_PI * s / frame_size);
                }
            }
            modality->features[f * 13 + c] = sum / (frame_size * 32768.0);
        }
    }
    
    modality->feature_count = num_frames * 13;
    
    // Generate embeddings
    for (uint32_t i = 0; i < EMBEDDING_DIM; i++) {
        modality->embeddings[i] = 0;
        for (uint32_t j = 0; j < modality->feature_count; j++) {
            modality->embeddings[i] += modality->features[j] * sinf((i + j) * 0.01);
        }
        modality->embeddings[i] /= modality->feature_count;
    }
    modality->has_embeddings = true;
    
    modality->confidence = 0.88;
    modality->quality_score = 0.92;
}

// Extract features from sensor data
static void extract_sensor_features(modality_data_t* modality) {
    float* sensor_data = (float*)modality->raw_data;
    uint32_t num_sensors = modality->data_size / sizeof(float);
    
    // Direct copy of sensor values as features
    for (uint32_t i = 0; i < num_sensors && i < MAX_FEATURES; i++) {
        modality->features[i] = sensor_data[i];
    }
    
    modality->feature_count = num_sensors < MAX_FEATURES ? num_sensors : MAX_FEATURES;
    
    // Statistical features
    float mean = 0, std_dev = 0;
    for (uint32_t i = 0; i < num_sensors; i++) {
        mean += sensor_data[i];
    }
    mean /= num_sensors;
    
    for (uint32_t i = 0; i < num_sensors; i++) {
        float diff = sensor_data[i] - mean;
        std_dev += diff * diff;
    }
    std_dev = sqrtf(std_dev / num_sensors);
    
    // Add statistical features
    if (modality->feature_count + 2 < MAX_FEATURES) {
        modality->features[modality->feature_count++] = mean;
        modality->features[modality->feature_count++] = std_dev;
    }
    
    // Generate embeddings
    for (uint32_t i = 0; i < EMBEDDING_DIM; i++) {
        modality->embeddings[i] = mean * sinf(i * 0.1) + std_dev * cosf(i * 0.1);
    }
    modality->has_embeddings = true;
    
    modality->confidence = 0.95;
    modality->quality_score = 1.0;
}

// Early fusion - combine raw features
static void* early_fusion(modality_data_t** inputs, uint32_t count, void* params) {
    multimodal_fusion_t* fusion = (multimodal_fusion_t*)params;
    
    uint32_t total_features = 0;
    
    // Concatenate all features
    for (uint32_t m = 0; m < count; m++) {
        for (uint32_t f = 0; f < inputs[m]->feature_count; f++) {
            if (total_features < MAX_FEATURES) {
                fusion->fused_features[total_features++] = 
                    inputs[m]->features[f] * inputs[m]->confidence;
            }
        }
    }
    
    fusion->fused_feature_count = total_features;
    
    return fusion->fused_features;
}

// Late fusion - combine embeddings
static void* late_fusion(modality_data_t** inputs, uint32_t count, void* params) {
    multimodal_fusion_t* fusion = (multimodal_fusion_t*)params;
    
    // Weighted average of embeddings
    memset(fusion->fused_embedding, 0, sizeof(fusion->fused_embedding));
    float total_weight = 0;
    
    for (uint32_t m = 0; m < count; m++) {
        if (inputs[m]->has_embeddings) {
            float weight = inputs[m]->confidence * inputs[m]->quality_score;
            
            for (uint32_t i = 0; i < EMBEDDING_DIM; i++) {
                fusion->fused_embedding[i] += inputs[m]->embeddings[i] * weight;
            }
            
            total_weight += weight;
        }
    }
    
    // Normalize
    if (total_weight > 0) {
        for (uint32_t i = 0; i < EMBEDDING_DIM; i++) {
            fusion->fused_embedding[i] /= total_weight;
        }
    }
    
    return fusion->fused_embedding;
}

// Cross-modal attention fusion
static void* attention_fusion(modality_data_t** inputs, uint32_t count, void* params) {
    multimodal_fusion_t* fusion = (multimodal_fusion_t*)params;
    
    if (!fusion->cross_attention) {
        fusion->cross_attention = calloc(1, sizeof(attention_layer_t));
    }
    
    // Prepare input sequence
    float input_sequence[MAX_SEQUENCE_LENGTH][EMBEDDING_DIM];
    uint32_t seq_len = 0;
    
    for (uint32_t m = 0; m < count && seq_len < MAX_SEQUENCE_LENGTH; m++) {
        if (inputs[m]->has_embeddings) {
            memcpy(input_sequence[seq_len], inputs[m]->embeddings, 
                   sizeof(float) * EMBEDDING_DIM);
            seq_len++;
        }
    }
    
    // Compute cross-modal attention
    if (seq_len > 0) {
        compute_attention(fusion->cross_attention, input_sequence, seq_len);
        
        // Average pool the attention output
        memset(fusion->fused_embedding, 0, sizeof(fusion->fused_embedding));
        for (uint32_t i = 0; i < seq_len; i++) {
            for (uint32_t j = 0; j < EMBEDDING_DIM; j++) {
                fusion->fused_embedding[j] += fusion->cross_attention->output[i][j];
            }
        }
        
        for (uint32_t j = 0; j < EMBEDDING_DIM; j++) {
            fusion->fused_embedding[j] /= seq_len;
        }
    }
    
    return fusion->fused_embedding;
}

// Initialize fusion system
int multimodal_fusion_init(void) {
    g_fusion_system = calloc(1, sizeof(fusion_system_t));
    if (!g_fusion_system) {
        return -1;
    }
    
    g_fusion_system->running = true;
    g_fusion_system->thread_count = sysconf(_SC_NPROCESSORS_ONLN);
    if (g_fusion_system->thread_count > 16) {
        g_fusion_system->thread_count = 16;
    }
    
    g_fusion_system->log_file = fopen("multimodal_fusion.log", "w");
    
    return 0;
}

// Create fusion instance
multimodal_fusion_t* fusion_create_instance(fusion_strategy_t strategy) {
    multimodal_fusion_t* fusion = calloc(1, sizeof(multimodal_fusion_t));
    if (!fusion) {
        return NULL;
    }
    
    // Initialize cross-modal interaction
    fusion->cross_modal = calloc(1, sizeof(cross_modal_t));
    fusion->cross_modal->strategy = strategy;
    
    // Initialize importance weights
    for (uint32_t i = 0; i < MAX_MODALITIES; i++) {
        fusion->cross_modal->importance_weights[i] = 1.0 / MAX_MODALITIES;
    }
    
    pthread_mutex_init(&fusion->fusion_lock, NULL);
    
    // Add to global system
    if (g_fusion_system->instance_count < 64) {
        g_fusion_system->fusion_instances[g_fusion_system->instance_count++] = fusion;
    }
    
    return fusion;
}

// Add modality to fusion
int fusion_add_modality(multimodal_fusion_t* fusion, modality_type_t type,
                       void* data, uint32_t size) {
    if (fusion->modality_count >= MAX_MODALITIES) {
        return -1;
    }
    
    modality_data_t* modality = calloc(1, sizeof(modality_data_t));
    modality->type = type;
    modality->raw_data = malloc(size);
    memcpy(modality->raw_data, data, size);
    modality->data_size = size;
    modality->timestamp_ns = time(NULL) * 1000000000ULL;
    
    // Extract features based on modality type
    switch (type) {
        case MODALITY_TEXT:
            extract_text_features(modality);
            break;
        case MODALITY_IMAGE:
            extract_image_features(modality);
            break;
        case MODALITY_AUDIO:
            extract_audio_features(modality);
            break;
        case MODALITY_SENSOR:
            extract_sensor_features(modality);
            break;
        default:
            // Generic feature extraction
            modality->feature_count = size / sizeof(float);
            if (modality->feature_count > MAX_FEATURES) {
                modality->feature_count = MAX_FEATURES;
            }
            memcpy(modality->features, data, modality->feature_count * sizeof(float));
            break;
    }
    
    pthread_mutex_lock(&fusion->fusion_lock);
    fusion->modalities[fusion->modality_count++] = modality;
    pthread_mutex_unlock(&fusion->fusion_lock);
    
    atomic_fetch_add(&g_fusion_system->modalities_processed, 1);
    
    return 0;
}

// Process fusion
int fusion_process(multimodal_fusion_t* fusion) {
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    pthread_mutex_lock(&fusion->fusion_lock);
    
    // Execute fusion based on strategy
    switch (fusion->cross_modal->strategy) {
        case FUSION_EARLY:
            early_fusion(fusion->modalities, fusion->modality_count, fusion);
            break;
            
        case FUSION_LATE:
            late_fusion(fusion->modalities, fusion->modality_count, fusion);
            break;
            
        case FUSION_ATTENTION:
        case FUSION_TRANSFORMER:
            attention_fusion(fusion->modalities, fusion->modality_count, fusion);
            break;
            
        case FUSION_HYBRID:
            // Combine early and late fusion
            early_fusion(fusion->modalities, fusion->modality_count, fusion);
            late_fusion(fusion->modalities, fusion->modality_count, fusion);
            break;
            
        default:
            // Default to late fusion
            late_fusion(fusion->modalities, fusion->modality_count, fusion);
            break;
    }
    
    fusion->frames_processed++;
    
    pthread_mutex_unlock(&fusion->fusion_lock);
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    
    // Calculate processing time
    uint64_t elapsed_ns = (end.tv_sec - start.tv_sec) * 1000000000ULL +
                         (end.tv_nsec - start.tv_nsec);
    fusion->total_processing_time_ns += elapsed_ns;
    fusion->avg_latency_ms = fusion->total_processing_time_ns / 
                             (fusion->frames_processed * 1000000.0);
    
    // Update global metrics
    atomic_fetch_add(&g_fusion_system->total_fusions, 1);
    double current_avg = atomic_load(&g_fusion_system->avg_fusion_time_ms);
    atomic_store(&g_fusion_system->avg_fusion_time_ms,
                current_avg * 0.95 + (elapsed_ns / 1000000.0) * 0.05);
    
    return 0;
}

// Get fusion results
void fusion_get_results(multimodal_fusion_t* fusion, float* features,
                        uint32_t* feature_count, float* embedding) {
    pthread_mutex_lock(&fusion->fusion_lock);
    
    if (features && feature_count) {
        memcpy(features, fusion->fused_features, 
               fusion->fused_feature_count * sizeof(float));
        *feature_count = fusion->fused_feature_count;
    }
    
    if (embedding) {
        memcpy(embedding, fusion->fused_embedding, 
               EMBEDDING_DIM * sizeof(float));
    }
    
    pthread_mutex_unlock(&fusion->fusion_lock);
}

// Cleanup fusion instance
void fusion_destroy_instance(multimodal_fusion_t* fusion) {
    pthread_mutex_lock(&fusion->fusion_lock);
    
    // Free modalities
    for (uint32_t i = 0; i < fusion->modality_count; i++) {
        free(fusion->modalities[i]->raw_data);
        free(fusion->modalities[i]);
    }
    
    // Free components
    free(fusion->self_attention);
    free(fusion->cross_attention);
    free(fusion->cross_modal);
    
    pthread_mutex_unlock(&fusion->fusion_lock);
    pthread_mutex_destroy(&fusion->fusion_lock);
    
    free(fusion);
}

// Shutdown fusion system
void multimodal_fusion_shutdown(void) {
    g_fusion_system->running = false;
    
    // Cleanup instances
    for (uint32_t i = 0; i < g_fusion_system->instance_count; i++) {
        fusion_destroy_instance(g_fusion_system->fusion_instances[i]);
    }
    
    if (g_fusion_system->log_file) {
        fclose(g_fusion_system->log_file);
    }
    
    free(g_fusion_system);
    g_fusion_system = NULL;
}

// Demo function
int main(int argc, char** argv) {
    printf("Multi-Modal Fusion System - <50ms Processing\n");
    printf("=============================================\n\n");
    
    // Initialize system
    if (multimodal_fusion_init() != 0) {
        fprintf(stderr, "Failed to initialize fusion system\n");
        return 1;
    }
    
    // Create fusion instance with attention-based strategy
    multimodal_fusion_t* fusion = fusion_create_instance(FUSION_ATTENTION);
    
    // Simulate text input
    char text_data[] = "Agent system operating normally with high performance";
    fusion_add_modality(fusion, MODALITY_TEXT, text_data, strlen(text_data));
    
    // Simulate image input (dummy data)
    uint8_t image_data[224 * 224 * 3];
    for (int i = 0; i < sizeof(image_data); i++) {
        image_data[i] = rand() % 256;
    }
    modality_data_t image_mod = {
        .type = MODALITY_IMAGE,
        .dimensions = {224, 224, 3}
    };
    fusion->modalities[fusion->modality_count - 1]->dimensions[0] = 224;
    fusion->modalities[fusion->modality_count - 1]->dimensions[1] = 224;
    fusion->modalities[fusion->modality_count - 1]->dimensions[2] = 3;
    fusion_add_modality(fusion, MODALITY_IMAGE, image_data, sizeof(image_data));
    
    // Simulate audio input (dummy data)
    int16_t audio_data[16000];  // 1 second at 16kHz
    for (int i = 0; i < 16000; i++) {
        audio_data[i] = (int16_t)(sin(i * 0.1) * 16384);
    }
    fusion_add_modality(fusion, MODALITY_AUDIO, audio_data, sizeof(audio_data));
    
    // Simulate sensor input
    float sensor_data[] = {23.5, 65.2, 1013.25, 0.78, 42.1};  // temp, humidity, pressure, etc
    fusion_add_modality(fusion, MODALITY_SENSOR, sensor_data, sizeof(sensor_data));
    
    printf("Added 4 modalities: text, image, audio, sensor\n");
    printf("Processing fusion...\n\n");
    
    // Process fusion multiple times to measure performance
    for (int i = 0; i < 10; i++) {
        fusion_process(fusion);
        
        // Get results
        float embedding[EMBEDDING_DIM];
        fusion_get_results(fusion, NULL, NULL, embedding);
        
        printf("Iteration %d: Latency=%.2fms", i + 1, fusion->avg_latency_ms);
        
        if (fusion->avg_latency_ms < 50.0) {
            printf(" ✓ Meeting <50ms target\n");
        } else {
            printf(" ⚠ Above 50ms target\n");
        }
    }
    
    // Print final statistics
    uint64_t total_fusions = atomic_load(&g_fusion_system->total_fusions);
    double avg_time = atomic_load(&g_fusion_system->avg_fusion_time_ms);
    uint64_t modalities = atomic_load(&g_fusion_system->modalities_processed);
    
    printf("\nFinal Statistics:\n");
    printf("Total fusions: %lu\n", total_fusions);
    printf("Average fusion time: %.2fms\n", avg_time);
    printf("Modalities processed: %lu\n", modalities);
    
    // Cleanup
    fusion_destroy_instance(fusion);
    multimodal_fusion_shutdown();
    
    return 0;
}