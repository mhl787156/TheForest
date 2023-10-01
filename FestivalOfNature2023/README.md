# The Forest

Project for the Forest of nature festival 2023


## Installation and Setup 

### Requirements

This setup requires the `sonic-pi` raspberry pi installation. 

### Download

You should first git clone this onto the associated raspberry pi. 

```
git clone https://github.com/mhl787156/TheForest
```

### Samples

You will want to download the set of samples from teams and place them in a folder `TheForest/Samples`

Note that sonic-pi is designed for short samples which can fit into memory. Therefore we would recommend samples of length 30 seconds to a minute. 

Note also that you have to set the default sound interface to be the speakers, this can be done through `sudo raspi-config`

### Sonic pi script installation

We wish for sonic pi to run our backend script by default. To do this we will overwrite the default sonic-pi startup file. 

```
cp forest_backend_sonicpi.rb ~/.sonic-pi/init.rb
cp forest_backend_sonicpi.rb ~/.sonic-pi/config/init.rb
```

> Note: It is not clear whether the default is `init.rb` or `config/init.rb` therefore recommendation is to overwrite both. This may be placed in an installation script at some point. 

### NFC 

This work assumes the NFC hat is used, or the NFC's are wired using the standard SPI method. This takes GPIO pins 8. 16, 18 and 10. The generic NFC Contorller is in `nfc_controller.py`

In its current state it assumes the use of RFID tags or stickers which when read emit a string ID. 

### LEDs / Extra sensors

It is assumed that the LEDS and other sensors are being handled by an offboard Arduino running the `led_arduino_control.ino` assumed to be connected over USB. 

> Note: it was attempted to integrate the LEDs into the Pi without an offboard Arduino, but there appears to be a clash between the SPI and LED control. Perhaps stemming from a shared PWM signal or something similar. 

This `ino` file controls the LEDs using the [`ws281fx` library](https://github.com/kitesurfer1404/WS2812FX). The raspberry pi can control the arduino over serial by sending strings of the form `<segment_id>,<mode_id>;` where the segment is a contiguous chunk of lights, and the modes are listed at [this link](https://github.com/kitesurfer1404/WS2812FX/blob/master/src/modes_arduino.h). 

> Note: the `main.py` might fail if it cannot find the right serial connection e.g. `/dev/ttyACM0`. This can change if there are other USBs plugged in, or on a whim. Therefore an idev rule should be added at somepoint to bind the arduino usb to `/dev/arduino` or something similar. 

## Running The System 

### Starting the main system 

First start sonic-pi. 

1. If you have the gui, start the GUI as if its any other GUI application. 
2. If you are using CLI and have to use it in headless mode, first ensure that you run `export DISPLAY=:0` either manually, or its automatically run via the `~/.bashrc`. Then run `sonic-pi &`. Them ampersand is required for it to run in the background. 

Then in the terminal, you can run the core python control script. 

```bash
cd TheForest
python main.py
```

The raspberry pi's should be setup such that sonic-pi is started by the `autostart` utility, and the `main.py` is automatically run via `systemd`. To check the systemd process you can run `sudo systemctl status theforest.service`, or run `journalctl -u theforest` (Use `Ctrl+g` to go to the bottom quickly). 

> Note: If the screens are running, you should see sonic-pi start and run somethding. 


### Registering objects

Objects can be registered using the `link_tags_to_sounds.py` script. First ensure that `main.py` is not running, then run the script. 

```
cd TheForest
python link_tags_to_sounds.py
```

This script will load up the list of samples within `TheForest/Samples` and one-by-one ask you to place an object on any one of the RFID readers. This will read the ID off of the object's RFID tag and register it to that object. It will continue until Ctrl+C is pressed or you have run out of samples. Once exited, the script will save the mapping into `sdict.json`. 

> Note `main.py` reads `sdict.json` into memory at start time. Therefore if you change `sdict.json`, you will need to restart `main.py`. 