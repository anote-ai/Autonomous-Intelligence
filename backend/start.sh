#!/bin/bash
set -e

# Activate the virtual environment
source /opt/venv/bin/activate

# Start Flask
echo "Starting Flask application..."
exec flask run --host=0.0.0.0 --port=5000

#!/bin/bash
ray start --head --port=6379 --dashboard-port=9998
sleep 3  # small delay to ensure Ray is ready
flask run --host=0.0.0.0 --port=5000 --no-reload
