#!/usr/bin/env python3
"""
Test script to verify LED status reading and pitch adjustment functionality.
This script simulates the interaction between the Teensy and the main controller.

Usage:
    python test_led_pitch.py
"""

import time
import random
import sys
import os
import threading
import queue

# Add the raveforest directory to sys.path so we can import from it
sys.path.append(os.path.join(os.path.dirname(__file__), 'raveforest'))

from pillar_hw_interface import Pillar
from mapping_interface import SoundState, FixedMapper
from sound_manager import SoundManager

class MockSerial:
    """
    Mock serial port for testing without hardware.
    Simulates sending and receiving data through serial connection.
    """
    def __init__(self):
        self.buffer = queue.Queue()
        self.is_open = True
    
    def write(self, data):
        """Handle data sent to the serial port"""
        data_str = data.decode('utf-8')
        print(f"[MOCK SERIAL] Received command: {data_str.strip()}")
        
        # Simulate Teensy responding to GETLED command
        if "GETLED" in data_str:
            # Generate random LED status for 6 tubes
            for i in range(6):
                hue = random.randint(0, 255)
                brightness = random.randint(100, 255)
                self.buffer.put(f"LED,{i},{hue},{brightness}\n")
            print("[MOCK SERIAL] Sent LED status response")
    
    def readline(self):
        """Simulate reading a line from serial"""
        try:
            data = self.buffer.get_nowait()
            return data.encode('utf-8')
        except queue.Empty:
            # Simulate no data available
            time.sleep(0.1)
            return b""
    
    def close(self):
        """Close the serial connection"""
        self.is_open = False

def serial_for_url(url, baudrate=9600):
    """Mock implementation of serial_for_url"""
    print(f"[MOCK SERIAL] Creating mock serial for {url}")
    return MockSerial()

# Replace the actual serial with our mock version
import serial
serial.serial_for_url = serial_for_url

def test_led_status_and_pitch():
    """Test the LED status reading and pitch adjustment functionality"""
    print("Starting test_led_status_and_pitch...")
    
    # Create a pillar manager with mock serial
    pillar_config = {
        "id": 0,
        "port": "virtual_port",
        "num_tubes": 6,
        "notes": [0, 2, 4, 5, 7, 9],
        "octave": 4,
        "map": "FixedMapper"
    }
    
    pillar_manager = Pillar(**pillar_config)
    
    # Create a sound state for testing
    sound_state = SoundState({
        "volume": {
            "melody": 1.0,
            "harmony": 0.5,
            "background": 0.3
        },
        "instruments": {
            "melody": "piano",
            "harmony": "flute",
            "background": "strings"
        },
        "key": 60,
        "bpm": 100,
        "melody_scale": "pentatonic",
        "melody_number": 0,
        "baseline_style": "long",
    })
    
    # Initial reaction notes
    sound_state.append_reaction_notes(60)  # Middle C
    sound_state.append_reaction_notes(64)  # E
    sound_state.append_reaction_notes(67)  # G
    
    print(f"Initial reaction notes: {sound_state.reaction_notes}")
    print(f"Initial key: {sound_state.key}")
    
    # Request LED status
    print("Requesting LED status...")
    pillar_manager.request_led_status()
    
    # Give time for the mock serial to process
    time.sleep(1)
    
    # Read from serial to get LED status
    pillar_manager.read_from_serial()
    
    # Display the LED status
    led_status = pillar_manager.get_all_light_status()
    print(f"Received LED status: {led_status}")
    
    # Adjust pitch by +3
    print("Adjusting pitch by +3...")
    sound_state.adjust_pitch(3)
    
    # Display the updated pitch
    print(f"Updated reaction notes: {sound_state.reaction_notes}")
    print(f"Updated key: {sound_state.key}")
    
    # Verify the pitch has been increased by 3
    assert sound_state.reaction_notes[0] == 63, "First note should be 63 (C+3)"
    assert sound_state.reaction_notes[1] == 67, "Second note should be 67 (E+3)"
    assert sound_state.reaction_notes[2] == 70, "Third note should be 70 (G+3)"
    assert sound_state.key == 63, "Key should be 63 (C+3)"
    
    print("Test completed successfully!")

if __name__ == "__main__":
    test_led_status_and_pitch() 