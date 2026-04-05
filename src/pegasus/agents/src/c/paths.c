/**
 * Path Resolution Implementation for Claude Agent System
 * Provides runtime path initialization and management
 */

#include "paths.h"

// Path buffers (defined once here)
char claude_venv_path[PATH_MAX];
char claude_toolchain_path[PATH_MAX];
char claude_obsidian_vault[PATH_MAX];
char claude_data_home[PATH_MAX];

/**
 * Initialize all path buffers with environment-aware defaults
 * Must be called once at program startup before accessing any paths
 *
 * Returns: 0 on success, -1 on failure
 */
int claude_init_paths(void) {
    const char* data_home_env = getenv("CLAUDE_DATA_HOME");
    const char* home = getenv("HOME");

    // Initialize data home
    if (data_home_env && strlen(data_home_env) > 0) {
        if (strlen(data_home_env) >= PATH_MAX) {
            return -1;  // Path too long
        }
        snprintf(claude_data_home, PATH_MAX, "%s", data_home_env);
    } else if (home) {
        if (strlen(home) >= PATH_MAX - 50) {  // Reserve space for suffix
            return -1;  // Path too long
        }
        snprintf(claude_data_home, PATH_MAX, "%s/.local/share/claude", home);
    } else {
        claude_data_home[0] = '\0';
        return -1;  // Cannot determine data home
    }

    // Initialize venv and toolchain paths
    if (strlen(claude_data_home) > 0) {
        snprintf(claude_venv_path, PATH_MAX, "%s/datascience", claude_data_home);
        snprintf(claude_toolchain_path, PATH_MAX, "%s/c-toolchain", claude_data_home);
    } else {
        claude_venv_path[0] = '\0';
        claude_toolchain_path[0] = '\0';
    }

    // Initialize Obsidian vault
    if (home) {
        if (strlen(home) >= PATH_MAX - 50) {
            return -1;  // Path too long
        }
        snprintf(claude_obsidian_vault, PATH_MAX, "%s/Documents/Obsidian/DataScience", home);
    } else {
        claude_obsidian_vault[0] = '\0';
    }

    return 0;
}
