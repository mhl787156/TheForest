# Future 2023 Project "The Pillars"

## Concept

We have two pillars made of a number of sub-tubes. 

- Each sub-tube can be interacted with using capacitive touch
- Each sub-tube can be lit up by a set of LEDs

On touch, the system will choose a note and colour to play and display.

The notes are played in two ways using sonic-pi

- On touch, its note will immediately sound
- The note gets added to the sequencer which goes around at a specified bpm and plays the note related to each sub-tube.

## Usage

### Running

First run sonic-pi (On both of the raspberry pis it starts on boot)

You can run the controller and the gui using the `./run.sh` on linux

You can run the primary program using `python raveforest/main.py`

You can run the connecting gui using `python gui/gui.py`

> There will be a number of dependencies, one in particular is `psonic` or the `python-sonic library`. As of writing you should install `mhl787156/python-sonic` as it contains fixes for sonic-pi v4.4. 
> ```
> git clone https://github.com/mhl787156/python-sonic.git
> cd python-sonic
> pip install -e .
> ```

An arduino or teensy should have `arduino/arduino.ino` uploaded onto it

### Configuration

The configuration is contained within `config/config.json`

```json
{
    "notes_to_color": 1,
    "notes": [50, 30, 70, 100, 25, 90, 60],
    "colors": [
        [100, 50],
        [70, 50],
        [30, 50],
        [150, 50],
        [220, 50],
        [80, 50],
        [180, 50]
    ],
    "mapping_id": 1,
    "pillars": [
        {
            "id": 0,
            "port": "/dev/ttyACM0",
            "pan": 0
        }
    ],
    "bpm": 60,
    "sonic-pi-ip": "172.18.144.1",
    "sonic-pi-config-file": "/mnt/c/Users/qo18522/.sonic-pi/log/spider.log"
}

```

Here you should specify notes and mappings, which built in mapping function you wish to use, the specific setup of the pillars (this includes the serial port which you will need to find).

## Implementation

This project is composed of a controller and a gui. There is a lot of concurrency involved with the use of threading. This is because we are having to deal with many concurrent controls. 

### Controller

The controller is the core of this project. describing each file:

- main.py: This file is the main entry point of the program. It initalises and starts everything as well as contains the main event loop. 
    - It starts the pillar serial reader and writer, the Sound Manager for timings and conencting to sonic pi and the websockets for communicating with the GUI
- pillar_hw_interface.py: This file primarily deals with the serial connection to the pillars. Threading is used to concurrently manage reading and writing to serial to avoid blocking the main thread. 
- sonic.py: This file deals with bpm timing and sending things to sonic-pi to play. A thread is started for timing at the specified BPM. This BPM can be changed on the fly. A thread is also started for each pillar. These threads implement the sequencer. A condition is used within the timing to coordinate all the involved threads playing notes. 
- MappingInterface.py: This file defines the mappings between the currently activated sub-tubes of a pillar to the notes and light patterns they should show. It is designed such that this file should have multiple different implementations which can be switched up on the fly. 
- config.py: Contains a small number of variables [deperecated]

### GUI

A dash gui has been (partially) built intended for the realtime control and monitoring of the system. 

Websockets are used to communicate between the controller and the gui. 