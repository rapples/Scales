# Guitar Mode Finder / Scales App

A Streamlit prototype for exploring guitar, bass, piano, and mallet-style scale patterns one selected scale at a time.

The app is designed to show a single playable scale path instead of exposing a full master chart. Users choose a root note, scale family, and scale/mode, and the app renders only the selected ascending path starting from the root on the lowest string.

## Features

- Select a root note: `C`, `C#`, `D`, etc.
- Select a scale family:
  - Diatonic Modes
  - Pentatonic
  - Blues
  - Symmetric
- Select a scale or mode:
  - Ionian / Major
  - Dorian
  - Phrygian
  - Lydian
  - Mixolydian
  - Aeolian / Minor
  - Locrian
  - Major Pentatonic
  - Minor Pentatonic
  - Blues scales
  - Whole Tone
  - Diminished
- Render one selected ascending scale path only
- Start from the root note on the lowest string
- Continue the scale across the instrument
- Show only the selected path notes, not every matching note on the neck
- Synchronized visual playback
- Multiple instrument views:
  - Guitar Neck
  - Bass Guitar Neck
  - Piano Keyboard
  - Mallet Bars
- Audio playback options:
  - Built-in synth
  - Public web samples
- Adjustable playback speed
- Adjustable fret range
- Adjustable position width

## Screens / Views

The app supports several visual renderers using the same selected scale path:

### Guitar Neck

Displays a guitar-style fretboard with strings, frets, note circles, and a subtle path line.

### Bass Guitar Neck

Uses a 4-string bass tuning view.

### Piano Keyboard

Maps the same selected notes to piano keys.

### Mallet Bars

Shows the selected path as a simple mallet-style instrument view.

## Installation

Clone the repository:

```bash
git clone https://github.com/rapples/Scales.git
 
