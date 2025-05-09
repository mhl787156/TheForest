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
import serial

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

def test_teensy_communication(port='/dev/ttyACM0', baud=9600, duration=60):
    # Open serial connection
    ser = serial.Serial(port, baud)
    print(f"Connected to {port} at {baud} baud")
    
    # Record start time
    start_time = time.time()
    end_time = start_time + duration
    
    # Test commands to send
    test_commands = [
        "LED,0,100,255;",    # Set tube 0 to hue 100, brightness 255
        "GETLED;",           # Request LED status
        "ALLLED,0,255,0,50,255,0,100,255,0,150,255,0,200,255,0,250,255,0;"  # Set all LEDs
    ]
    command_index = 0
    last_command_time = start_time
    
    # Create log file
    log_file = open("teensy_communication_log.txt", "w")
    
    try:
        while time.time() < end_time:
            # Send test command every 5 seconds
            current_time = time.time()
            if current_time - last_command_time > 5:
                command = test_commands[command_index % len(test_commands)]
                ser.write(command.encode())
                log_entry = f"[{current_time - start_time:.2f}s] SENT: {command}\n"
                print(log_entry, end="")
                log_file.write(log_entry)
                
                command_index += 1
                last_command_time = current_time
            
            # Read and log any incoming data
            if ser.in_waiting:
                data = ser.readline().decode('utf-8', errors='ignore').strip()
                if data:
                    log_entry = f"[{current_time - start_time:.2f}s] RECEIVED: {data}\n"
                    print(log_entry, end="")
                    log_file.write(log_entry)
            
            # Short sleep to avoid hogging CPU
            time.sleep(0.01)
                
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    finally:
        ser.close()
        log_file.close()
        print(f"\nTest completed. Log saved to teensy_communication_log.txt")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test Teensy-Pi communication")
    parser.add_argument("--port", default="/dev/ttyACM0", help="Serial port")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    args = parser.parse_args()
    
    test_teensy_communication(args.port, args.baud, args.duration) 