/*
 * Neural Architecture Search (NAS) System
 * Self-optimizing agent architecture with 1000 architectures/hour evaluation
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

#define MAX_LAYERS 256
#define MAX_CONNECTIONS 4096
#define MAX_ARCHITECTURES 10000
#define POPULATION_SIZE 100
#define MUTATION_RATE 0.15
#define CROSSOVER_RATE 0.75
#define ELITE_SIZE 10
#define MAX_PARAMS 100000000  // 100M parameters max

// Layer types
typedef enum {
    LAYER_INPUT,
    LAYER_DENSE,
    LAYER_CONV2D,
    LAYER_LSTM,
    LAYER_GRU,
    LAYER_ATTENTION,
    LAYER_TRANSFORMER,
    LAYER_DROPOUT,
    LAYER_BATCH_NORM,
    LAYER_ACTIVATION,
    LAYER_POOLING,
    LAYER_RESIDUAL,
    LAYER_OUTPUT
} layer_type_t;

// Activation functions
typedef enum {
    ACT_RELU,
    ACT_SIGMOID,
    ACT_TANH,
    ACT_SOFTMAX,
    ACT_GELU,
    ACT_SWISH,
    ACT_MISH,
    ACT_ELU,
    ACT_SELU
} activation_type_t;

// Search space definition
typedef struct {
    layer_type_t type;
    uint32_t units;           // Number of units/filters
    uint32_t kernel_size;     // For conv layers
    uint32_t stride;          // For conv/pooling
    float dropout_rate;       // For dropout layers
    activation_type_t activation;
    bool use_bias;
    bool use_batch_norm;
} layer_config_t;

// Neural network architecture
typedef struct {
    uint32_t architecture_id;
    layer_config_t layers[MAX_LAYERS];
    uint32_t layer_count;
    uint32_t connections[MAX_CONNECTIONS][2];  // From layer -> to layer
    uint32_t connection_count;
    uint64_t total_params;
    double fitness_score;
    double accuracy;
    double latency_ms;
    double memory_mb;
    double flops;
    bool is_valid;
} architecture_t;

// Training metrics
typedef struct {
    double train_loss;
    double val_loss;
    double train_acc;
    double val_acc;
    double convergence_speed;
    uint32_t epochs_to_converge;
} training_metrics_t;

// Search controller
typedef struct {
    architecture_t* population[POPULATION_SIZE];
    architecture_t* best_architecture;
    uint32_t generation;
    double best_fitness;
    pthread_mutex_t population_lock;
} evolution_controller_t;

// Bayesian optimization state
typedef struct {
    double** gaussian_process;  // Surrogate model
    double* acquisition_values;
    uint32_t sample_count;
    double exploration_rate;
} bayesian_optimizer_t;

// Reinforcement learning controller
typedef struct {
    double** q_table;
    uint32_t state_size;
    uint32_t action_size;
    double epsilon;  // Exploration rate
    double alpha;    // Learning rate
    double gamma;    // Discount factor
} rl_controller_t;

// Main NAS system
typedef struct {
    evolution_controller_t* evolution;
    bayesian_optimizer_t* bayesian;
    rl_controller_t* rl;
    architecture_t* architecture_cache[MAX_ARCHITECTURES];
    uint32_t cache_size;
    pthread_t search_threads[16];
    uint32_t thread_count;
    _Atomic uint32_t architectures_evaluated;
    _Atomic uint32_t architectures_per_hour;
    bool running;
    FILE* log_file;
} nas_system_t;

static nas_system_t* g_nas = NULL;

// Fast architecture hash for caching
static uint64_t architecture_hash(architecture_t* arch) {
    uint64_t hash = 0;
    for (uint32_t i = 0; i < arch->layer_count; i++) {
        hash ^= ((uint64_t)arch->layers[i].type << 32) | 
                (arch->layers[i].units << 16) |
                arch->layers[i].activation;
        hash = hash * 31 + arch->layers[i].kernel_size;
    }
    return hash;
}

// Check if architecture exists in cache
static architecture_t* check_cache(uint64_t hash) {
    for (uint32_t i = 0; i < g_nas->cache_size; i++) {
        if (architecture_hash(g_nas->architecture_cache[i]) == hash) {
            return g_nas->architecture_cache[i];
        }
    }
    return NULL;
}

// Estimate model parameters
static uint64_t estimate_parameters(architecture_t* arch) {
    uint64_t params = 0;
    uint32_t prev_units = 0;
    
    for (uint32_t i = 0; i < arch->layer_count; i++) {
        layer_config_t* layer = &arch->layers[i];
        
        switch (layer->type) {
            case LAYER_DENSE:
                if (prev_units > 0) {
                    params += prev_units * layer->units;
                    if (layer->use_bias) params += layer->units;
                }
                prev_units = layer->units;
                break;
                
            case LAYER_CONV2D:
                if (prev_units > 0) {
                    params += layer->kernel_size * layer->kernel_size * 
                             prev_units * layer->units;
                    if (layer->use_bias) params += layer->units;
                }
                prev_units = layer->units;
                break;
                
            case LAYER_LSTM:
            case LAYER_GRU:
                if (prev_units > 0) {
                    params += 4 * (prev_units + layer->units + 1) * layer->units;
                }
                prev_units = layer->units;
                break;
                
            case LAYER_ATTENTION:
            case LAYER_TRANSFORMER:
                params += 4 * layer->units * layer->units;  // Q, K, V, O matrices
                prev_units = layer->units;
                break;
                
            default:
                break;
        }
        
        if (layer->use_batch_norm && layer->units > 0) {
            params += 2 * layer->units;  // Scale and shift parameters
        }
    }
    
    return params;
}

// Estimate model FLOPs
static double estimate_flops(architecture_t* arch, uint32_t batch_size, uint32_t seq_len) {
    double flops = 0;
    uint32_t prev_units = 0;
    
    for (uint32_t i = 0; i < arch->layer_count; i++) {
        layer_config_t* layer = &arch->layers[i];
        
        switch (layer->type) {
            case LAYER_DENSE:
                if (prev_units > 0) {
                    flops += 2.0 * batch_size * prev_units * layer->units;
                }
                prev_units = layer->units;
                break;
                
            case LAYER_CONV2D:
                if (prev_units > 0) {
                    // Assuming square input/output
                    uint32_t output_size = 224 / layer->stride;  // Example input size
                    flops += 2.0 * batch_size * output_size * output_size *
                            layer->kernel_size * layer->kernel_size * 
                            prev_units * layer->units;
                }
                prev_units = layer->units;
                break;
                
            case LAYER_ATTENTION:
                flops += 4.0 * batch_size * seq_len * seq_len * layer->units;
                prev_units = layer->units;
                break;
                
            default:
                break;
        }
    }
    
    return flops;
}

// Simulate training (would be replaced with actual training)
static training_metrics_t simulate_training(architecture_t* arch) {
    training_metrics_t metrics = {0};
    
    // Simulate based on architecture complexity
    double complexity = (double)arch->total_params / 1000000.0;  // In millions
    
    // Simple heuristic: smaller models train faster but may have lower accuracy
    metrics.train_loss = 0.1 + (rand() % 100) / 1000.0;
    metrics.val_loss = metrics.train_loss * (1.1 + (rand() % 20) / 100.0);
    
    // Accuracy based on model size and architecture
    double base_acc = 0.7 + complexity * 0.002;
    if (base_acc > 0.99) base_acc = 0.99;
    
    metrics.train_acc = base_acc + (rand() % 100) / 10000.0;
    metrics.val_acc = metrics.train_acc - (rand() % 50) / 1000.0;
    
    metrics.convergence_speed = 100.0 / (1.0 + complexity);
    metrics.epochs_to_converge = 10 + complexity * 2;
    
    // Penalize overly complex architectures
    if (arch->total_params > MAX_PARAMS) {
        metrics.val_acc *= 0.8;
    }
    
    return metrics;
}

// Calculate fitness score (multi-objective)
static double calculate_fitness(architecture_t* arch) {
    training_metrics_t metrics = simulate_training(arch);
    
    // Multi-objective fitness: accuracy, efficiency, and size
    double accuracy_score = metrics.val_acc;
    double efficiency_score = 1.0 / (1.0 + arch->latency_ms / 10.0);
    double size_score = 1.0 / (1.0 + log10(arch->total_params + 1) / 10.0);
    double convergence_score = 1.0 / (1.0 + metrics.epochs_to_converge / 100.0);
    
    // Weighted combination
    double fitness = 0.4 * accuracy_score + 
                    0.3 * efficiency_score + 
                    0.2 * size_score +
                    0.1 * convergence_score;
    
    // Store metrics
    arch->accuracy = metrics.val_acc;
    arch->latency_ms = arch->total_params / 1000000.0;  // Simplified
    arch->memory_mb = arch->total_params * 4 / 1048576.0;  // 4 bytes per param
    
    return fitness;
}

// Generate random architecture
static architecture_t* generate_random_architecture(void) {
    architecture_t* arch = calloc(1, sizeof(architecture_t));
    arch->architecture_id = atomic_fetch_add(&g_nas->architectures_evaluated, 1);
    
    // Random number of layers (5-50)
    arch->layer_count = 5 + rand() % 46;
    
    // Always start with input layer
    arch->layers[0].type = LAYER_INPUT;
    arch->layers[0].units = 224;  // Example input size
    
    // Generate random layers
    for (uint32_t i = 1; i < arch->layer_count - 1; i++) {
        layer_config_t* layer = &arch->layers[i];
        
        // Random layer type
        layer->type = 1 + rand() % 11;  // Skip INPUT and OUTPUT
        
        // Random configuration based on type
        switch (layer->type) {
            case LAYER_DENSE:
                layer->units = 32 + (rand() % 30) * 32;  // 32-992
                layer->activation = rand() % 9;
                layer->use_bias = rand() % 2;
                layer->use_batch_norm = rand() % 2;
                break;
                
            case LAYER_CONV2D:
                layer->units = 8 + (rand() % 8) * 8;  // 8-64 filters
                layer->kernel_size = 1 + 2 * (rand() % 3);  // 1, 3, or 5
                layer->stride = 1 + rand() % 2;
                layer->activation = rand() % 9;
                layer->use_bias = rand() % 2;
                layer->use_batch_norm = rand() % 2;
                break;
                
            case LAYER_LSTM:
            case LAYER_GRU:
                layer->units = 32 + (rand() % 16) * 32;  // 32-512
                layer->activation = ACT_TANH;
                layer->use_bias = true;
                break;
                
            case LAYER_ATTENTION:
            case LAYER_TRANSFORMER:
                layer->units = 64 + (rand() % 8) * 64;  // 64-512
                layer->activation = ACT_SOFTMAX;
                break;
                
            case LAYER_DROPOUT:
                layer->dropout_rate = 0.1 + (rand() % 40) / 100.0;  // 0.1-0.5
                break;
                
            default:
                layer->units = 64 + rand() % 256;
                break;
        }
    }
    
    // Always end with output layer
    arch->layers[arch->layer_count - 1].type = LAYER_OUTPUT;
    arch->layers[arch->layer_count - 1].units = 10;  // Example: 10 classes
    arch->layers[arch->layer_count - 1].activation = ACT_SOFTMAX;
    
    // Generate connections (default sequential for now)
    for (uint32_t i = 0; i < arch->layer_count - 1; i++) {
        arch->connections[i][0] = i;
        arch->connections[i][1] = i + 1;
    }
    arch->connection_count = arch->layer_count - 1;
    
    // Add skip connections randomly
    for (uint32_t i = 0; i < arch->layer_count - 2; i++) {
        if (rand() % 100 < 20) {  // 20% chance
            if (arch->connection_count < MAX_CONNECTIONS) {
                arch->connections[arch->connection_count][0] = i;
                arch->connections[arch->connection_count][1] = i + 2 + rand() % 
                    (arch->layer_count - i - 2);
                arch->connection_count++;
            }
        }
    }
    
    // Calculate parameters and fitness
    arch->total_params = estimate_parameters(arch);
    arch->flops = estimate_flops(arch, 32, 100);
    arch->fitness_score = calculate_fitness(arch);
    arch->is_valid = arch->total_params < MAX_PARAMS;
    
    return arch;
}

// Crossover two architectures
static architecture_t* crossover(architecture_t* parent1, architecture_t* parent2) {
    architecture_t* child = calloc(1, sizeof(architecture_t));
    child->architecture_id = atomic_fetch_add(&g_nas->architectures_evaluated, 1);
    
    // Crossover point
    uint32_t min_layers = parent1->layer_count < parent2->layer_count ? 
                         parent1->layer_count : parent2->layer_count;
    uint32_t crossover_point = 1 + rand() % (min_layers - 2);
    
    // Copy layers from parents
    for (uint32_t i = 0; i < crossover_point; i++) {
        child->layers[i] = parent1->layers[i];
    }
    
    uint32_t remaining = parent2->layer_count - crossover_point;
    for (uint32_t i = 0; i < remaining; i++) {
        child->layers[crossover_point + i] = parent2->layers[crossover_point + i];
    }
    
    child->layer_count = crossover_point + remaining;
    
    // Inherit connections with some randomization
    child->connection_count = 0;
    for (uint32_t i = 0; i < parent1->connection_count; i++) {
        if (parent1->connections[i][1] < child->layer_count && 
            rand() % 100 < 70) {  // 70% inheritance rate
            child->connections[child->connection_count][0] = parent1->connections[i][0];
            child->connections[child->connection_count][1] = parent1->connections[i][1];
            child->connection_count++;
        }
    }
    
    // Recalculate metrics
    child->total_params = estimate_parameters(child);
    child->flops = estimate_flops(child, 32, 100);
    child->fitness_score = calculate_fitness(child);
    child->is_valid = child->total_params < MAX_PARAMS;
    
    return child;
}

// Mutate architecture
static void mutate(architecture_t* arch) {
    // Mutation types
    int mutation_type = rand() % 5;
    
    switch (mutation_type) {
        case 0:  // Change layer type
            if (arch->layer_count > 2) {
                uint32_t layer_idx = 1 + rand() % (arch->layer_count - 2);
                arch->layers[layer_idx].type = 1 + rand() % 11;
            }
            break;
            
        case 1:  // Change layer size
            if (arch->layer_count > 2) {
                uint32_t layer_idx = 1 + rand() % (arch->layer_count - 2);
                arch->layers[layer_idx].units = 32 + (rand() % 30) * 32;
            }
            break;
            
        case 2:  // Add layer
            if (arch->layer_count < MAX_LAYERS - 1) {
                uint32_t insert_pos = 1 + rand() % (arch->layer_count - 1);
                // Shift layers
                for (uint32_t i = arch->layer_count; i > insert_pos; i--) {
                    arch->layers[i] = arch->layers[i - 1];
                }
                // Insert new random layer
                arch->layers[insert_pos].type = 1 + rand() % 11;
                arch->layers[insert_pos].units = 64 + rand() % 256;
                arch->layers[insert_pos].activation = rand() % 9;
                arch->layer_count++;
            }
            break;
            
        case 3:  // Remove layer
            if (arch->layer_count > 3) {
                uint32_t remove_pos = 1 + rand() % (arch->layer_count - 2);
                // Shift layers
                for (uint32_t i = remove_pos; i < arch->layer_count - 1; i++) {
                    arch->layers[i] = arch->layers[i + 1];
                }
                arch->layer_count--;
            }
            break;
            
        case 4:  // Add/remove skip connection
            if (rand() % 2 && arch->connection_count < MAX_CONNECTIONS) {
                // Add skip connection
                uint32_t from = rand() % (arch->layer_count - 2);
                uint32_t to = from + 2 + rand() % (arch->layer_count - from - 2);
                arch->connections[arch->connection_count][0] = from;
                arch->connections[arch->connection_count][1] = to;
                arch->connection_count++;
            } else if (arch->connection_count > arch->layer_count) {
                // Remove random connection
                uint32_t idx = arch->layer_count + rand() % 
                              (arch->connection_count - arch->layer_count);
                for (uint32_t i = idx; i < arch->connection_count - 1; i++) {
                    arch->connections[i][0] = arch->connections[i + 1][0];
                    arch->connections[i][1] = arch->connections[i + 1][1];
                }
                arch->connection_count--;
            }
            break;
    }
    
    // Recalculate metrics
    arch->total_params = estimate_parameters(arch);
    arch->flops = estimate_flops(arch, 32, 100);
    arch->fitness_score = calculate_fitness(arch);
    arch->is_valid = arch->total_params < MAX_PARAMS;
}

// Evolution thread
static void* evolution_search(void* arg) {
    evolution_controller_t* evo = (evolution_controller_t*)arg;
    
    while (g_nas->running) {
        pthread_mutex_lock(&evo->population_lock);
        
        // Sort population by fitness
        for (uint32_t i = 0; i < POPULATION_SIZE - 1; i++) {
            for (uint32_t j = i + 1; j < POPULATION_SIZE; j++) {
                if (evo->population[j]->fitness_score > 
                    evo->population[i]->fitness_score) {
                    architecture_t* temp = evo->population[i];
                    evo->population[i] = evo->population[j];
                    evo->population[j] = temp;
                }
            }
        }
        
        // Create new generation
        architecture_t* new_population[POPULATION_SIZE];
        
        // Keep elite
        for (uint32_t i = 0; i < ELITE_SIZE; i++) {
            new_population[i] = evo->population[i];
        }
        
        // Generate offspring
        for (uint32_t i = ELITE_SIZE; i < POPULATION_SIZE; i++) {
            if ((double)rand() / RAND_MAX < CROSSOVER_RATE) {
                // Crossover
                uint32_t parent1_idx = rand() % (POPULATION_SIZE / 2);
                uint32_t parent2_idx = rand() % (POPULATION_SIZE / 2);
                new_population[i] = crossover(evo->population[parent1_idx],
                                             evo->population[parent2_idx]);
            } else {
                // Copy from population
                new_population[i] = generate_random_architecture();
            }
            
            // Mutation
            if ((double)rand() / RAND_MAX < MUTATION_RATE) {
                mutate(new_population[i]);
            }
        }
        
        // Replace old population (except elite)
        for (uint32_t i = ELITE_SIZE; i < POPULATION_SIZE; i++) {
            if (evo->population[i] != new_population[i]) {
                free(evo->population[i]);
            }
            evo->population[i] = new_population[i];
        }
        
        // Update best
        if (evo->population[0]->fitness_score > evo->best_fitness) {
            evo->best_fitness = evo->population[0]->fitness_score;
            evo->best_architecture = evo->population[0];
            
            printf("Generation %u: New best fitness = %.4f (Acc: %.2f%%, Params: %luM)\n",
                   evo->generation, evo->best_fitness,
                   evo->best_architecture->accuracy * 100,
                   evo->best_architecture->total_params / 1000000);
        }
        
        evo->generation++;
        pthread_mutex_unlock(&evo->population_lock);
        
        usleep(10000);  // 10ms delay between generations
    }
    
    return NULL;
}

// Bayesian optimization acquisition function
static double acquisition_function(double mean, double std, double best_score) {
    // Expected Improvement (EI)
    if (std == 0) return 0;
    
    double z = (mean - best_score) / std;
    double ei = std * (z * 0.5 * (1 + erf(z / sqrt(2))) + 
                      exp(-z * z / 2) / sqrt(2 * M_PI));
    return ei;
}

// Initialize NAS system
int nas_init(void) {
    g_nas = calloc(1, sizeof(nas_system_t));
    if (!g_nas) {
        return -1;
    }
    
    // Initialize evolution controller
    g_nas->evolution = calloc(1, sizeof(evolution_controller_t));
    pthread_mutex_init(&g_nas->evolution->population_lock, NULL);
    
    // Generate initial population
    for (uint32_t i = 0; i < POPULATION_SIZE; i++) {
        g_nas->evolution->population[i] = generate_random_architecture();
    }
    
    // Initialize Bayesian optimizer
    g_nas->bayesian = calloc(1, sizeof(bayesian_optimizer_t));
    g_nas->bayesian->exploration_rate = 1.0;
    
    // Initialize RL controller
    g_nas->rl = calloc(1, sizeof(rl_controller_t));
    g_nas->rl->epsilon = 0.1;
    g_nas->rl->alpha = 0.1;
    g_nas->rl->gamma = 0.95;
    
    // Open log file
    g_nas->log_file = fopen("nas_search.log", "w");
    
    g_nas->running = true;
    g_nas->thread_count = 1;  // Start with evolution search
    
    // Start search threads
    pthread_create(&g_nas->search_threads[0], NULL, evolution_search, g_nas->evolution);
    
    return 0;
}

// Export architecture to file
void nas_export_architecture(architecture_t* arch, const char* filename) {
    FILE* fp = fopen(filename, "w");
    if (!fp) return;
    
    fprintf(fp, "# Neural Architecture Search Result\n");
    fprintf(fp, "# ID: %u, Fitness: %.4f, Accuracy: %.2f%%\n",
            arch->architecture_id, arch->fitness_score, arch->accuracy * 100);
    fprintf(fp, "# Parameters: %lu, FLOPs: %.2fG, Memory: %.2fMB\n\n",
            arch->total_params, arch->flops / 1e9, arch->memory_mb);
    
    fprintf(fp, "architecture:\n");
    fprintf(fp, "  layers:\n");
    
    for (uint32_t i = 0; i < arch->layer_count; i++) {
        layer_config_t* layer = &arch->layers[i];
        fprintf(fp, "    - type: %d\n", layer->type);
        fprintf(fp, "      units: %u\n", layer->units);
        if (layer->type == LAYER_CONV2D) {
            fprintf(fp, "      kernel_size: %u\n", layer->kernel_size);
            fprintf(fp, "      stride: %u\n", layer->stride);
        }
        if (layer->type == LAYER_DROPOUT) {
            fprintf(fp, "      dropout_rate: %.2f\n", layer->dropout_rate);
        }
        fprintf(fp, "      activation: %d\n", layer->activation);
        fprintf(fp, "      use_bias: %s\n", layer->use_bias ? "true" : "false");
        fprintf(fp, "      use_batch_norm: %s\n", layer->use_batch_norm ? "true" : "false");
    }
    
    fprintf(fp, "\n  connections:\n");
    for (uint32_t i = 0; i < arch->connection_count; i++) {
        fprintf(fp, "    - [%u, %u]\n", 
                arch->connections[i][0], arch->connections[i][1]);
    }
    
    fclose(fp);
}

// Get search statistics
void nas_get_stats(uint32_t* architectures_evaluated, double* best_fitness,
                  uint32_t* generation) {
    if (architectures_evaluated) {
        *architectures_evaluated = atomic_load(&g_nas->architectures_evaluated);
    }
    if (best_fitness) {
        *best_fitness = g_nas->evolution->best_fitness;
    }
    if (generation) {
        *generation = g_nas->evolution->generation;
    }
}

// Shutdown NAS system
void nas_shutdown(void) {
    g_nas->running = false;
    
    // Wait for threads
    for (uint32_t i = 0; i < g_nas->thread_count; i++) {
        pthread_join(g_nas->search_threads[i], NULL);
    }
    
    // Cleanup evolution controller
    for (uint32_t i = 0; i < POPULATION_SIZE; i++) {
        free(g_nas->evolution->population[i]);
    }
    pthread_mutex_destroy(&g_nas->evolution->population_lock);
    free(g_nas->evolution);
    
    // Cleanup other components
    free(g_nas->bayesian);
    free(g_nas->rl);
    
    // Close log
    if (g_nas->log_file) {
        fclose(g_nas->log_file);
    }
    
    free(g_nas);
    g_nas = NULL;
}

// Demo function
// int main_disabled(int argc, char** argv) {
    printf("Neural Architecture Search System\n");
    printf("==================================\n\n");
    
    // Initialize NAS
    if (nas_init() != 0) {
        fprintf(stderr, "Failed to initialize NAS system\n");
        return 1;
    }
    
    printf("Starting architecture search...\n");
    printf("Target: 1000 architectures/hour\n\n");
    
    // Run search for demonstration
    time_t start_time = time(NULL);
    
    while (g_nas->running) {
        sleep(5);
        
        // Get statistics
        uint32_t evaluated;
        double best_fitness;
        uint32_t generation;
        nas_get_stats(&evaluated, &best_fitness, &generation);
        
        // Calculate rate
        time_t elapsed = time(NULL) - start_time;
        if (elapsed > 0) {
            uint32_t rate = (evaluated * 3600) / elapsed;
            atomic_store(&g_nas->architectures_per_hour, rate);
            
            printf("Generation: %u, Evaluated: %u, Rate: %u/hour, Best: %.4f\n",
                   generation, evaluated, rate, best_fitness);
        }
        
        // Export best architecture periodically
        if (generation % 10 == 0 && g_nas->evolution->best_architecture) {
            nas_export_architecture(g_nas->evolution->best_architecture, 
                                   "best_architecture.yaml");
        }
        
        // Stop after evaluating 100 architectures for demo
        if (evaluated >= 100) {
            break;
        }
    }
    
    printf("\nSearch complete. Best architecture exported to best_architecture.yaml\n");
    
    // Shutdown
    nas_shutdown();
    
    return 0;
}