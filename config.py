import os

# Deriv API Configuration
APP_ID = os.getenv("DERIV_APP_ID", "1089")  # Default public App ID
API_TOKEN = os.getenv("DERIV_API_TOKEN", "")

# Scanner Configuration
PAIRS = ["R_75", "1HZ75V", "R_10", "R_25"]
TIMEFRAMES = {
    "H4": 14400,
    "H1": 3600,
    "M15": 900,
    "M5": 300
}

# Scanning Interval (5 minutes)
SCAN_INTERVAL = 300 

# Cooldown (4 hours per level)
COOLDOWN_PERIOD = 14400 

# Timezone
TIMEZONE = "Africa/Lagos"  # West African Time (WAT)
