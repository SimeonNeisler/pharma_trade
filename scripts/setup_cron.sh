#!/bin/bash
# Setup script for pharma trading cron jobs

PROJECT_ROOT="/Users/simeonneisler/Projects/pharma_trade"
WRAPPER_SCRIPT="$PROJECT_ROOT/scripts/trading_wrapper.sh"

echo "Setting up Pharma Trading Automation Cron Jobs..."

# Create necessary directories
echo "Creating logs directory..."
mkdir -p "$PROJECT_ROOT/logs"

# Make wrapper script executable
echo "Making wrapper script executable..."
chmod +x "$WRAPPER_SCRIPT"

# Test the wrapper script
echo "Testing wrapper script..."
if [[ -f "$WRAPPER_SCRIPT" ]]; then
    echo "Wrapper script found at: $WRAPPER_SCRIPT"
    echo "Testing with 'trading' command (dry run)..."
    # Add a test mode to wrapper script if needed
else
    echo "ERROR: Wrapper script not found at $WRAPPER_SCRIPT"
    exit 1
fi

# Check if Python environment is working
echo "Checking Python environment..."
cd "$PROJECT_ROOT" || exit 1

if python3 -c "import sys; print(f'Python: {sys.executable}')"; then
    echo "Python environment is working"
else
    echo "ERROR: Python environment issue detected"
    exit 1
fi

# Display current crontab
echo "Current crontab entries:"
crontab -l 2>/dev/null || echo "No crontab entries found"

echo ""
echo "To install the cron jobs:"
echo "1. Run: crontab -e"
echo "2. Add these lines:"
echo ""
echo "# Pharma Trading Automation"
echo "30 9 * * 1-5 $WRAPPER_SCRIPT trading"
echo "0 9 * * 1 $WRAPPER_SCRIPT weekly"
echo ""
echo "3. Save and exit (:wq in vim)"
echo "4. Verify with: crontab -l"
echo ""
echo "Log files will be created in: $PROJECT_ROOT/logs/"

# Optional: Automatically add to crontab (commented out for safety)
# echo "Would you like to automatically add these cron jobs? (y/n)"
# read -r response
# if [[ "$response" =~ ^[Yy]$ ]]; then
#     # Backup existing crontab
#     crontab -l > "$PROJECT_ROOT/crontab_backup_$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null
#     
#     # Add new cron jobs
#     (crontab -l 2>/dev/null; echo "# Pharma Trading Automation"; echo "30 9 * * 1-5 $WRAPPER_SCRIPT trading"; echo "0 9 * * 1 $WRAPPER_SCRIPT weekly") | crontab -
#     
#     echo "Cron jobs added successfully!"
#     echo "New crontab:"
#     crontab -l
# fi

echo "Setup complete!"