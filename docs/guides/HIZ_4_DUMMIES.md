# HIZ-4-DUMMIES: High-Gravity Setup Guide

Welcome to HIGH-GRAVITY. This guide will help you get set up with minimal effort.

## Step 1: Run the Setup Wrapper
Open your terminal in the `HIGH-GRAVITY` directory and run:
```bash
./hiz_setup.sh
```

## Step 2: Choose Your Path
The script provides a simple menu:

1. **[Install/Update Patches]**: Run this first to patch your Windsurf Next installation. (Requires sudo, password: `1786`).
2. **[Wire Project]**: Run this inside a project directory to link it to the local High-Gravity proxy.
3. **[Launch Dashboard]**: Opens the monitor. Leave this running to ensure your optimizations (caching, spoofing) are active.

## Step 3: Enjoy
Once wired and the dashboard is running, restart Windsurf. All inference requests will now be automatically optimized and proxied.

*Need help? Check the `logs/` directory for any connection issues.*
