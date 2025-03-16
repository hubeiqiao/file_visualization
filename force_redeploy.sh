#!/bin/bash

# This script forces a redeploy on Vercel by adding a timestamp to a file
# and committing the change

# Generate a timestamp
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Create or update the deployment timestamp file
echo "Last deployment: $TIMESTAMP" > deploy_timestamp.txt

# Commit and push the change
git add deploy_timestamp.txt
git commit -m "Force redeploy with timestamp: $TIMESTAMP"
git push origin production-ready
git push origin main

echo "Forced redeploy initiated with timestamp: $TIMESTAMP" 