#!/bin/bash

# Function to handle Ctrl+C
function cleanup() {
    echo "Stopping processes..."
    kill -TERM "$pid1" 2>/dev/null
    kill -TERM "$pid2" 2>/dev/null
    exit 0
}

# Set up Ctrl+C handler
trap cleanup INT

# Run the first Python script in the background
python raveforest/main.py &
pid1=$!

# Run the second Python script in the background
python gui/gui.py --host=0.0.0.0 &
pid2=$!

# Wait for both processes to finish
wait "$pid1"
wait "$pid2"
