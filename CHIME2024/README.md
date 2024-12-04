# CHIME 2024 

## Concept

We have two pillars made of a number of sub-tubes. 

- Each sub-tube can be interacted with using capacitive touch
- Each sub-tube can be lit up by a set of LEDs
- Eac pillar will generate some sounds

This uses the V3 Forest setup but with a new sound generation system. Designated V3S

## Usage

Install scamp and scamp_extensions

```
pip3 install --user scamp scamp_extensions
```

Then run the following to start it up

```
python raveforest/main.py
```

It will read the configuration at `config/config.json` with the parameters linked to the hostname of the sytem.

> If running on a new PI you will need to add a configuration for it within config.json

### Local Testing

The above works if running on one of the designated FONPIs. However we have also built a utility for local testing of the sound system. 

You can start a virtual serial port using `socat` this is encapusalted in the tmux_session.yaml

> You will need to `sudo apt-get install tmux tmuxinator pygame`

```bash
./arduino_test_environment.sh
```

It will then show you the names of the virtual serial ports. Use these to connect up `main.py` and the pretend interface

Run the pretend frontend using

```
python3 testing/mock_teensy --port <serial port from socat>
```

And run the forest

```bash
python3 raveforest/main.py --serial_port <other socat port> --hostname <pretend hostname>
# e.g.
python3 raveforest/main.py --serial_port /dev/pts/3 --hostname fon006
```

## What it does

The Sound Manager now interacts iwth scamp instead of sonic pi to generate sounds. 

The Mapping Interface defines a method of interaction between the touch, light and sound

The raveforest/interfaces.py defines the primary datastructures including:

- The instruments (from scamp)
- The scales (from scamp_extensions)
- The melodies
- The baselines
- **The default state**

**Currently to change the initial defaults of the system you will need to manually change this default state**

## Usage Notes

1. In this new version, the configuration file is linked to the hostname of the machine using it. 
2. Some things are hardcoded look around. especially in DEFAULT_STATE in interfaces

Need to refactor some of this out. 
