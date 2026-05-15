import tkinter as tk
from tkinter import ttk
import random
import numpy as np
import sounddevice as sd
import threading
import time
import math

NOTE_NAMES = [
    "C", "C#/Db", "D", "D#/Eb", "E", "F",
    "F#/Gb", "G", "G#/Ab", "A", "A#/Bb", "B"
]

SAMPLE_RATE = 44100
BLOCK_SIZE = 4096


def midi_to_note(midi):
    name = NOTE_NAMES[midi % 12]
    octave = (midi // 12) - 1
    return f"{name}{octave}"


def note_name_only(note):
    return ''.join([c for c in note if not c.isdigit() and c != "-"])


def notes_match(detected_note, target_note):
    detected_variants = detected_note.split("/")
    target_variants = target_note.split("/")

    return any(
        d.upper() == t.upper()
        for d in detected_variants
        for t in target_variants
    )


def freq_to_midi(freq):
    return round(69 + 12 * math.log2(freq / 440.0))


def midi_to_freq(midi):
    return 440.0 * (2 ** ((midi - 69) / 12))


def cents_off(freq, midi):
    target_freq = midi_to_freq(midi)
    return 1200 * math.log2(freq / target_freq)


def detect_pitch(audio):
    audio = audio.flatten()
    audio = audio - np.mean(audio)

    if np.max(np.abs(audio)) < 0.01:
        return None

    corr = np.correlate(audio, audio, mode="full")
    corr = corr[len(corr) // 2:]

    min_freq = 25
    max_freq = 500

    min_lag = int(SAMPLE_RATE / max_freq)
    max_lag = int(SAMPLE_RATE / min_freq)

    corr[:min_lag] = 0
    peak = np.argmax(corr[min_lag:max_lag]) + min_lag

    if peak == 0:
        return None

    return SAMPLE_RATE / peak


class BassNoteTrainer:
    def __init__(self, root):
        self.root = root
        self.root.title("5-String Bass Note Trainer")

        self.target_note = None
        self.listening = False
        self.tuner_mode = False
        self.score = 0
        self.total = 0

        self.build_gui()
        self.new_question()

    def build_gui(self):
        main = ttk.Frame(self.root, padding=20)
        main.grid()

        ttk.Label(
            main,
            text="5-String Bass Note Trainer",
            font=("Segoe UI", 18, "bold")
        ).grid(row=0, column=0, columnspan=3, pady=10)

        ttk.Label(
            main,
            text="Play the prompted note anywhere on the bass"
        ).grid(row=1, column=0, columnspan=3)

        self.question_label = ttk.Label(
            main,
            text="",
            font=("Segoe UI", 24, "bold")
        )
        self.question_label.grid(row=2, column=0, columnspan=3, pady=25)

        self.detected_label = ttk.Label(
            main,
            text="Detected: --",
            font=("Segoe UI", 14)
        )
        self.detected_label.grid(row=3, column=0, columnspan=3, pady=5)

        self.tuner_label = ttk.Label(
            main,
            text="Tuner: --",
            font=("Segoe UI", 14)
        )
        self.tuner_label.grid(row=4, column=0, columnspan=3, pady=5)

        self.result_label = ttk.Label(
            main,
            text="",
            font=("Segoe UI", 14)
        )
        self.result_label.grid(row=5, column=0, columnspan=3, pady=10)

        ttk.Button(
            main,
            text="New Note",
            command=self.new_question
        ).grid(row=6, column=0, pady=10, padx=5)

        self.listen_button = ttk.Button(
            main,
            text="Start Listening",
            command=self.toggle_listening
        )
        self.listen_button.grid(row=6, column=1, pady=10, padx=5)

        self.tuner_button = ttk.Button(
            main,
            text="Tuner Mode",
            command=self.toggle_tuner_mode
        )
        self.tuner_button.grid(row=6, column=2, pady=10, padx=5)

        self.score_label = ttk.Label(
            main,
            text="Score: 0/0"
        )
        self.score_label.grid(row=7, column=0, columnspan=3, pady=10)

    def new_question(self):
        self.tuner_mode = False
        self.tuner_button.config(text="Tuner Mode")

        self.target_note = random.choice(NOTE_NAMES)

        self.question_label.config(
            text=f"Play: {self.target_note}"
        )

        self.result_label.config(text="")
        self.detected_label.config(text="Detected: --")
        self.tuner_label.config(text="Tuner: --")

    def toggle_tuner_mode(self):
        self.tuner_mode = not self.tuner_mode

        if self.tuner_mode:
            self.question_label.config(text="Tuner Mode")
            self.result_label.config(text="Play a single open string or fretted note")
            self.tuner_button.config(text="Exit Tuner")
        else:
            self.tuner_button.config(text="Tuner Mode")
            self.new_question()

        if not self.listening:
            self.toggle_listening()

    def toggle_listening(self):
        if not self.listening:
            self.listening = True
            self.listen_button.config(text="Stop Listening")
            threading.Thread(target=self.listen_loop, daemon=True).start()
        else:
            self.listening = False
            self.listen_button.config(text="Start Listening")

    def listen_loop(self):
        with sd.InputStream(
            channels=1,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE
        ) as stream:

            while self.listening:
                audio, _ = stream.read(BLOCK_SIZE)
                freq = detect_pitch(audio)

                if freq:
                    midi = freq_to_midi(freq)
                    detected_note = midi_to_note(midi)
                    detected_name = note_name_only(detected_note)
                    cents = cents_off(freq, midi)

                    if cents > 5:
                        tuning_status = f"{cents:.1f} cents sharp"
                    elif cents < -5:
                        tuning_status = f"{abs(cents):.1f} cents flat"
                    else:
                        tuning_status = "in tune"

                    self.root.after(
                        0,
                        self.detected_label.config,
                        {"text": f"Detected: {detected_note} ({freq:.1f} Hz)"}
                    )

                    self.root.after(
                        0,
                        self.tuner_label.config,
                        {"text": f"Tuner: {detected_note} — {tuning_status}"}
                    )

                    if self.tuner_mode:
                        time.sleep(0.05)
                        continue

                    if notes_match(detected_name, self.target_note):
                        self.score += 1
                        self.total += 1

                        self.root.after(
                            0,
                            self.result_label.config,
                            {"text": f"Correct: {self.target_note}"}
                        )

                        self.root.after(
                            0,
                            self.score_label.config,
                            {"text": f"Score: {self.score}/{self.total}"}
                        )

                        time.sleep(1)
                        self.root.after(0, self.new_question)

                time.sleep(0.05)


if __name__ == "__main__":
    root = tk.Tk()
    app = BassNoteTrainer(root)
    root.mainloop()
