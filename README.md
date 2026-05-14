# bass
Bass utils
# 5-String Bass Note Trainer

A simple Python GUI application for learning the notes on a 5-string bass guitar using your microphone.

The app prompts you with a note name and listens through your system microphone to detect whether you played the correct note anywhere on the fretboard.

Designed for:

* Fretboard memorisation
* Note recognition
* Position independence
* Ear training
* Bass practice drills

---

## Features

* GUI interface using Tkinter
* Real-time microphone pitch detection
* Random note prompts
* Works with 5-string bass standard tuning:

  * B E A D G
* Score tracking
* Accepts the note in any position/octave

---

## Screenshot

Example prompt:

```text
Play: F#
```

Detected input:

```text
Detected: F#1 (46.2 Hz)
```

---

## Requirements

* Python 3.10+
* Microphone or audio interface
* Windows / Linux / macOS

---

## Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/bass-note-trainer.git
cd bass-note-trainer
```

Install dependencies:

```bash
pip install sounddevice numpy
```

---

## Running

```bash
python bass_note_gui_trainer.py
```

---

## Recommended Setup

For best pitch detection results:

* Plug bass into an audio interface
* OR place microphone near bass amp
* Use a reasonably quiet room
* Avoid excessive distortion/fuzz

Laptop microphones may struggle with very low frequencies like the low B string.

---

## How It Works

The application:

1. Displays a random target note
2. Listens to microphone input
3. Detects pitch using autocorrelation
4. Converts detected frequency into a musical note
5. Checks whether the played note matches the target

---

## Example Practice Ideas

* Play every note in one position
* Play notes only on one string
* Ascending chromatic exercises
* Practice octave locations
* Timed drills

---

## Future Ideas

Possible future features:

* Fretboard visualiser
* Required string mode
* Scale trainer
* Interval trainer
* Arpeggio trainer
* MIDI input support
* Adjustable difficulty
* Alternate tunings
* Timing/rhythm mode
* Statistics/history tracking

---

## Known Limitations

* Very low bass frequencies can be difficult for cheap microphones
* Pitch detection is monophonic (single notes only)
* Heavy effects/distortion may reduce accuracy

---

## License

MIT License

---

## Credits

Built with:

* Python
* Tkinter
* NumPy
* sounddevice

Inspired by practical fretboard training for bass players.
