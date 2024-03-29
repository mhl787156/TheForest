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

MYIP=`ip addr show $(ip route | awk '/default/ { print $5 }') | grep "inet" | head -n 1 | awk '/inet/ {print $2}' | cut -d'/' -f1`

# Run the first Python script in the background
python raveforest/main.py --ws-host=0.0.0.0&
pid1=$!

# Run the second Python script in the background
python gui/gui.py --host=0.0.0.0 --ws-host="${MYIP}" &
pid2=$!

# Wait for both processes to finish
wait "$pid1"
wait "$pid2"
