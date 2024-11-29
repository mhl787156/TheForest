#!/bin/bash

# Define variables for the virtual serial ports and tmuxinator configuration
SOCAT_PORT_1="/dev/ttyS10"
SOCAT_PORT_2="/dev/ttyS11"

socat -d -d pty,raw,echo=0 pty,raw,echo=0
