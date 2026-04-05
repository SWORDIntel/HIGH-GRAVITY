#ifndef CLAUDE_PATHS_H
#define CLAUDE_PATHS_H

#include <stdlib.h>
#include <string.h>
#include <limits.h>

/**
 * Path Resolution Header for Claude Agent System
 * Provides runtime-initialized path management
 */

/**
 * Get environment variable with fallback to default value
 * Thread-safe read-only access
 */
static inline const char* get_env_or_default(const char* env_var, const char* default_val) {
    const char* val = getenv(env_var);
    return val ? val : default_val;
}

// Path buffers (defined in paths.c)
extern char claude_venv_path[PATH_MAX];
extern char claude_toolchain_path[PATH_MAX];
extern char claude_obsidian_vault[PATH_MAX];
extern char claude_data_home[PATH_MAX];

/**
 * Initialize all path buffers
 * Call once at program startup
 * Returns: 0 on success, -1 on failure
 */
int claude_init_paths(void);

// Public accessors
#define VENV_PATH claude_venv_path
#define CUSTOM_TOOLCHAIN_PATH claude_toolchain_path
#define OBSIDIAN_VAULT_PATH claude_obsidian_vault

/**
 * Check if path is initialized and non-empty
 * Returns: 1 if valid, 0 if empty/uninitialized
 */
static inline int claude_path_is_valid(const char* path) {
    return path && strlen(path) > 0;
}

#endif // CLAUDE_PATHS_H
