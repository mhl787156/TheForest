# CHIME 2024 

## Concept

We have two pillars made of a number of sub-tubes. 

- Each sub-tube can be interacted with using capacitive touch
- Each sub-tube can be lit up by a set of LEDs
- Eac pillar will generate some sounds

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

## What it does

The Sound Manager now interacts iwth scamp instead of sonic pi to generate sounds. 

The Mapping Interface defines a method of interaction between the touch, light and sound