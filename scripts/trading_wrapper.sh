#!/bin/bash
# Trading Bot Wrapper Script with Enhanced Logging and Error Handling

# Set script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PYTHON_ENV="$PROJECT_ROOT/bin/python3"
LOG_DIR="$PROJECT_ROOT/logs"
DATE=$(date +%Y%m%d_%H%M%S)

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/wrapper.log"
}

# Function to run trading with error handling
run_trading() {
    local log_file="$LOG_DIR/trading_$DATE.log"
    
    log "Starting trading bot execution..."
    log "Log file: $log_file"
    
    cd "$PROJECT_ROOT" || {
        log "ERROR: Could not change to project directory: $PROJECT_ROOT"
        exit 1
    }
    
    # Check if Python environment exists
    if [[ ! -f "$PYTHON_ENV" ]]; then
        PYTHON_ENV=$(which python3)
        log "Using system Python: $PYTHON_ENV"
    fi
    
    # Run the trading bot
    "$PYTHON_ENV" src/main.py run_trades > "$log_file" 2>&1
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log "Trading bot completed successfully"
    else
        log "ERROR: Trading bot failed with exit code $exit_code"
        log "Check log file for details: $log_file"
        
        # Send error notification (optional)
        # echo "Trading bot failed at $(date)" | mail -s "Trading Bot Error" your_email@example.com
    fi
    
    return $exit_code
}

# Function to run PDUFA scraping
run_pdufa_scraping() {
    local log_file="$LOG_DIR/pdufa_$DATE.log"
    
    log "Starting PDUFA data scraping..."
    log "Log file: $log_file"
    
    cd "$PROJECT_ROOT" || {
        log "ERROR: Could not change to project directory: $PROJECT_ROOT"
        exit 1
    }
    
    "$PYTHON_ENV" src/main.py scrape_pdufa > "$log_file" 2>&1
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log "PDUFA scraping completed successfully"
    else
        log "ERROR: PDUFA scraping failed with exit code $exit_code"
    fi
    
    return $exit_code
}

# Function to run clinical trials fetching
run_trials_fetching() {
    local log_file="$LOG_DIR/trials_$DATE.log"
    
    log "Starting clinical trials data fetching..."
    log "Log file: $log_file"
    
    cd "$PROJECT_ROOT" || {
        log "ERROR: Could not change to project directory: $PROJECT_ROOT"
        exit 1
    }
    
    "$PYTHON_ENV" src/main.py fetch_trials > "$log_file" 2>&1
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log "Clinical trials fetching completed successfully"
    else
        log "ERROR: Clinical trials fetching failed with exit code $exit_code"
    fi
    
    return $exit_code
}

# Main execution based on command line argument
case "${1:-}" in
    "trading")
        run_trading
        ;;
    "pdufa")
        run_pdufa_scraping
        ;;
    "trials")
        run_trials_fetching
        ;;
    "weekly")
        # Run weekly tasks (PDUFA then trials)
        log "Starting weekly data refresh..."
        run_pdufa_scraping
        sleep 30  # Wait 30 seconds between tasks
        run_trials_fetching
        log "Weekly data refresh completed"
        ;;
    *)
        echo "Usage: $0 {trading|pdufa|trials|weekly}"
        echo "  trading - Run daily trading bot"
        echo "  pdufa   - Scrape PDUFA data and screen companies"
        echo "  trials  - Fetch clinical trials data"
        echo "  weekly  - Run both pdufa and trials (for weekly refresh)"
        exit 1
        ;;
esac

exit $?