# LED-Matrix-32x24-from-12-8x8

## Overview

An Arduino-based LED matrix display
that plays black-and-white video using
12 MAX7219 LED matrices.

## Hardware

- Arduino Uno
- 12x MAX7219 8x8 LED matrices
- Jumper wires
- External power supply

## Display Configuration

- Resolution: 32x24 pixels
- Color: Monochrome
- Three independent groups
- Four MAX7219 modules per group

## Pin Configuration

| Arduino | MAX7219 |
|---------|---------|
| D12 | DIN |
| D11 | CLK |
| D10 | CS - Group 1 |
| D9  | CS - Group 2 |
| D8  | CS - Group 3 |

## Project Structure

- firmware/ - Arduino code
- photos/ - Hardware photos
- docs/ - Wiring documentation

## Demo

Add project photos and a video here.

## How it works

Video frames are converted into
binary image data and stored in frames.h.

Arduino reads the frames from Flash memory
and displays them on the LED matrices.
