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

STRING_CONFIGS = {
    "4 String (E A D G)": {
        "lowest_midi": 28,  # E1
        "highest_midi": 67  # G4
    },
    "5 String (B E A D G)": {
        "lowest_midi": 23,  # B0
        "highest_midi": 67  # G4
    },
    "6 String (B E A D G C)": {
        "lowest_midi": 23,  # B0
        "highest_midi": 72  # C5
    }
}

SAMPLE_RATE = 44100
BLOCK_SIZE = 4096
TUNER_RANGE_CENTS = 50


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
        self.root.title("Bass Note Trainer")

        self.string_config = tk.StringVar(value="5 String (B E A D G)")
        self.target_note = None

        self.listening = False
        self.tuner_mode = False

        self.correct = 0
        self.incorrect = 0
        self.total = 0
        self.answer_locked = False

        self.build_gui()
        self.new_question()

    def build_gui(self):
        main = ttk.Frame(self.root, padding=20)
        main.grid()

        ttk.Label(
            main,
            text="Bass Note Trainer",
            font=("Segoe UI", 18, "bold")
        ).grid(row=0, column=0, columnspan=4, pady=10)

        ttk.Label(
            main,
            text="Play the prompted note anywhere on the bass"
        ).grid(row=1, column=0, columnspan=4)

        ttk.Label(
            main,
            text="Bass Type:"
        ).grid(row=2, column=0, pady=5, sticky="e")

        self.string_selector = ttk.Combobox(
            main,
            textvariable=self.string_config,
            values=list(STRING_CONFIGS.keys()),
            state="readonly",
            width=24
        )
        self.string_selector.grid(row=2, column=1, columnspan=3, pady=5, sticky="w")
        self.string_selector.bind("<<ComboboxSelected>>", self.on_string_config_changed)

        self.question_label = ttk.Label(
            main,
            text="",
            font=("Segoe UI", 24, "bold")
        )
        self.question_label.grid(row=3, column=0, columnspan=4, pady=20)

        self.detected_label = ttk.Label(
            main,
            text="Detected: --",
            font=("Segoe UI", 14)
        )
        self.detected_label.grid(row=4, column=0, columnspan=4, pady=5)

        self.tuner_label = ttk.Label(
            main,
            text="Tuner: --",
            font=("Segoe UI", 14)
        )
        self.tuner_label.grid(row=5, column=0, columnspan=4, pady=5)

        self.tuner_canvas = tk.Canvas(
            main,
            width=360,
            height=90,
            bg="white",
            highlightthickness=1,
            highlightbackground="#cccccc"
        )
        self.tuner_canvas.grid(row=6, column=0, columnspan=4, pady=10)
        self.draw_tuner(0)

        self.result_label = ttk.Label(
            main,
            text="",
            font=("Segoe UI", 14)
        )
        self.result_label.grid(row=7, column=0, columnspan=4, pady=10)

        ttk.Button(
            main,
            text="New Note",
            command=self.new_question
        ).grid(row=8, column=0, pady=10, padx=5)

        self.listen_button = ttk.Button(
            main,
            text="Start Listening",
            command=self.toggle_listening
        )
        self.listen_button.grid(row=8, column=1, pady=10, padx=5)

        self.tuner_button = ttk.Button(
            main,
            text="Tuner Mode",
            command=self.toggle_tuner_mode
        )
        self.tuner_button.grid(row=8, column=2, pady=10, padx=5)

        ttk.Button(
            main,
            text="Reset Score",
            command=self.reset_score
        ).grid(row=8, column=3, pady=10, padx=5)

        self.score_label = ttk.Label(
            main,
            text="Correct: 0 | Incorrect: 0 | Total: 0"
        )
        self.score_label.grid(row=9, column=0, columnspan=4, pady=10)

    def on_string_config_changed(self, event=None):
        self.new_question()

    def draw_tuner(self, cents):
        self.tuner_canvas.delete("all")

        width = 360
        height = 90
        center_x = width // 2
        center_y = 65

        self.tuner_canvas.create_text(
            center_x,
            10,
            text="Flat        In Tune        Sharp",
            font=("Segoe UI", 9)
        )

        self.tuner_canvas.create_line(
            30,
            center_y,
            width - 30,
            center_y,
            width=2
        )

        self.tuner_canvas.create_line(
            center_x,
            20,
            center_x,
            center_y + 10,
            width=2
        )

        for offset in [-50, -25, 0, 25, 50]:
            x = center_x + int((offset / TUNER_RANGE_CENTS) * 150)
            tick_height = 20 if offset == 0 else 12

            self.tuner_canvas.create_line(
                x,
                center_y - tick_height,
                x,
                center_y + tick_height,
                width=2 if offset == 0 else 1
            )

            self.tuner_canvas.create_text(
                x,
                center_y + 25,
                text=str(offset),
                font=("Segoe UI", 8)
            )

        clipped_cents = max(-TUNER_RANGE_CENTS, min(TUNER_RANGE_CENTS, cents))
        needle_x = center_x + int((clipped_cents / TUNER_RANGE_CENTS) * 150)

        self.tuner_canvas.create_line(
            center_x,
            15,
            needle_x,
            center_y,
            width=3
        )

        self.tuner_canvas.create_oval(
            center_x - 5,
            10,
            center_x + 5,
            20,
            fill="black"
        )

    def new_question(self):
        self.tuner_mode = False
        self.answer_locked = False
        self.tuner_button.config(text="Tuner Mode")

        config = STRING_CONFIGS[self.string_config.get()]

        target_midi = random.randint(
            config["lowest_midi"],
            config["highest_midi"]
        )

        self.target_note = note_name_only(
            midi_to_note(target_midi)
        )

        self.question_label.config(text=f"Play: {self.target_note}")
        self.result_label.config(text="")
        self.detected_label.config(text="Detected: --")
        self.tuner_label.config(text="Tuner: --")
        self.draw_tuner(0)

    def reset_score(self):
        self.correct = 0
        self.incorrect = 0
        self.total = 0
        self.answer_locked = False
        self.update_score_label()
        self.result_label.config(text="Score reset")

    def update_score_label(self):
        self.score_label.config(
            text=f"Correct: {self.correct} | Incorrect: {self.incorrect} | Total: {self.total}"
        )

    def toggle_tuner_mode(self):
        self.tuner_mode = not self.tuner_mode

        if self.tuner_mode:
            self.question_label.config(text="Tuner Mode")
            self.result_label.config(text="Play a single open string or fretted note")
            self.tuner_button.config(text="Exit Tuner")
            self.answer_locked = True
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

                    self.root.after(0, self.draw_tuner, cents)

                    if self.tuner_mode:
                        time.sleep(0.05)
                        continue

                    if not self.answer_locked:
                        self.answer_locked = True
                        self.total += 1

                        if notes_match(detected_name, self.target_note):
                            self.correct += 1

                            self.root.after(
                                0,
                                self.result_label.config,
                                {"text": f"Correct: {self.target_note}"}
                            )
                        else:
                            self.incorrect += 1

                            self.root.after(
                                0,
                                self.result_label.config,
                                {
                                    "text": (
                                        f"Incorrect. Played {detected_name}, "
                                        f"target was {self.target_note}"
                                    )
                                }
                            )

                        self.root.after(0, self.update_score_label)

                        time.sleep(1.2)
                        self.root.after(0, self.new_question)

                time.sleep(0.05)


if __name__ == "__main__":
    root = tk.Tk()
    app = BassNoteTrainer(root)
    root.mainloop()
