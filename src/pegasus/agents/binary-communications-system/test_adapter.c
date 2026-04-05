/*
 * TEST ADAPTER PATTERN - Demonstrates the smart integration approach
 * 
 * This shows how the adapter pattern elegantly solves the integration problem
 * by providing a uniform interface to different ring buffer implementations.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "ring_buffer_adapter.h"

int main() {
    printf("=== SMART ADAPTER PATTERN DEMONSTRATION ===\n\n");
    
    // Create adapters for different implementations
    printf("Creating compatibility layer adapter...\n");
    ring_buffer_adapter_t* compat_adapter = create_compat_ring_buffer_adapter(1024);
    
    printf("Creating hybrid NUMA-aware adapter...\n");
    ring_buffer_adapter_t* hybrid_adapter = create_hybrid_ring_buffer_adapter(1024, 0);
    
    // Both adapters use the EXACT SAME interface!
    enhanced_msg_header_t msg = {
        .magic = 0x4E454741,
        .version = 1,
        .msg_type = 100,
        .priority = 2,
        .timestamp = time(NULL),
        .source_id = 1,
        .target_id = 2,
        .payload_size = 64,
        .checksum = 0xDEADBEEF
    };
    
    uint8_t payload[64];
    memset(payload, 0x42, sizeof(payload));
    
    // Test writing to both adapters with identical code
    printf("\n1. Writing to compat adapter: ");
    if (ring_buffer_write(compat_adapter, 2, &msg, payload) == 0) {
        printf("SUCCESS\n");
    } else {
        printf("FAILED\n");
    }
    
    printf("2. Writing to hybrid adapter: ");
    if (ring_buffer_write(hybrid_adapter, 2, &msg, payload) == 0) {
        printf("SUCCESS\n");
    } else {
        printf("FAILED\n");
    }
    
    // Test reading from both adapters
    enhanced_msg_header_t read_msg;
    uint8_t read_payload[64];
    
    printf("\n3. Reading from compat adapter: ");
    if (ring_buffer_read(compat_adapter, 2, &read_msg, read_payload) == 0) {
        printf("SUCCESS (msg_type=%d)\n", read_msg.msg_type);
    } else {
        printf("No messages\n");
    }
    
    printf("4. Reading from hybrid adapter: ");
    if (ring_buffer_read(hybrid_adapter, 2, &read_msg, read_payload) == 0) {
        printf("SUCCESS (msg_type=%d)\n", read_msg.msg_type);
    } else {
        printf("No messages\n");
    }
    
    // Show statistics (hybrid adapter tracks stats, compat doesn't)
    printf("\n5. Hybrid adapter stats:\n");
    printf("   - Total messages: %zu\n", hybrid_adapter->ops->get_stats(hybrid_adapter->impl, 0));
    printf("   - Total bytes: %zu\n", hybrid_adapter->ops->get_stats(hybrid_adapter->impl, 1));
    printf("   - NUMA node: %zu\n", hybrid_adapter->ops->get_stats(hybrid_adapter->impl, 2));
    
    printf("\n6. Compat adapter stats: %zu (not tracked)\n", 
           compat_adapter->ops->get_stats(compat_adapter->impl, 0));
    
    // Clean up - same interface for destruction
    printf("\n7. Cleaning up both adapters...\n");
    ring_buffer_destroy_adapter(compat_adapter);
    ring_buffer_destroy_adapter(hybrid_adapter);
    
    printf("\n=== KEY INSIGHTS ===\n");
    printf("1. Both implementations use the SAME interface\n");
    printf("2. Can switch implementations without changing code\n");
    printf("3. Each adapter can have unique features (stats, NUMA, etc.)\n");
    printf("4. Clean separation of concerns\n");
    printf("5. This is how professional C projects handle multiple backends\n");
    printf("   (Examples: PostgreSQL, SQLite, Linux kernel drivers)\n");
    
    return 0;
}