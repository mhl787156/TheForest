#!/bin/bash

# Define variables for the virtual serial ports and tmuxinator configuration
SOCAT_PORT_1="/dev/ttyS10"
SOCAT_PORT_2="/dev/ttyS11"

# Check for dependencies
if ! command -v socat &>/dev/null || ! command -v tmuxinator &>/dev/null; then
  echo "Error: socat and tmuxinator are required but not installed."
  exit 1
fi

# Output instructions and launch tmuxinator
echo "Launching tmux environment with tmuxinator..."
tmuxinator start -p "testing/tmux_session.yaml" \
    port1=${SOCAT_PORT_1} \
    port2=${SOCAT_PORT_2}
