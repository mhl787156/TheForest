#!/bin/bash

# Set up port and baud rate
PORT=${1:-/dev/ttyACM0}
BAUD=${2:-9600}

# Create a timestamped log file
LOGFILE="teensy_log_$(date +%Y%m%d_%H%M%S).txt"

echo "Starting Teensy communication monitor on $PORT at $BAUD baud"
echo "Logging to $LOGFILE"
echo "Press Ctrl+C to stop"

# Function to send test commands
send_test_command() {
    echo -e "$1" > $PORT
    echo "[SENT] $1" | tee -a $LOGFILE
}

# Start logging received data
(stty -F $PORT $BAUD raw; cat $PORT | while read -N 1 char; do 
    printf "$char" 
    printf "$char" >> $LOGFILE
done) &
CAT_PID=$!

# Send test commands periodically
while true; do
    echo "[$(date +%T)] Sending test commands..." | tee -a $LOGFILE
    send_test_command "GETLED;\n\r"
    sleep 5
    send_test_command "LED,0,$(( RANDOM % 255 )),255;\n\r"
    sleep 5
done

# Clean up on exit
trap "kill $CAT_PID; echo 'Monitor stopped'" EXIT 