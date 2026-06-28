import streamlit as st
import numpy as np
import wave
import io
import html
import json
import logging
import urllib.request


# ============================================================
# Guitar Mode Finder Prototype
# ------------------------------------------------------------
# Install:
#   pip install streamlit numpy
#
# Run:
#   streamlit run app.py
# ============================================================


# ----------------------------
# Music data
# ----------------------------

CHROMATIC_SHARPS = [
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B"
]

ENHARMONIC_LABELS = {
    "C#": "C#/Db",
    "D#": "D#/Eb",
    "F#": "F#/Gb",
    "G#": "G#/Ab",
    "A#": "A#/Bb",
}

SCALE_LIBRARY = {
    "Diatonic Modes": {
        "Ionian / Major": [0, 2, 4, 5, 7, 9, 11],
        "Dorian": [0, 2, 3, 5, 7, 9, 10],
        "Phrygian": [0, 1, 3, 5, 7, 8, 10],
        "Lydian": [0, 2, 4, 6, 7, 9, 11],
        "Mixolydian": [0, 2, 4, 5, 7, 9, 10],
        "Aeolian / Minor": [0, 2, 3, 5, 7, 8, 10],
        "Locrian": [0, 1, 3, 5, 6, 8, 10],
    },
    "Pentatonic": {
        "Major Pentatonic": [0, 2, 4, 7, 9],
        "Minor Pentatonic": [0, 3, 5, 7, 10],
        "Suspended Pentatonic": [0, 2, 5, 7, 10],
    },
    "Blues": {
        "Minor Blues": [0, 3, 5, 6, 7, 10],
        "Major Blues": [0, 2, 3, 4, 7, 9],
    },
    "Symmetric": {
        "Whole Tone": [0, 2, 4, 6, 8, 10],
        "Diminished (Half-Whole)": [0, 1, 3, 4, 6, 7, 9, 10],
    },
}

STANDARD_TUNING = [
    ("E", 4),  # high E
    ("B", 3),
    ("G", 3),
    ("D", 3),
    ("A", 2),
    ("E", 2),  # low E
]

BASS_TUNING = [
    ("G", 2),  # high G
    ("D", 2),
    ("A", 1),
    ("E", 1),  # low E
]

SOUND_PRESETS = {
    "Studio Sine": {
        "harmonics": [1.0],
        "attack": 0.012,
        "decay": 0.11,
        "sustain": 0.88,
        "release": 0.09,
        "vibrato_hz": 4.8,
        "vibrato_depth": 0.0018,
        "delay_ms": 0,
        "delay_mix": 0.0,
    },
    "Clean Guitar": {
        "harmonics": [1.0, 0.52, 0.28, 0.16, 0.09],
        "attack": 0.004,
        "decay": 0.17,
        "sustain": 0.58,
        "release": 0.12,
        "vibrato_hz": 5.4,
        "vibrato_depth": 0.0024,
        "delay_ms": 80,
        "delay_mix": 0.1,
    },
    "Warm Lead": {
        "harmonics": [1.0, 0.66, 0.38, 0.19],
        "attack": 0.009,
        "decay": 0.16,
        "sustain": 0.7,
        "release": 0.13,
        "vibrato_hz": 5.8,
        "vibrato_depth": 0.0035,
        "delay_ms": 95,
        "delay_mix": 0.15,
    },
    "Glass Bell": {
        "harmonics": [1.0, 0.74, 0.5, 0.27, 0.18],
        "attack": 0.002,
        "decay": 0.34,
        "sustain": 0.33,
        "release": 0.18,
        "vibrato_hz": 0.0,
        "vibrato_depth": 0.0,
        "delay_ms": 120,
        "delay_mix": 0.2,
    },
}

# Public web sample sources (ToneJS-Instruments sample set, CC-BY 3.0).
WEB_SAMPLE_SOURCES = {
    "Guitar Acoustic (A2 sample)": {
        "url": "https://raw.githubusercontent.com/nbrosowsky/tonejs-instruments/master/samples/guitar-acoustic/A2.wav",
        "base_midi": 45,
    },
    "Piano (C4 sample)": {
        "url": "https://raw.githubusercontent.com/nbrosowsky/tonejs-instruments/master/samples/piano/C4.wav",
        "base_midi": 60,
    },
    "Violin (A4 sample)": {
        "url": "https://raw.githubusercontent.com/nbrosowsky/tonejs-instruments/master/samples/violin/A4.wav",
        "base_midi": 69,
    },
    "Flute (C5 sample)": {
        "url": "https://raw.githubusercontent.com/nbrosowsky/tonejs-instruments/master/samples/flute/C5.wav",
        "base_midi": 72,
    },
}


# ----------------------------
# Music helpers
# ----------------------------

def note_index(note: str) -> int:
    return CHROMATIC_SHARPS.index(note)


def transpose(note: str, semitones: int) -> str:
    return CHROMATIC_SHARPS[(note_index(note) + semitones) % 12]


def build_scale(root: str, scale_kind: str, mode_name: str) -> list[str]:
    intervals = SCALE_LIBRARY[scale_kind][mode_name]
    return [transpose(root, i) for i in intervals]


def note_at_string_fret(open_note: str, fret: int) -> str:
    return transpose(open_note, fret)


def midi_number(note: str, octave: int) -> int:
    return (octave + 1) * 12 + note_index(note)


def midi_for_string_fret(string_index: int, fret: int, tuning: list[tuple[str, int]] = STANDARD_TUNING) -> int:
    open_note, open_octave = tuning[string_index]
    return midi_number(open_note, open_octave) + fret


def note_name_from_midi(midi_num: int) -> str:
    return CHROMATIC_SHARPS[midi_num % 12]


def note_display_name(note: str) -> str:
    """Return display label with enharmonic flat names for black keys."""
    return ENHARMONIC_LABELS.get(note, note)


def octave_from_midi(midi_num: int) -> int:
    return (midi_num // 12) - 1


def note_frequency_from_midi(midi_num: int) -> float:
    """
    Equal temperament frequency.
    A4 = MIDI 69 = 440 Hz.
    """
    return 440.0 * (2 ** ((midi_num - 69) / 12))


def _adsr_envelope(length: int, sample_rate: int, attack: float, decay: float, sustain: float, release: float) -> np.ndarray:
    """Build a simple ADSR envelope for one note."""
    if length <= 0:
        return np.zeros(0, dtype=np.float32)

    attack_n = max(1, int(sample_rate * max(0.001, attack)))
    decay_n = max(1, int(sample_rate * max(0.001, decay)))
    release_n = max(1, int(sample_rate * max(0.001, release)))

    sustain_n = max(1, length - attack_n - decay_n - release_n)
    if attack_n + decay_n + sustain_n + release_n > length:
        sustain_n = max(1, length - attack_n - decay_n - release_n)

    env_a = np.linspace(0.0, 1.0, attack_n, endpoint=False)
    env_d = np.linspace(1.0, max(0.0, min(1.0, sustain)), decay_n, endpoint=False)
    env_s = np.full(sustain_n, max(0.0, min(1.0, sustain)), dtype=np.float64)
    env_r = np.linspace(max(0.0, min(1.0, sustain)), 0.0, release_n, endpoint=True)

    env = np.concatenate([env_a, env_d, env_s, env_r])
    if len(env) < length:
        env = np.pad(env, (0, length - len(env)), mode='constant')
    elif len(env) > length:
        env = env[:length]

    return env.astype(np.float32)


def _synth_note(freq: float, seconds: float, sample_rate: int, preset_name: str) -> np.ndarray:
    """Synthesize one note using additive harmonics and light effects."""
    preset = SOUND_PRESETS.get(preset_name, SOUND_PRESETS["Clean Guitar"])
    sample_count = max(1, int(sample_rate * max(0.05, seconds)))
    t = np.linspace(0, seconds, sample_count, endpoint=False, dtype=np.float64)

    vib_hz = float(preset.get("vibrato_hz", 0.0) or 0.0)
    vib_depth = float(preset.get("vibrato_depth", 0.0) or 0.0)
    vibrato = 1.0 + vib_depth * np.sin(2 * np.pi * vib_hz * t)

    tone = np.zeros_like(t, dtype=np.float64)
    harmonics = preset.get("harmonics", [1.0])
    for idx, amp in enumerate(harmonics, start=1):
        partial_freq = freq * idx
        tone += float(amp) * np.sin(2 * np.pi * partial_freq * t * vibrato)

    max_abs = np.max(np.abs(tone))
    if max_abs > 1e-9:
        tone = tone / max_abs

    env = _adsr_envelope(
        sample_count,
        sample_rate,
        attack=float(preset.get("attack", 0.01) or 0.01),
        decay=float(preset.get("decay", 0.12) or 0.12),
        sustain=float(preset.get("sustain", 0.75) or 0.75),
        release=float(preset.get("release", 0.1) or 0.1),
    )
    tone = tone * env

    delay_ms = int(preset.get("delay_ms", 0) or 0)
    delay_mix = float(preset.get("delay_mix", 0.0) or 0.0)
    if delay_ms > 0 and delay_mix > 0:
        delay_n = int(sample_rate * delay_ms / 1000.0)
        if delay_n > 0 and delay_n < len(tone):
            delayed = np.zeros_like(tone)
            delayed[delay_n:] = tone[:-delay_n]
            tone = (1.0 - delay_mix) * tone + delay_mix * delayed

    return tone.astype(np.float32)


def _decode_wav_bytes(wav_bytes: bytes) -> tuple[np.ndarray, int]:
    """Decode WAV bytes to mono float32 in [-1, 1]."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        sample_width = wf.getsampwidth()
        frame_count = wf.getnframes()
        raw = wf.readframes(frame_count)

    if sample_width == 1:
        arr = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
        arr = (arr - 128.0) / 128.0
    elif sample_width == 2:
        arr = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        arr = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width}")

    if channels > 1:
        arr = arr.reshape(-1, channels).mean(axis=1)

    return arr.astype(np.float32), int(sample_rate)


def _resample_linear(signal: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    """Resample with linear interpolation."""
    if src_rate == dst_rate or len(signal) == 0:
        return signal.astype(np.float32)
    src_idx = np.arange(len(signal), dtype=np.float64)
    dst_len = max(1, int(round(len(signal) * (dst_rate / src_rate))))
    dst_idx = np.linspace(0, len(signal) - 1, dst_len, endpoint=True, dtype=np.float64)
    return np.interp(dst_idx, src_idx, signal).astype(np.float32)


@st.cache_data(show_spinner=False, ttl=24 * 3600)
def _fetch_web_sample(url: str) -> tuple[np.ndarray, int]:
    """Fetch and decode a WAV sample from a public URL."""
    req = urllib.request.Request(url, headers={"User-Agent": "WeedHounds-Scales/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read()
    return _decode_wav_bytes(data)


def _sample_note(
    base_sample: np.ndarray,
    base_midi: int,
    target_midi: int,
    seconds: float,
    sample_rate: int,
) -> np.ndarray:
    """Create one note by pitch-shifting a fetched sample."""
    if len(base_sample) == 0:
        return np.zeros(max(1, int(sample_rate * seconds)), dtype=np.float32)

    ratio = 2 ** ((float(target_midi) - float(base_midi)) / 12.0)
    src_idx = np.arange(len(base_sample), dtype=np.float64)
    read_idx = np.arange(0, len(base_sample), ratio, dtype=np.float64)
    pitched = np.interp(read_idx, src_idx, base_sample).astype(np.float32)

    out_len = max(1, int(sample_rate * max(0.05, seconds)))
    if len(pitched) < out_len:
        pitched = np.pad(pitched, (0, out_len - len(pitched)), mode="constant")
    else:
        pitched = pitched[:out_len]

    fade_len = max(1, int(sample_rate * 0.01))
    if len(pitched) > fade_len * 2:
        pitched[:fade_len] *= np.linspace(0, 1, fade_len, endpoint=False, dtype=np.float32)
        pitched[-fade_len:] *= np.linspace(1, 0, fade_len, endpoint=True, dtype=np.float32)

    return pitched


def make_path_wav_from_web_samples(
    path_notes: list[dict],
    sample_source: str,
    seconds_per_note: float = 0.45,
    sample_rate: int = 44100,
) -> tuple[io.BytesIO | None, str | None]:
    """Generate WAV by using public instrument samples fetched from the web."""
    source = WEB_SAMPLE_SOURCES.get(sample_source)
    if not source:
        return None, "Unknown web sample source"

    try:
        base_sample, src_rate = _fetch_web_sample(source["url"])
        base_sample = _resample_linear(base_sample, src_rate, sample_rate)
    except Exception as exc:
        return None, f"Web sample load failed: {exc}"

    audio = np.array([], dtype=np.float32)
    base_midi = int(source["base_midi"])

    for item in path_notes:
        midi_num = int(item["pitch"])
        tone = _sample_note(base_sample, base_midi, midi_num, seconds_per_note, sample_rate)
        audio = np.concatenate([audio, tone * 0.72])

    if len(audio) == 0:
        return None, "No notes generated"

    peak = float(np.max(np.abs(audio)))
    if peak > 0.98:
        audio = audio / peak * 0.98

    audio_int16 = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())
    wav_buffer.seek(0)
    return wav_buffer, None


# ----------------------------
# Audio
# ----------------------------

def make_path_wav(
    path_notes: list[dict],
    seconds_per_note: float = 0.45,
    sample_rate: int = 44100,
    preset_name: str = "Clean Guitar",
) -> io.BytesIO:
    """
    Generate a simple sine-wave WAV from the actual displayed scale path.
    """
    audio = np.array([], dtype=np.float32)

    for item in path_notes:
        midi_num = item["pitch"]
        freq = note_frequency_from_midi(midi_num)
        tone = _synth_note(freq, seconds_per_note, sample_rate, preset_name)
        audio = np.concatenate([audio, tone * 0.55])

    audio_int16 = np.int16(audio * 32767)

    wav_buffer = io.BytesIO()

    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())

    wav_buffer.seek(0)
    return wav_buffer


# ----------------------------
# Scale-path logic
# ----------------------------

def find_root_on_low_e(root: str, max_fret: int, tuning: list[tuple[str, int]] = STANDARD_TUNING) -> int | None:
    """
    Find the first occurrence of the root on the LOW E string
    within the visible fret range.
    """
    low_e_string_index = len(tuning) - 1
    open_note, _ = tuning[low_e_string_index]

    for fret in range(max_fret + 1):
        if note_at_string_fret(open_note, fret) == root:
            return fret

    return None


def build_single_scale_path(
    root: str,
    scale_kind: str,
    mode_name: str,
    max_fret: int,
    position_span: int = 4,
    tuning: list[tuple[str, int]] = STANDARD_TUNING,
) -> list[dict]:
    """
    Build ONE ascending scale path starting on the root note
    found on the LOW E string, then continue across all six strings.

    It does not place every possible scale note on the neck.
    It places only one playable ascending path through the selected scale.
    """
    scale_notes = build_scale(root, scale_kind, mode_name)
    root_fret = find_root_on_low_e(root, max_fret, tuning=tuning)

    if root_fret is None:
        return []

    # Start on low E string
    start_string = len(tuning) - 1
    start_pitch = midi_for_string_fret(start_string, root_fret, tuning=tuning)

    # Keep the fingering in a local box around the starting root.
    # Example: root_fret 8 and position_span 4 gives frets 7 through 12.
    fret_min = max(0, root_fret - 1)
    fret_max = min(max_fret, root_fret + position_span)

    path = [{
        "string_index": start_string,
        "fret": root_fret,
        "note": root,
        "pitch": start_pitch,
        "step": 1
    }]

    current_pitch = start_pitch
    current_string = start_string
    current_fret = root_fret
    step_num = 2

    while True:
        best = None

        # Search from current string upward toward the high E string.
        for string_index in range(current_string, -1, -1):
            for fret in range(fret_min, fret_max + 1):
                note_here = note_at_string_fret(tuning[string_index][0], fret)

                if note_here not in scale_notes:
                    continue

                pitch_here = midi_for_string_fret(string_index, fret, tuning=tuning)

                if pitch_here <= current_pitch:
                    continue

                # Prefer:
                # - nearest next pitch
                # - natural string movement
                # - modest fret movement
                score = (
                    (pitch_here - current_pitch) * 10
                    + abs(string_index - current_string) * 6
                    + abs(fret - current_fret) * 3
                )

                if best is None or score < best["score"]:
                    best = {
                        "score": score,
                        "string_index": string_index,
                        "fret": fret,
                        "note": note_here,
                        "pitch": pitch_here,
                        "step": step_num
                    }

        if best is None:
            break

        path.append(best)

        current_pitch = best["pitch"]
        current_string = best["string_index"]
        current_fret = best["fret"]
        step_num += 1

        # Stop only after reaching the high E string and exhausting
        # further ascending scale notes within the selected position.
        if current_string == 0:
            more_on_high_e = False

            for fret in range(current_fret + 1, fret_max + 1):
                note_here = note_at_string_fret(tuning[0][0], fret)
                pitch_here = midi_for_string_fret(0, fret, tuning=tuning)

                if note_here in scale_notes and pitch_here > current_pitch:
                    more_on_high_e = True
                    break

            if not more_on_high_e:
                break

    return path


# ----------------------------
# SVG fretboard renderer
# ----------------------------

def render_fretboard_svg(
    root: str,
    mode_name: str,
    path_notes: list[dict],
    max_fret: int = 12,
    tuning: list[tuple[str, int]] = STANDARD_TUNING,
) -> str:
    """
    Render the fretboard and show ONLY the single selected scale path.
    No extra scale notes are displayed anywhere else.
    """

    width = 1180
    height = 460

    left_margin = 85
    right_margin = 30
    top_margin = 78
    bottom_margin = 70

    board_width = width - left_margin - right_margin
    board_height = height - top_margin - bottom_margin

    string_count = len(tuning)
    string_gap = board_height / (string_count - 1)
    fret_gap = board_width / max_fret

    svg_parts = []

    svg_parts.append(f"""
    <svg width="100%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
        <style>
            .bg {{
                fill: #fbfbfb;
            }}

            .title {{
                font-family: Arial, sans-serif;
                font-size: 18px;
                font-weight: bold;
                fill: #111;
            }}

            .subtitle {{
                font-family: Arial, sans-serif;
                font-size: 13px;
                fill: #444;
            }}

            .string {{
                stroke: #333;
                stroke-width: 2;
            }}

            .string.thin {{
                stroke-width: 1.8;
            }}

            .string.medium {{
                stroke-width: 2.4;
            }}

            .string.thick {{
                stroke-width: 3.2;
            }}

            .fret {{
                stroke: #777;
                stroke-width: 2;
            }}

            .nut {{
                stroke: #111;
                stroke-width: 8;
            }}

            .string-label {{
                font-family: Arial, sans-serif;
                font-size: 16px;
                font-weight: bold;
                text-anchor: middle;
                dominant-baseline: middle;
                fill: #111;
            }}

            .fret-label {{
                font-family: Arial, sans-serif;
                font-size: 12px;
                text-anchor: middle;
                fill: #444;
            }}

            .note-circle {{
                stroke: #1d4f73;
                stroke-width: 2;
                fill: #dff1ff;
            }}

            .start-circle {{
                stroke: #12374f;
                stroke-width: 2.8;
                fill: #bfe3ff;
            }}

            .active-note {{
                fill: #ffe066 !important;
                stroke: #b58900 !important;
                stroke-width: 3 !important;
            }}

            .note-text {{
                font-family: Arial, sans-serif;
                font-size: 16px;
                font-weight: bold;
                text-anchor: middle;
                dominant-baseline: middle;
                fill: #111;
            }}

            .step-text {{
                font-family: Arial, sans-serif;
                font-size: 10px;
                text-anchor: middle;
                fill: #444;
            }}

            .path-line {{
                stroke: #1d4f73;
                stroke-width: 3;
                opacity: 0.28;
                fill: none;
            }}
        </style>

        <rect class="bg" x="0" y="0" width="{width}" height="{height}" rx="12" />

        <text class="title" x="{left_margin}" y="34">
            {html.escape(root)} {html.escape(mode_name)} scale path
        </text>
        <text class="subtitle" x="{left_margin}" y="55">
            Starts on the low E string root and continues across all six strings.
        </text>
    """)

    # Frets
    for fret in range(max_fret + 1):
        x = left_margin + fret * fret_gap
        css_class = "nut" if fret == 0 else "fret"

        svg_parts.append(
            f'<line class="{css_class}" '
            f'x1="{x}" y1="{top_margin}" '
            f'x2="{x}" y2="{top_margin + board_height}" />'
        )

    # Strings
    for string_index, (open_note, octave) in enumerate(tuning):
        y = top_margin + string_index * string_gap

        if string_index <= 1:
            string_class = "string thin"
        elif string_index <= 3:
            string_class = "string medium"
        else:
            string_class = "string thick"

        svg_parts.append(
            f'<line class="{string_class}" '
            f'x1="{left_margin}" y1="{y}" '
            f'x2="{left_margin + board_width}" y2="{y}" />'
        )

        svg_parts.append(
            f'<text class="string-label" x="{left_margin - 38}" y="{y}">'
            f'{html.escape(open_note)}</text>'
        )

    # Fret labels
    for fret in range(max_fret + 1):
        if fret == 0:
            label = "open"
            x = left_margin
        else:
            label = str(fret)
            x = left_margin + (fret - 0.5) * fret_gap

        svg_parts.append(
            f'<text class="fret-label" x="{x}" y="{height - 24}">{label}</text>'
        )

    # Build coordinates for path notes
    coords = []
    for item in path_notes:
        string_index = item["string_index"]
        fret = item["fret"]

        y = top_margin + string_index * string_gap

        if fret == 0:
            x = left_margin
        else:
            x = left_margin + (fret - 0.5) * fret_gap

        coords.append((x, y))

    # Draw a subtle line through the scale path
    if len(coords) >= 2:
        points = " ".join(f"{x},{y}" for x, y in coords)
        svg_parts.append(f'<polyline class="path-line" points="{points}" />')

    # Draw only the selected path notes
    for note_idx, item in enumerate(path_notes):
        string_index = item["string_index"]
        fret = item["fret"]
        note = item["note"]
        step = item["step"]

        y = top_margin + string_index * string_gap

        if fret == 0:
            x = left_margin
        else:
            x = left_margin + (fret - 0.5) * fret_gap

        circle_class = "start-circle" if step == 1 else "note-circle"

        svg_parts.append(
            f'<circle id="note-node-{note_idx}" class="{circle_class}" cx="{x}" cy="{y}" r="18" />'
        )

        svg_parts.append(
            f'<text class="note-text" x="{x}" y="{y}">{html.escape(note)}</text>'
        )

        svg_parts.append(
            f'<text class="step-text" x="{x}" y="{y + 31}">{step}</text>'
        )

    svg_parts.append("</svg>")

    return "\n".join(svg_parts)


def render_piano_keyboard_svg(path_notes: list[dict]) -> str:
    """Render a piano keyboard view with per-step markers for synchronized highlighting."""
    if not path_notes:
        return "<div>No notes</div>"

    width = 1180
    height = 360
    left = 40
    right = 30
    top = 60
    keyboard_h = 210
    keyboard_w = width - left - right

    min_midi = min(int(p["pitch"]) for p in path_notes)
    max_midi = max(int(p["pitch"]) for p in path_notes)

    start_midi = max(21, (min_midi // 12) * 12)
    end_midi = min(108, ((max_midi // 12) + 1) * 12 + 11)

    def _is_black(midi_num: int) -> bool:
        return note_name_from_midi(midi_num).endswith('#')

    white_midis = [m for m in range(start_midi, end_midi + 1) if not _is_black(m)]
    white_count = max(1, len(white_midis))
    white_w = keyboard_w / white_count
    black_w = white_w * 0.62
    black_h = keyboard_h * 0.62

    white_x = {}
    for i, m in enumerate(white_midis):
        white_x[m] = left + i * white_w

    key_center = {}
    for m in range(start_midi, end_midi + 1):
        if not _is_black(m):
            key_center[m] = white_x[m] + white_w / 2
        else:
            prev_white = m - 1
            while prev_white >= start_midi and _is_black(prev_white):
                prev_white -= 1
            if prev_white in white_x:
                key_center[m] = white_x[prev_white] + white_w * 0.74
            else:
                key_center[m] = left

        parts = [f"""
    <svg width="100%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
      <style>
        .title {{ font-family: Arial, sans-serif; font-size: 20px; font-weight: bold; fill: #111; }}
        .subtitle {{ font-family: Arial, sans-serif; font-size: 13px; fill: #475569; }}
        .white-key {{ fill: #ffffff; stroke: #2f2f2f; stroke-width: 1.2; }}
        .black-key {{ fill: #1f2937; stroke: #111827; stroke-width: 1; }}
        .marker {{ fill: #93c5fd; stroke: #1d4f73; stroke-width: 2; }}
                .marker-white {{ fill: #93c5fd; stroke: #1d4f73; stroke-width: 2; }}
                .marker-black {{ fill: #f8fafc; stroke: #1d4f73; stroke-width: 2; }}
                .marker-step {{ font-family: Arial, sans-serif; font-size: 10px; text-anchor: middle; fill: #111; font-weight: bold; }}
                .marker-step-on-black {{ fill: #111; }}
                .marker-note {{ font-family: Arial, sans-serif; font-size: 9px; text-anchor: middle; fill: #334155; }}
                .black-key-label {{ font-family: Arial, sans-serif; font-size: 10px; text-anchor: middle; fill: #334155; }}
        .active-note {{ fill: #ffe066 !important; stroke: #b58900 !important; stroke-width: 3 !important; }}
      </style>
      <text class="title" x="{left}" y="30">Piano Keyboard View</text>
            <text class="subtitle" x="{left}" y="48">Notes are mapped onto real key positions (including sharp/flat enharmonics).</text>
    """]

    for m in white_midis:
        x = white_x[m]
        parts.append(f'<rect class="white-key" x="{x}" y="{top}" width="{white_w}" height="{keyboard_h}" />')

    for m in range(start_midi, end_midi + 1):
        if not _is_black(m):
            continue
        cx = key_center[m]
        parts.append(f'<rect class="black-key" x="{cx - black_w/2}" y="{top}" width="{black_w}" height="{black_h}" />')
        parts.append(
            f'<text class="black-key-label" x="{cx}" y="{top - 8}">{html.escape(note_display_name(note_name_from_midi(m)))}</text>'
        )

    for idx, item in enumerate(path_notes):
        midi_num = int(item["pitch"])
        cx = key_center.get(midi_num, left)
        note = str(item.get("note", ""))
        step = int(item.get("step", idx + 1))
        is_black_note = _is_black(midi_num)
        marker_y = top + (black_h * 0.58 if is_black_note else keyboard_h * 0.74)
        marker_r = 12 if is_black_note else 14
        marker_class = "marker-black" if is_black_note else "marker-white"
        step_class = "marker-step marker-step-on-black" if is_black_note else "marker-step"

        parts.append(f'<circle id="note-node-{idx}" class="{marker_class}" cx="{cx}" cy="{marker_y}" r="{marker_r}" />')
        parts.append(f'<text class="{step_class}" x="{cx}" y="{marker_y + 3}">{step}</text>')
        parts.append(
            f'<text class="marker-note" x="{cx}" y="{marker_y + marker_r + 11}">{html.escape(note_display_name(note))}</text>'
        )

    parts.append('</svg>')
    return "\n".join(parts)


def render_mallet_bars_svg(path_notes: list[dict]) -> str:
    """Render an instrument-style mallet bar view for the same path notes."""
    if not path_notes:
        return "<div>No notes</div>"

    width = 1180
    height = 340
    left = 50
    top = 70
    bar_h = 54
    gap = 10
    bar_w = (width - (left * 2) - (len(path_notes) - 1) * gap) / max(1, len(path_notes))

    parts = [f"""
    <svg width="100%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
      <style>
        .title {{ font-family: Arial, sans-serif; font-size: 20px; font-weight: bold; fill: #111; }}
        .subtitle {{ font-family: Arial, sans-serif; font-size: 13px; fill: #475569; }}
        .bar {{ fill: #93c5fd; stroke: #1d4f73; stroke-width: 2; rx: 8; }}
        .bar-step {{ font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; text-anchor: middle; fill: #0f172a; }}
        .bar-note {{ font-family: Arial, sans-serif; font-size: 12px; text-anchor: middle; fill: #334155; }}
        .active-note {{ fill: #ffe066 !important; stroke: #b58900 !important; stroke-width: 3 !important; }}
      </style>
      <text class="title" x="{left}" y="30">Mallet Bars View</text>
      <text class="subtitle" x="{left}" y="48">Pluggable alternative instrument-style visualization.</text>
    """]

    for idx, item in enumerate(path_notes):
        x = left + idx * (bar_w + gap)
        y = top + ((idx % 2) * 10)
        note = str(item.get("note", ""))
        step = int(item.get("step", idx + 1))
        parts.append(f'<rect id="note-node-{idx}" class="bar" x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" rx="8" />')
        parts.append(f'<text class="bar-step" x="{x + bar_w/2}" y="{y + 24}">{step}</text>')
        parts.append(f'<text class="bar-note" x="{x + bar_w/2}" y="{y + 42}">{html.escape(note)}</text>')

    parts.append('</svg>')
    return "\n".join(parts)


VIEW_RENDERERS = {
    "Guitar Neck": render_fretboard_svg,
    "Bass Guitar Neck": lambda root, mode_name, path_notes, max_fret: render_fretboard_svg(
        root,
        mode_name,
        path_notes,
        max_fret=max_fret,
        tuning=BASS_TUNING,
    ),
    "Piano Keyboard": lambda root, mode_name, path_notes, max_fret: render_piano_keyboard_svg(path_notes),
    "Mallet Bars": lambda root, mode_name, path_notes, max_fret: render_mallet_bars_svg(path_notes),
}


def render_synced_player_html(
    root: str,
    mode_name: str,
    path_notes: list[dict],
    max_fret: int,
    seconds_per_note: float,
    audio_engine: str,
    web_sample_source: str,
    sound_preset: str,
    view_mode: str,
) -> str:
    """Render selected instrument view with an in-browser synced player."""
    renderer = VIEW_RENDERERS.get(view_mode, render_fretboard_svg)
    svg_markup = renderer(root, mode_name, path_notes, max_fret)

    note_events = []
    for idx, item in enumerate(path_notes):
        note_events.append({
            "idx": idx,
            "midi": int(item["pitch"]),
            "label": str(item["note"]),
            "string": int(item["string_index"]),
            "fret": int(item["fret"]),
        })

    source_meta = WEB_SAMPLE_SOURCES.get(web_sample_source, {})
    sample_url = str(source_meta.get("url", ""))
    sample_base_midi = int(source_meta.get("base_midi", 60))
    synth_preset = str(sound_preset or "Clean Guitar")

    note_events_json = json.dumps(note_events)
    sample_url_json = json.dumps(sample_url)
    audio_engine_json = json.dumps(audio_engine)
    synth_preset_json = json.dumps(synth_preset)

    return f"""
<div style="border:1px solid #e5e7eb;border-radius:12px;padding:10px;background:#ffffff;">
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:6px 6px 10px 6px;">
        <button id="play-sync-scale" style="background:#14532d;color:white;border:none;border-radius:8px;padding:10px 14px;font-weight:600;cursor:pointer;">▶ Play Scale</button>
        <button id="stop-sync-scale" style="background:#334155;color:white;border:none;border-radius:8px;padding:10px 14px;font-weight:600;cursor:pointer;">⏹ Stop</button>
        <span id="sync-status" style="font-family:Arial,sans-serif;color:#475569;font-size:13px;">Ready</span>
    </div>
    <div>{svg_markup}</div>
</div>
<script>
(() => {{
    const noteEvents = {note_events_json};
    const secondsPerNote = {float(seconds_per_note)};
    const audioEngine = {audio_engine_json};
    const sampleUrl = {sample_url_json};
    const sampleBaseMidi = {sample_base_midi};
    const synthPreset = {synth_preset_json};
    const noteTailFactor = 1.35;

    const playBtn = document.getElementById('play-sync-scale');
    const stopBtn = document.getElementById('stop-sync-scale');
    const statusEl = document.getElementById('sync-status');

    let audioCtx = null;
    let sampleBuffer = null;
    let stopRequested = false;
    let activeSource = null;

    function setStatus(msg) {{
        if (statusEl) statusEl.textContent = msg;
    }}

    async function ensureAudioContext() {{
        if (!audioCtx) {{
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }}
        if (audioCtx.state === 'suspended') {{
            await audioCtx.resume();
        }}
    }}

    async function ensureSampleBuffer() {{
        if (audioEngine !== 'Public Web Samples') return;
        if (sampleBuffer || !sampleUrl) return;
        const resp = await fetch(sampleUrl, {{ cache: 'force-cache' }});
        if (!resp.ok) throw new Error('Sample fetch failed: ' + resp.status);
        const arr = await resp.arrayBuffer();
        sampleBuffer = await audioCtx.decodeAudioData(arr.slice(0));
    }}

    function clearHighlights() {{
        noteEvents.forEach((ev) => {{
            const el = document.getElementById(`note-node-${{ev.idx}}`);
            if (el) el.classList.remove('active-note');
        }});
    }}

    function sleep(ms) {{
        return new Promise((resolve) => setTimeout(resolve, ms));
    }}

    async function playWebSample(midi, durationSec) {{
        const audibleSec = Math.max(0.06, durationSec * noteTailFactor);
        const gain = audioCtx.createGain();
        gain.gain.setValueAtTime(0.0, audioCtx.currentTime);
        gain.gain.linearRampToValueAtTime(0.95, audioCtx.currentTime + 0.01);
        gain.gain.setTargetAtTime(0.95, audioCtx.currentTime + 0.02, 0.08);
        gain.gain.setTargetAtTime(0.001, audioCtx.currentTime + Math.max(0.05, durationSec * 0.95), 0.22);
        gain.connect(audioCtx.destination);

        const src = audioCtx.createBufferSource();
        src.buffer = sampleBuffer;
        src.playbackRate.value = Math.pow(2, (midi - sampleBaseMidi) / 12);
        src.connect(gain);
        activeSource = src;
        src.start();
        src.stop(audioCtx.currentTime + audibleSec);
        await sleep(durationSec * 1000);
    }}

    async function playSynth(midi, durationSec) {{
        const audibleSec = Math.max(0.06, durationSec * noteTailFactor);
        const freq = 440 * Math.pow(2, (midi - 69) / 12);
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        const waveByPreset = {{
            'Studio Sine': 'sine',
            'Clean Guitar': 'triangle',
            'Warm Lead': 'sawtooth',
            'Glass Bell': 'sine',
        }};
        osc.type = waveByPreset[synthPreset] || 'triangle';
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.0, audioCtx.currentTime);
        gain.gain.linearRampToValueAtTime(0.82, audioCtx.currentTime + 0.012);
        gain.gain.setTargetAtTime(0.82, audioCtx.currentTime + 0.02, 0.07);
        gain.gain.setTargetAtTime(0.001, audioCtx.currentTime + Math.max(0.05, durationSec * 0.95), 0.25);
        osc.connect(gain).connect(audioCtx.destination);
        activeSource = osc;
        osc.start();
        osc.stop(audioCtx.currentTime + audibleSec);
        await sleep(durationSec * 1000);
    }}

    async function playSequence() {{
        if (!noteEvents.length) return;
        stopRequested = false;
        clearHighlights();

        try {{
            await ensureAudioContext();
            await ensureSampleBuffer();
        }} catch (err) {{
            setStatus('Audio init failed');
            return;
        }}

        playBtn.disabled = true;
        setStatus('Playing...');

        for (const ev of noteEvents) {{
            if (stopRequested) break;
            clearHighlights();
            const el = document.getElementById(`note-node-${{ev.idx}}`);
            if (el) el.classList.add('active-note');

            try {{
                if (audioEngine === 'Public Web Samples' && sampleBuffer) {{
                    await playWebSample(ev.midi, secondsPerNote);
                }} else {{
                    await playSynth(ev.midi, secondsPerNote);
                }}
            }} catch (err) {{
                await playSynth(ev.midi, secondsPerNote);
            }}

            if (el) el.classList.remove('active-note');
        }}

        clearHighlights();
        playBtn.disabled = false;
        setStatus(stopRequested ? 'Stopped' : 'Finished');
    }}

    playBtn.addEventListener('click', () => {{
        if (!playBtn.disabled) playSequence();
    }});

    stopBtn.addEventListener('click', () => {{
        stopRequested = true;
        if (activeSource) {{
            try {{ activeSource.stop(); }} catch (_) {{}}
        }}
        clearHighlights();
        playBtn.disabled = false;
        setStatus('Stopped');
    }});
}})();
</script>
"""


# ----------------------------
# Streamlit app
# ----------------------------

st.set_page_config(
    page_title="Guitar Mode Finder",
    page_icon="🎸",
    layout="wide"
)

st.title("🎸 Guitar Mode Finder")
st.caption(
    "Shows one ascending scale path across all six strings, starting from the root on the low E string."
)

with st.sidebar:
    st.header("Selection")

    root = st.selectbox(
        "Root note",
        CHROMATIC_SHARPS,
        index=0
    )

    scale_kind = st.selectbox(
        "Scale family",
        list(SCALE_LIBRARY.keys()),
        index=0,
        help="Pick the kind of scale first, then choose a specific scale or mode.",
    )

    mode = st.selectbox(
        "Scale / mode",
        list(SCALE_LIBRARY[scale_kind].keys()),
        index=0,
    )

    max_fret = st.slider(
        "Frets to show",
        min_value=5,
        max_value=24,
        value=12,
        step=1
    )

    position_span = st.slider(
        "Position width",
        min_value=3,
        max_value=7,
        value=4,
        step=1,
        help="How many frets above the starting root to use for the scale path."
    )

    seconds_per_note = st.slider(
        "Playback speed",
        min_value=0.15,
        max_value=1.00,
        value=0.45,
        step=0.05
    )

    audio_engine = st.selectbox(
        "Audio source",
        ["Public Web Samples", "Built-in Synth"],
        index=0,
        help="Use internet-hosted free instrument samples, or fallback to local synthesis.",
    )

    web_sample_source = st.selectbox(
        "Web instrument",
        list(WEB_SAMPLE_SOURCES.keys()),
        index=0,
        disabled=audio_engine != "Public Web Samples",
    )

    sound_preset = st.selectbox(
        "Sound preset",
        list(SOUND_PRESETS.keys()),
        index=1,
        help="Used when Audio source is Built-in Synth.",
        disabled=audio_engine != "Built-in Synth",
    )

    view_mode = st.selectbox(
        "Instrument view",
        list(VIEW_RENDERERS.keys()),
        index=0,
        help="Pluggable visualizations that stay synchronized with the same scale playback.",
    )

    if audio_engine == "Public Web Samples":
        st.caption("Sources: ToneJS-Instruments samples (CC-BY 3.0), loaded from public GitHub URLs.")

scale_notes = build_scale(root, scale_kind, mode)

selected_tuning = BASS_TUNING if view_mode == "Bass Guitar Neck" else STANDARD_TUNING

path_notes = build_single_scale_path(
    root=root,
    scale_kind=scale_kind,
    mode_name=mode,
    max_fret=max_fret,
    position_span=position_span,
    tuning=selected_tuning,
)

st.subheader(f"{root} {mode}")
st.caption(f"Scale family: {scale_kind}")

col1, col2 = st.columns([1.3, 1])

with col1:
    st.markdown(
        "**Scale notes:** "
        + "  ".join(f"`{note}`" for note in scale_notes)
    )

with col2:
    common_name = ""

    if mode == "Ionian / Major":
        common_name = "Common name: Major"
    elif mode == "Aeolian / Minor":
        common_name = "Common name: Minor"

    if common_name:
        st.markdown(f"**{common_name}**")

if not path_notes:
    st.warning(
        "The selected root does not appear on the low E string within the visible fret range. "
        "Increase the fret range."
    )
else:
    start_fret = path_notes[0]["fret"]
    last_note = path_notes[-1]["note"]
    last_string = selected_tuning[path_notes[-1]["string_index"]][0]
    last_fret = path_notes[-1]["fret"]
    start_string_label = selected_tuning[path_notes[0]["string_index"]][0]

    st.markdown(
        f"**Starting position:** `{start_string_label}` string, fret `{start_fret}`  \n"
        f"**Displayed path:** `{len(path_notes)}` notes, ending on `{last_note}` "
        f"on `{last_string}` string, fret `{last_fret}`"
    )

    st.markdown(f"### {view_mode} + Synchronized Playback")

    st.components.v1.html(
        render_synced_player_html(
            root=root,
            mode_name=mode,
            path_notes=path_notes,
            max_fret=max_fret,
            seconds_per_note=seconds_per_note,
            audio_engine=audio_engine,
            web_sample_source=web_sample_source,
            sound_preset=sound_preset,
            view_mode=view_mode,
        ),
        height=580,
        scrolling=False,
    )

    with st.expander("Displayed scale path"):
        rows = []

        for item in path_notes:
            string_name = selected_tuning[item["string_index"]][0]
            octave = octave_from_midi(item["pitch"])

            rows.append({
                "Step": item["step"],
                "Note": item["note"],
                "String": string_name,
                "Fret": item["fret"],
                "Octave": octave
            })

        st.dataframe(rows, use_container_width=True, hide_index=True)

with st.expander("Prototype notes"):
    st.write(
        """
        This version shows only one ascending scale path.

        Behavior:
        - Finds the root on the low E string.
        - Builds a single ascending scale path from that starting note.
        - Continues across all six strings.
        - Displays only those selected path notes.
        - Does not show every scale note on the neck.
        - Audio playback follows the displayed path.
        """
    )
