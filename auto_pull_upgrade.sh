#!/bin/bash

CONTAINER_ID="9d90df619613"  # Replace with your Docker container name

git fetch

if [ "$(git rev-parse HEAD)" != "$(git rev-parse @{u})" ]; then
    git pull
    docker restart "CONTAINER_ID"
    echo "Updated and restarted Odoo container."
else
    echo "Already up to date"
fi
