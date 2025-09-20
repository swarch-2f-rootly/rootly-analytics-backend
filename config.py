# Analytics Service Configuration
# Copy this file to .env and adjust values as needed

# InfluxDB Configuration
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-influxdb-token-here
INFLUXDB_BUCKET=rootly-bucket
INFLUXDB_ORG=rootly-org

# Server Configuration
HOST=0.0.0.0
PORT=8000

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,*

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s

# Application Configuration
APP_NAME=rootly Analytics Service
APP_VERSION=1.0.0
DEBUG=true

# Development/Production flags
ENVIRONMENT=development

