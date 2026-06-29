import streamlit as st
import numpy as np
import wave
import io
import html
import json
import logging
import re
import struct
import http.cookiejar
import urllib.parse
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
    "Bass Electric (E1 sample)": {
        "url": "https://raw.githubusercontent.com/nbrosowsky/tonejs-instruments/master/samples/bass-electric/E1.wav",
        "base_midi": 28,
    },
    "Blocks (Xylophone C5 sample)": {
        "url": "https://raw.githubusercontent.com/nbrosowsky/tonejs-instruments/master/samples/xylophone/C5.wav",
        "base_midi": 72,
    },
    "Trumpet (C4 sample)": {
        "url": "https://raw.githubusercontent.com/nbrosowsky/tonejs-instruments/master/samples/trumpet/C4.wav",
        "base_midi": 60,
    },
    "Trombone (C3 sample)": {
        "url": "https://raw.githubusercontent.com/nbrosowsky/tonejs-instruments/master/samples/trombone/C3.wav",
        "base_midi": 48,
    },
    "French Horn (C4 sample)": {
        "url": "https://raw.githubusercontent.com/nbrosowsky/tonejs-instruments/master/samples/french-horn/C4.wav",
        "base_midi": 60,
    },
    "Saxophone (C4 sample)": {
        "url": "https://raw.githubusercontent.com/nbrosowsky/tonejs-instruments/master/samples/saxophone/C4.wav",
        "base_midi": 60,
    },
    "Organ (C4 sample)": {
        "url": "https://raw.githubusercontent.com/nbrosowsky/tonejs-instruments/master/samples/organ/C4.wav",
        "base_midi": 60,
    },
    "Standup Bass (Contrabass C2 sample)": {
        "url": "https://raw.githubusercontent.com/nbrosowsky/tonejs-instruments/master/samples/contrabass/C2.wav",
        "base_midi": 36,
    },
    "Chorus (Harmonium C4 sample)": {
        "url": "https://raw.githubusercontent.com/nbrosowsky/tonejs-instruments/master/samples/harmonium/C4.wav",
        "base_midi": 60,
    },
}

CHANNEL_COLOR_SEQUENCE = [
    ("Yellow", "#ffe066"),
    ("Red", "#ff6b6b"),
    ("Blue", "#4dabf7"),
    ("Green", "#69db7c"),
    ("Orange", "#ffa94d"),
    ("Purple", "#b197fc"),
    ("Cyan", "#66d9e8"),
    ("Pink", "#f783ac"),
]

PUBLIC_MIDI_SOURCES = {
    "Fur Elise (Beethoven)": "https://www.mfiles.co.uk/downloads/fur-elise.mid",
    "Greensleeves": "https://www.mfiles.co.uk/downloads/greensleeves.mid",
    "Nocturne Op.9 No.2 (Chopin)": "https://www.mfiles.co.uk/downloads/chopin-nocturne-op9-no2.mid",
    "Symphony No.5 - 1st Movement (Beethoven)": "https://www.mfiles.co.uk/downloads/beethoven-symphony5-1.mid",
    "Moonlight Sonata 1 (Guitar, Beethoven/Tarrega)": "https://www.mfiles.co.uk/downloads/beethoven-tarrega-moonlight-sonata1-guitar.mid",
    "Cello Suite No.1 Prelude (Bach)": "https://www.mfiles.co.uk/downloads/bach-cello-suite-no1-prelude.mid",
    "Lullaby (Brahms)": "https://www.mfiles.co.uk/downloads/brahms-lullaby-wiegenlied.mid",
    "Carol of the Bells": "https://www.mfiles.co.uk/downloads/carol-of-the-bells.mid",
    "Auld Lang Syne": "https://www.mfiles.co.uk/downloads/auld-lang-syne.mid",
    "Ode to Joy (Piano Solo)": "https://www.mfiles.co.uk/downloads/beethoven-symphony9-4-ode-to-joy-piano-solo.mid",
    "Minuet (Boccherini)": "https://www.mfiles.co.uk/downloads/Boccherini-Minuet.mid",
    "Grateful Dead - Around And Around": "https://freemidi.org/download3-22437-around-and-around-grateful-dead",
    "Grateful Dead - Big Railroad Blues": "https://freemidi.org/download3-25137-big-railroad-blues-grateful-dead",
    "Grateful Dead - Casey Jones": "https://freemidi.org/download3-3516-casey-jones-grateful-dead",
    "Grateful Dead - Casey Jones (2)": "https://freemidi.org/download3-25138-casey-jones-2-grateful-dead",
    "Grateful Dead - Cripple Creek": "https://freemidi.org/download3-22438-cripple-creek-grateful-dead",
    "Grateful Dead - Dark Star": "https://freemidi.org/download3-3517-dark-star-grateful-dead",
    "Grateful Dead - Fire On The Mountain": "https://freemidi.org/download3-3518-fire-on-the-mountain-grateful-dead",
    "Grateful Dead - Franklin's Tower": "https://freemidi.org/download3-3519-franklins-tower-grateful-dead",
    "Grateful Dead - Friend Of The Devil": "https://freemidi.org/download3-3520-friend-of-the-devil-grateful-dead",
    "Grateful Dead - Going Down The Road Feelin Bad": "https://freemidi.org/download3-25139-going-down-the-road-feelin-bad-grateful-dead",
    "Grateful Dead - Not Fade Away": "https://freemidi.org/download3-22436-not-fade-away-grateful-dead",
    "Grateful Dead - Operator": "https://freemidi.org/download3-3521-operator-grateful-dead",
    "Grateful Dead - Ramble On Rose": "https://freemidi.org/download3-3522-ramble-on-rose-grateful-dead",
    "Grateful Dead - Ripple": "https://freemidi.org/download3-3523-ripple-grateful-dead",
    "Grateful Dead - Scarlet Begonias": "https://freemidi.org/download3-3524-scarlet-begonias-grateful-dead",
    "Grateful Dead - Terapin Station": "https://freemidi.org/download3-3525-terapin-station-grateful-dead",
    "Grateful Dead - The Golden Road To Unlimited Devotion": "https://freemidi.org/download3-3526-the-golden-road-to-unlimited-devotion-grateful-dead",
    "Grateful Dead - Throwing Stones": "https://freemidi.org/download3-3527-throwing-stones-grateful-dead",
    "Grateful Dead - Truckin": "https://freemidi.org/download3-3528-truckin-grateful-dead",
    "Grateful Dead - Truckin (2)": "https://freemidi.org/download3-25140-truckin-2-grateful-dead",
    "Grateful Dead - Turn On Your Love Light": "https://freemidi.org/download3-25141-turn-on-your-love-light-grateful-dead",
    "Grateful Dead - Uncle John's Band": "https://freemidi.org/download3-3529-uncle-johns-band-grateful-dead",
    "Grateful Dead - Uncle Johns Band (2)": "https://freemidi.org/download3-25142-uncle-johns-band-2-grateful-dead",
    "Grateful Dead - West La Fadeaway": "https://freemidi.org/download3-3530-west-la-fadeaway-grateful-dead",
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


def _read_vlq(data: bytes, idx: int) -> tuple[int, int]:
    value = 0
    while idx < len(data):
        b = data[idx]
        idx += 1
        value = (value << 7) | (b & 0x7F)
        if (b & 0x80) == 0:
            break
    return value, idx


@st.cache_data(show_spinner=False, ttl=24 * 3600)
def _fetch_public_midi_bytes(url: str) -> bytes:
    headers = {"User-Agent": "WeedHounds-Scales/1.0"}

    # FreeMidi pages expose a download page (download3-...) with a cookie-backed
    # getter endpoint. Follow that flow so we receive raw MIDI bytes.
    if "freemidi.org/download3-" in url or "freemidi.net/download3-" in url:
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

        page_req = urllib.request.Request(url, headers=headers)
        with opener.open(page_req, timeout=20) as resp:
            page_html = resp.read().decode("utf-8", errors="ignore")

        getter_match = re.search(
            r'id\s*=\s*["\']?downloadmidi["\']?[^>]*href\s*=\s*["\']?([^"\'\s>]+)',
            page_html,
            flags=re.IGNORECASE,
        )
        if not getter_match:
            getter_match = re.search(r'href\s*=\s*["\']?(getter-[^"\'\s>]+)', page_html, flags=re.IGNORECASE)
        if not getter_match:
            raise ValueError("Could not find FreeMidi getter link")

        getter_url = urllib.parse.urljoin(url, getter_match.group(1))
        getter_req = urllib.request.Request(getter_url, headers={**headers, "Referer": url})
        with opener.open(getter_req, timeout=20) as resp:
            data = resp.read()

        if not data.startswith(b"MThd"):
            raise ValueError("FreeMidi getter did not return MIDI bytes")
        return data

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def parse_midi_note_on_events(midi_bytes: bytes, max_events: int | None = 500) -> list[dict]:
    """Parse note-on events from a standard MIDI file into timed events."""
    if not midi_bytes.startswith(b"MThd"):
        return []

    header_len = struct.unpack(">I", midi_bytes[4:8])[0]
    if header_len < 6:
        return []

    _, ntrks, division = struct.unpack(">HHH", midi_bytes[8:14])
    if division == 0:
        return []

    idx = 8 + header_len
    all_events = []
    tempo_us_per_quarter = 500_000

    for _ in range(ntrks):
        if idx + 8 > len(midi_bytes) or midi_bytes[idx:idx + 4] != b"MTrk":
            break
        track_len = struct.unpack(">I", midi_bytes[idx + 4:idx + 8])[0]
        track_data = midi_bytes[idx + 8:idx + 8 + track_len]
        idx += 8 + track_len

        t_idx = 0
        abs_ticks = 0
        abs_seconds = 0.0
        running_status = None

        while t_idx < len(track_data):
            delta_ticks, t_idx = _read_vlq(track_data, t_idx)
            abs_ticks += delta_ticks
            abs_seconds += (delta_ticks * tempo_us_per_quarter) / (division * 1_000_000.0)
            if t_idx >= len(track_data):
                break

            status = track_data[t_idx]
            if status < 0x80:
                if running_status is None:
                    break
                status = running_status
            else:
                t_idx += 1
                running_status = status if status < 0xF0 else running_status

            if status == 0xFF:
                if t_idx >= len(track_data):
                    break
                meta_type = track_data[t_idx]
                t_idx += 1
                meta_len, t_idx = _read_vlq(track_data, t_idx)
                meta_data = track_data[t_idx:t_idx + meta_len]
                t_idx += meta_len
                if meta_type == 0x51 and len(meta_data) == 3:
                    tempo_us_per_quarter = (meta_data[0] << 16) | (meta_data[1] << 8) | meta_data[2]
                continue

            if status in (0xF0, 0xF7):
                syx_len, t_idx = _read_vlq(track_data, t_idx)
                t_idx += syx_len
                continue

            msg_type = status & 0xF0
            if msg_type in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                if t_idx + 2 > len(track_data):
                    break
                d1 = track_data[t_idx]
                d2 = track_data[t_idx + 1]
                t_idx += 2
                if msg_type == 0x90 and d2 > 0:
                    all_events.append({
                        "time": abs_seconds,
                        "midi": int(d1),
                        "channel": int(status & 0x0F),
                    })
            elif msg_type in (0xC0, 0xD0):
                if t_idx + 1 > len(track_data):
                    break
                t_idx += 1
            else:
                break

            if max_events is not None and len(all_events) >= max_events:
                break

        if max_events is not None and len(all_events) >= max_events:
            break

    all_events.sort(key=lambda e: e["time"])
    return all_events if max_events is None else all_events[:max_events]


def _normalize_key_note_name(note: str) -> str:
    enharmonic_to_sharp = {
        "Cb": "B",
        "Db": "C#",
        "Eb": "D#",
        "Fb": "E",
        "Gb": "F#",
        "Ab": "G#",
        "Bb": "A#",
    }
    if note in CHROMATIC_SHARPS:
        return note
    return enharmonic_to_sharp.get(note, note)


def extract_midi_key_signature(midi_bytes: bytes) -> tuple[str, str] | None:
    """Extract key from MIDI meta event FF 59 (if present)."""
    if not midi_bytes.startswith(b"MThd"):
        return None

    header_len = struct.unpack(">I", midi_bytes[4:8])[0]
    if header_len < 6:
        return None

    ntrks = struct.unpack(">H", midi_bytes[10:12])[0]
    idx = 8 + header_len

    major_keys = {
        -7: "Cb", -6: "Gb", -5: "Db", -4: "Ab", -3: "Eb", -2: "Bb", -1: "F",
        0: "C", 1: "G", 2: "D", 3: "A", 4: "E", 5: "B", 6: "F#", 7: "C#",
    }
    minor_keys = {
        -7: "Ab", -6: "Eb", -5: "Bb", -4: "F", -3: "C", -2: "G", -1: "D",
        0: "A", 1: "E", 2: "B", 3: "F#", 4: "C#", 5: "G#", 6: "D#", 7: "A#",
    }

    for _ in range(ntrks):
        if idx + 8 > len(midi_bytes) or midi_bytes[idx:idx + 4] != b"MTrk":
            break
        track_len = struct.unpack(">I", midi_bytes[idx + 4:idx + 8])[0]
        track_data = midi_bytes[idx + 8:idx + 8 + track_len]
        idx += 8 + track_len

        t_idx = 0
        running_status = None
        while t_idx < len(track_data):
            _, t_idx = _read_vlq(track_data, t_idx)
            if t_idx >= len(track_data):
                break

            status = track_data[t_idx]
            if status < 0x80:
                if running_status is None:
                    break
                status = running_status
            else:
                t_idx += 1
                running_status = status if status < 0xF0 else running_status

            if status == 0xFF:
                if t_idx >= len(track_data):
                    break
                meta_type = track_data[t_idx]
                t_idx += 1
                meta_len, t_idx = _read_vlq(track_data, t_idx)
                meta_data = track_data[t_idx:t_idx + meta_len]
                t_idx += meta_len
                if meta_type == 0x59 and len(meta_data) >= 2:
                    sf = int(struct.unpack("b", bytes([meta_data[0]]))[0])
                    mi = int(meta_data[1])
                    key_name = (minor_keys if mi == 1 else major_keys).get(sf)
                    if not key_name:
                        return None
                    root = _normalize_key_note_name(key_name)
                    mode_name = "Aeolian / Minor" if mi == 1 else "Ionian / Major"
                    if root in CHROMATIC_SHARPS:
                        return root, mode_name
                continue

            if status in (0xF0, 0xF7):
                syx_len, t_idx = _read_vlq(track_data, t_idx)
                t_idx += syx_len
                continue

            msg_type = status & 0xF0
            if msg_type in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                t_idx += 2
            elif msg_type in (0xC0, 0xD0):
                t_idx += 1
            else:
                break

    return None


def infer_midi_key_from_events(midi_events: list[dict]) -> tuple[str, str] | None:
    """Estimate key by maximizing pitch-class fit to major/minor templates."""
    if not midi_events:
        return None

    counts = [0] * 12
    for ev in midi_events:
        counts[int(ev["midi"]) % 12] += 1

    major_weights = {0: 2.0, 2: 1.2, 4: 1.8, 5: 1.0, 7: 1.6, 9: 1.1, 11: 0.9}
    minor_weights = {0: 2.0, 2: 1.2, 3: 1.8, 5: 1.0, 7: 1.6, 8: 1.1, 10: 0.9}

    best_score = -1.0
    best_root = None
    best_mode = None

    for root in range(12):
        major_score = sum(counts[(root + i) % 12] * w for i, w in major_weights.items())
        minor_score = sum(counts[(root + i) % 12] * w for i, w in minor_weights.items())

        if major_score > best_score:
            best_score = major_score
            best_root = root
            best_mode = "Ionian / Major"
        if minor_score > best_score:
            best_score = minor_score
            best_root = root
            best_mode = "Aeolian / Minor"

    if best_root is None or best_mode is None:
        return None
    return CHROMATIC_SHARPS[best_root], best_mode


def detect_midi_channels(midi_events: list[dict]) -> list[int]:
    """Return sorted MIDI channel numbers present in parsed events."""
    channels = sorted({int(ev.get("channel", 0)) for ev in midi_events})
    return [ch for ch in channels if 0 <= ch <= 15]


def build_channel_color_map(channels: list[int]) -> dict[int, dict]:
    """Assign deterministic colors to channels in order of appearance."""
    mapping: dict[int, dict] = {}
    for idx, ch in enumerate(sorted(set(int(c) for c in channels if 0 <= int(c) <= 15))):
        name, hex_color = CHANNEL_COLOR_SEQUENCE[idx % len(CHANNEL_COLOR_SEQUENCE)]
        mapping[int(ch)] = {"name": name, "hex": hex_color}
    return mapping


def detect_midi_scale_hint(midi_bytes: bytes, midi_events: list[dict]) -> tuple[str, str, str] | None:
    """Return (root, mode, source) from MIDI key signature or inferred pitch profile."""
    key_meta = extract_midi_key_signature(midi_bytes)
    if key_meta:
        return key_meta[0], key_meta[1], "MIDI key signature"

    inferred = infer_midi_key_from_events(midi_events)
    if inferred:
        return inferred[0], inferred[1], "inferred from note profile"

    return None


def _fit_midi_to_fretboard_range(midi_num: int, tuning: list[tuple[str, int]], max_fret: int) -> int:
    min_pitch = min(midi_for_string_fret(s, 0, tuning=tuning) for s in range(len(tuning)))
    max_pitch = max(midi_for_string_fret(s, max_fret, tuning=tuning) for s in range(len(tuning)))
    fitted = int(midi_num)
    while fitted < min_pitch:
        fitted += 12
    while fitted > max_pitch:
        fitted -= 12
    return fitted


def build_path_from_midi_events(
    midi_events: list[dict],
    tuning: list[tuple[str, int]],
    max_fret: int,
    max_notes: int | None = 80,
) -> tuple[list[dict], list[float], list[dict]]:
    """Map timed MIDI note-on events into display path, durations, and chord-aware playback events."""
    if not midi_events:
        return [], [], []

    path = []
    durations = []
    playback_events = []
    prev_string = len(tuning) - 1
    prev_fret = 0

    trimmed_source = midi_events if max_notes is None else midi_events[:max_notes]
    trimmed = sorted(trimmed_source, key=lambda e: float(e["time"]))

    # Group near-simultaneous note-ons into chord events.
    grouped_events: list[dict] = []
    time_epsilon = 0.0001
    for ev in trimmed:
        t = float(ev["time"])
        m = int(ev["midi"])
        ch = int(ev.get("channel", 0))
        if not grouped_events or abs(t - float(grouped_events[-1]["time"])) > time_epsilon:
            grouped_events.append({"time": t, "notes": [{"midi": m, "channel": ch}]})
        else:
            if not any(int(n.get("midi", -1)) == m and int(n.get("channel", -1)) == ch for n in grouped_events[-1]["notes"]):
                grouped_events[-1]["notes"].append({"midi": m, "channel": ch})

    for i, group in enumerate(grouped_events):
        chord_raw_notes = [{"midi": int(n["midi"]), "channel": int(n.get("channel", 0))} for n in group["notes"]]
        chord_raw_midis = [int(n["midi"]) for n in chord_raw_notes]
        chord_display_midis = sorted({_fit_midi_to_fretboard_range(m, tuning, max_fret) for m in chord_raw_midis})
        if not chord_display_midis:
            continue

        # Use the top pitch of each chord as a representative point for path display.
        midi_num = int(max(chord_display_midis))
        note = note_name_from_midi(midi_num)

        candidates = []
        for string_index in range(len(tuning)):
            for fret in range(max_fret + 1):
                if midi_for_string_fret(string_index, fret, tuning=tuning) == midi_num:
                    candidates.append((string_index, fret))

        if candidates:
            string_index, fret = min(
                candidates,
                key=lambda x: abs(x[1] - prev_fret) * 3 + abs(x[0] - prev_string) * 2,
            )
        else:
            string_index, fret = prev_string, max(0, min(max_fret, prev_fret))

        prev_string, prev_fret = string_index, fret

        next_time = grouped_events[i + 1]["time"] if i + 1 < len(grouped_events) else (group["time"] + 0.42)
        duration = max(0.12, min(1.2, float(next_time - group["time"])))
        durations.append(duration)

        playback_events.append({
            "idx": i,
            # Preserve original MIDI pitches for accurate octave playback/highlighting.
            "midis": sorted({int(m) for m in chord_raw_midis}),
            "notes": chord_raw_notes,
            "duration": float(duration),
        })

        path.append({
            "string_index": int(string_index),
            "fret": int(fret),
            "note": note,
            "pitch": int(midi_num),
            "step": i + 1,
        })

    return path, durations, playback_events


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
    show_all_notes: bool = False,
    overlay_pitch_classes: list[int] | None = None,
    overlay_root_pc: int | None = None,
) -> str:
    """
    Render the fretboard.
    In MIDI mode, show all notes on the visible neck and highlight any played pitch.
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
    <svg width="65%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
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

            .all-note-circle {{
                stroke: #1d4f73;
                stroke-width: 1.5;
                fill: #e2f0ff;
            }}

            .start-circle {{
                stroke: #12374f;
                stroke-width: 2.8;
                fill: #bfe3ff;
            }}

            .active-note {{
                fill: var(--active-fill, #ffe066) !important;
                stroke: var(--active-stroke, #b58900) !important;
                stroke-width: 3 !important;
            }}

            .scale-tone {{
                fill: #c7f9cc;
                stroke: #2b9348;
            }}

            .scale-root {{
                fill: #80ed99;
                stroke: #1b7f3a;
                stroke-width: 2.4;
            }}

            .note-text {{
                font-family: Arial, sans-serif;
                font-size: 16px;
                font-weight: bold;
                text-anchor: middle;
                dominant-baseline: middle;
                fill: #111;
            }}

            .all-note-text {{
                font-family: Arial, sans-serif;
                font-size: 9px;
                text-anchor: middle;
                dominant-baseline: middle;
                fill: #0f172a;
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
            {html.escape(root)} {html.escape(mode_name)} {'MIDI note map' if show_all_notes else 'scale path'}
        </text>
        <text class="subtitle" x="{left_margin}" y="55">
            {'All visible fretboard notes are shown; played MIDI notes light up wherever they appear.' if show_all_notes else 'Starts on the low E string root and continues across all six strings.'}
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

    if show_all_notes:
        for string_index in range(len(tuning)):
            for fret in range(max_fret + 1):
                midi_num = midi_for_string_fret(string_index, fret, tuning=tuning)
                note = note_name_from_midi(midi_num)
                y = top_margin + string_index * string_gap
                x = left_margin if fret == 0 else left_margin + (fret - 0.5) * fret_gap
                css_classes = ["all-note-circle"]
                if overlay_pitch_classes and (midi_num % 12) in overlay_pitch_classes:
                    css_classes.append("scale-tone")
                if overlay_root_pc is not None and (midi_num % 12) == overlay_root_pc:
                    css_classes.append("scale-root")

                svg_parts.append(
                    f'<circle data-midi="{midi_num}" class="{" ".join(css_classes)}" cx="{x}" cy="{y}" r="11" />'
                )
                svg_parts.append(
                    f'<text class="all-note-text" x="{x}" y="{y + 0.5}">{html.escape(note_display_name(note))}</text>'
                )
    else:
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
            midi_num = int(item["pitch"])

            y = top_margin + string_index * string_gap

            if fret == 0:
                x = left_margin
            else:
                x = left_margin + (fret - 0.5) * fret_gap

            circle_class = "start-circle" if step == 1 else "note-circle"

            svg_parts.append(
                f'<circle id="note-node-{note_idx}" data-note-idx="{note_idx}" data-midi="{midi_num}" class="{circle_class}" cx="{x}" cy="{y}" r="18" />'
            )

            svg_parts.append(
                f'<text class="note-text" x="{x}" y="{y}">{html.escape(note)}</text>'
            )

            svg_parts.append(
                f'<text class="step-text" x="{x}" y="{y + 31}">{step}</text>'
            )

    svg_parts.append("</svg>")

    return "\n".join(svg_parts)


def render_piano_keyboard_svg(
    path_notes: list[dict],
    show_all_notes: bool = False,
    overlay_pitch_classes: list[int] | None = None,
    overlay_root_pc: int | None = None,
    keyboard_range_mode: str = "Full 88 Keys",
) -> str:
    """Render a piano keyboard view with either path markers or full-key MIDI highlighting."""
    if not path_notes:
        return "<div>No notes</div>"

    width = 1180
    height = 360
    left = 40
    right = 30
    top = 60
    keyboard_h = 210
    keyboard_w = width - left - right

    if keyboard_range_mode == "Auto-fit from notes":
        min_midi = min(int(p["pitch"]) for p in path_notes)
        max_midi = max(int(p["pitch"]) for p in path_notes)
        start_midi = max(21, (min_midi // 12) * 12)
        end_midi = min(108, ((max_midi // 12) + 1) * 12 + 11)
    else:
        # Full 88-key keyboard span (A0..C8).
        start_midi = 21
        end_midi = 108

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
    <svg width="65%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
      <style>
        .title {{ font-family: Arial, sans-serif; font-size: 20px; font-weight: bold; fill: #111; }}
        .subtitle {{ font-family: Arial, sans-serif; font-size: 13px; fill: #475569; }}
        .white-key {{ fill: #ffffff; stroke: #2f2f2f; stroke-width: 1.2; }}
        .black-key {{ fill: #1f2937; stroke: #111827; stroke-width: 1; }}
        .white-key.scale-tone {{ fill: #d8f3dc; stroke: #2b9348; }}
        .black-key.scale-tone {{ fill: #2d6a4f; stroke: #1b4332; }}
        .white-key.scale-root {{ fill: #95d5b2; stroke: #1b7f3a; stroke-width: 2; }}
        .black-key.scale-root {{ fill: #40916c; stroke: #1b4332; stroke-width: 2; }}
        .marker {{ fill: #93c5fd; stroke: #1d4f73; stroke-width: 2; }}
                .marker-white {{ fill: #93c5fd; stroke: #1d4f73; stroke-width: 2; }}
                .marker-black {{ fill: #f8fafc; stroke: #1d4f73; stroke-width: 2; }}
                .marker-step {{ font-family: Arial, sans-serif; font-size: 10px; text-anchor: middle; fill: #111; font-weight: bold; }}
                .marker-step-on-black {{ fill: #111; }}
                .marker-note {{ font-family: Arial, sans-serif; font-size: 9px; text-anchor: middle; fill: #334155; }}
                .black-key-label {{ font-family: Arial, sans-serif; font-size: 10px; text-anchor: middle; fill: #334155; }}
        .active-note {{ fill: var(--active-fill, #ffe066) !important; stroke: var(--active-stroke, #b58900) !important; stroke-width: 3 !important; }}
      </style>
      <text class="title" x="{left}" y="30">Piano Keyboard View</text>
            <text class="subtitle" x="{left}" y="48">{'All keys are active in MIDI mode; played notes light by pitch.' if show_all_notes else 'Notes are mapped onto real key positions (including sharp/flat enharmonics).'}</text>
    """]

    for m in white_midis:
        x = white_x[m]
        key_classes = ["white-key"]
        if overlay_pitch_classes and (m % 12) in overlay_pitch_classes:
            key_classes.append("scale-tone")
        if overlay_root_pc is not None and (m % 12) == overlay_root_pc:
            key_classes.append("scale-root")
        parts.append(f'<rect class="{" ".join(key_classes)}" data-midi="{m}" x="{x}" y="{top}" width="{white_w}" height="{keyboard_h}" />')

    for m in range(start_midi, end_midi + 1):
        if not _is_black(m):
            continue
        cx = key_center[m]
        key_classes = ["black-key"]
        if overlay_pitch_classes and (m % 12) in overlay_pitch_classes:
            key_classes.append("scale-tone")
        if overlay_root_pc is not None and (m % 12) == overlay_root_pc:
            key_classes.append("scale-root")
        parts.append(f'<rect class="{" ".join(key_classes)}" data-midi="{m}" x="{cx - black_w/2}" y="{top}" width="{black_w}" height="{black_h}" />')
        parts.append(
            f'<text class="black-key-label" x="{cx}" y="{top - 8}">{html.escape(note_display_name(note_name_from_midi(m)))}</text>'
        )

    if not show_all_notes:
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

            parts.append(f'<circle id="note-node-{idx}" data-note-idx="{idx}" data-midi="{midi_num}" class="{marker_class}" cx="{cx}" cy="{marker_y}" r="{marker_r}" />')
            parts.append(f'<text class="{step_class}" x="{cx}" y="{marker_y + 3}">{step}</text>')
            parts.append(
                f'<text class="marker-note" x="{cx}" y="{marker_y + marker_r + 11}">{html.escape(note_display_name(note))}</text>'
            )

    parts.append('</svg>')
    return "\n".join(parts)


def render_mallet_bars_svg(
    path_notes: list[dict],
    max_fret: int = 12,
    tuning: list[tuple[str, int]] = STANDARD_TUNING,
    show_all_notes: bool = False,
    overlay_pitch_classes: list[int] | None = None,
    overlay_root_pc: int | None = None,
) -> str:
    """Render a mallet-style view for path notes or full visible chromatic note map."""
    if not path_notes:
        return "<div>No notes</div>"

    width = 1180
    height = 340
    left = 50
    top = 70
    bar_h = 54
    gap = 10
    render_items = []
    if show_all_notes:
        min_pitch = min(midi_for_string_fret(s, 0, tuning=tuning) for s in range(len(tuning)))
        max_pitch = max(midi_for_string_fret(s, max_fret, tuning=tuning) for s in range(len(tuning)))
        for midi_num in range(min_pitch, max_pitch + 1):
            render_items.append({
                "pitch": int(midi_num),
                "note": note_name_from_midi(midi_num),
                "step": int(midi_num),
            })
    else:
        render_items = list(path_notes)

    bar_w = (width - (left * 2) - (len(render_items) - 1) * gap) / max(1, len(render_items))

    parts = [f"""
    <svg width="65%" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
      <style>
        .title {{ font-family: Arial, sans-serif; font-size: 20px; font-weight: bold; fill: #111; }}
        .subtitle {{ font-family: Arial, sans-serif; font-size: 13px; fill: #475569; }}
        .bar {{ fill: #93c5fd; stroke: #1d4f73; stroke-width: 2; rx: 8; }}
        .bar.scale-tone {{ fill: #c7f9cc; stroke: #2b9348; }}
        .bar.scale-root {{ fill: #80ed99; stroke: #1b7f3a; stroke-width: 2.4; }}
        .bar-step {{ font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; text-anchor: middle; fill: #0f172a; }}
        .bar-note {{ font-family: Arial, sans-serif; font-size: 12px; text-anchor: middle; fill: #334155; }}
        .active-note {{ fill: var(--active-fill, #ffe066) !important; stroke: var(--active-stroke, #b58900) !important; stroke-width: 3 !important; }}
      </style>
      <text class="title" x="{left}" y="30">Mallet Bars View</text>
            <text class="subtitle" x="{left}" y="48">{'All visible chromatic notes are shown in MIDI mode.' if show_all_notes else 'Pluggable alternative instrument-style visualization.'}</text>
    """]

    for idx, item in enumerate(render_items):
        x = left + idx * (bar_w + gap)
        y = top + ((idx % 2) * 10)
        midi_num = int(item.get("pitch", 0))
        note = str(item.get("note", ""))
        step = int(item.get("step", idx + 1))
        node_id = f' id="note-node-{idx}" data-note-idx="{idx}"' if not show_all_notes else ""
        bar_classes = ["bar"]
        if overlay_pitch_classes and (midi_num % 12) in overlay_pitch_classes:
            bar_classes.append("scale-tone")
        if overlay_root_pc is not None and (midi_num % 12) == overlay_root_pc:
            bar_classes.append("scale-root")
        parts.append(f'<rect{node_id} data-midi="{midi_num}" class="{" ".join(bar_classes)}" x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" rx="8" />')
        parts.append(f'<text class="bar-step" x="{x + bar_w/2}" y="{y + 24}">{step if not show_all_notes else html.escape(note_display_name(note))}</text>')
        parts.append(f'<text class="bar-note" x="{x + bar_w/2}" y="{y + 42}">{html.escape(note_display_name(note))}</text>')

    parts.append('</svg>')
    return "\n".join(parts)


VIEW_RENDERERS = {
    "Guitar Neck": lambda root, mode_name, path_notes, max_fret, show_all_notes=False, tuning=STANDARD_TUNING, overlay_pitch_classes=None, overlay_root_pc=None, keyboard_range_mode="Full 88 Keys": render_fretboard_svg(
        root,
        mode_name,
        path_notes,
        max_fret=max_fret,
        tuning=STANDARD_TUNING,
        show_all_notes=show_all_notes,
        overlay_pitch_classes=overlay_pitch_classes,
        overlay_root_pc=overlay_root_pc,
    ),
    "Bass Guitar Neck": lambda root, mode_name, path_notes, max_fret, show_all_notes=False, tuning=STANDARD_TUNING, overlay_pitch_classes=None, overlay_root_pc=None, keyboard_range_mode="Full 88 Keys": render_fretboard_svg(
        root,
        mode_name,
        path_notes,
        max_fret=max_fret,
        tuning=BASS_TUNING,
        show_all_notes=show_all_notes,
        overlay_pitch_classes=overlay_pitch_classes,
        overlay_root_pc=overlay_root_pc,
    ),
    "Piano Keyboard": lambda root, mode_name, path_notes, max_fret, show_all_notes=False, tuning=STANDARD_TUNING, overlay_pitch_classes=None, overlay_root_pc=None, keyboard_range_mode="Full 88 Keys": render_piano_keyboard_svg(
        path_notes,
        show_all_notes=show_all_notes,
        overlay_pitch_classes=overlay_pitch_classes,
        overlay_root_pc=overlay_root_pc,
        keyboard_range_mode=keyboard_range_mode,
    ),
    "Mallet Bars": lambda root, mode_name, path_notes, max_fret, show_all_notes=False, tuning=STANDARD_TUNING, overlay_pitch_classes=None, overlay_root_pc=None, keyboard_range_mode="Full 88 Keys": render_mallet_bars_svg(
        path_notes,
        max_fret=max_fret,
        tuning=tuning,
        show_all_notes=show_all_notes,
        overlay_pitch_classes=overlay_pitch_classes,
        overlay_root_pc=overlay_root_pc,
    ),
}


def render_synced_player_html(
    root: str,
    mode_name: str,
    path_notes: list[dict],
    max_fret: int,
    seconds_per_note: float,
    audio_engine: str,
    web_sample_sources: list[str],
    sound_preset: str,
    view_mode: str,
    note_durations: list[float] | None = None,
    play_all_nonce: int = 0,
    show_all_notes: bool = False,
    tuning: list[tuple[str, int]] = STANDARD_TUNING,
    overlay_scale_notes: list[str] | None = None,
    overlay_root_note: str | None = None,
    playback_events: list[dict] | None = None,
    keyboard_range_mode: str = "Full 88 Keys",
    channel_instrument_map: dict[int, str] | None = None,
    channel_color_map: dict[int, dict] | None = None,
) -> str:
    """Render selected instrument view with an in-browser synced player."""
    renderer = VIEW_RENDERERS.get(view_mode, render_fretboard_svg)
    overlay_pcs = [note_index(n) for n in (overlay_scale_notes or []) if n in CHROMATIC_SHARPS]
    overlay_root_pc = note_index(overlay_root_note) if overlay_root_note in CHROMATIC_SHARPS else None
    svg_markup = renderer(
        root,
        mode_name,
        path_notes,
        max_fret,
        show_all_notes=show_all_notes,
        tuning=tuning,
        overlay_pitch_classes=overlay_pcs,
        overlay_root_pc=overlay_root_pc,
        keyboard_range_mode=keyboard_range_mode,
    )

    note_events = []
    if playback_events:
        for idx, ev in enumerate(playback_events):
            midis = [int(m) for m in ev.get("midis", [])]
            notes = [
                {
                    "midi": int(n.get("midi", 0)),
                    "channel": int(n.get("channel", 0)),
                }
                for n in ev.get("notes", [])
                if isinstance(n, dict) and n.get("midi") is not None
            ]
            if not midis:
                continue
            note_events.append({
                "idx": idx,
                "midis": midis,
                "notes": notes if notes else [{"midi": int(m), "channel": 0} for m in midis],
                "midi": int(max(midis)),
                "duration": float(ev.get("duration", 0.0) or 0.0),
            })
    else:
        for idx, item in enumerate(path_notes):
            note_events.append({
                "idx": idx,
                "midis": [int(item["pitch"])],
                "notes": [{"midi": int(item["pitch"]), "channel": 0}],
                "midi": int(item["pitch"]),
                "duration": 0.0,
                "label": str(item["note"]),
                "string": int(item["string_index"]),
                "fret": int(item["fret"]),
            })

    selected_sources_meta = []
    for source_name in (web_sample_sources or []):
        source_meta = WEB_SAMPLE_SOURCES.get(source_name)
        if not source_meta:
            continue
        selected_sources_meta.append({
            "name": str(source_name),
            "url": str(source_meta.get("url", "")),
            "base_midi": int(source_meta.get("base_midi", 60)),
        })

    if not selected_sources_meta and WEB_SAMPLE_SOURCES:
        first_name = next(iter(WEB_SAMPLE_SOURCES.keys()))
        first_meta = WEB_SAMPLE_SOURCES[first_name]
        selected_sources_meta.append({
            "name": str(first_name),
            "url": str(first_meta.get("url", "")),
            "base_midi": int(first_meta.get("base_midi", 60)),
        })

    synth_preset = str(sound_preset or "Clean Guitar")

    note_events_json = json.dumps(note_events)
    sample_sources_json = json.dumps(selected_sources_meta)
    channel_instrument_map_json = json.dumps({str(int(k)): str(v) for k, v in (channel_instrument_map or {}).items()})
    channel_color_map_json = json.dumps({str(int(k)): v for k, v in (channel_color_map or {}).items()})
    audio_engine_json = json.dumps(audio_engine)
    synth_preset_json = json.dumps(synth_preset)
    note_durations_json = json.dumps([float(x) for x in (note_durations or [])])
    play_all_nonce = int(play_all_nonce or 0)

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
    const sampleSources = {sample_sources_json};
    const channelInstrumentMap = {channel_instrument_map_json};
    const channelColorMap = {channel_color_map_json};
    const synthPreset = {synth_preset_json};
    const noteDurations = {note_durations_json};
    const playAllNonce = {play_all_nonce};
    const noteTailFactor = 1.35;

    const playBtn = document.getElementById('play-sync-scale');
    const stopBtn = document.getElementById('stop-sync-scale');
    const statusEl = document.getElementById('sync-status');

    let audioCtx = null;
    const sampleBufferMap = new Map();
    let stopRequested = false;
    let activeSources = [];
    let lastPlayedMidis = [];

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
        for (const srcMeta of sampleSources) {{
            if (!srcMeta || !srcMeta.name || !srcMeta.url) continue;
            if (sampleBufferMap.has(srcMeta.name)) continue;
            const resp = await fetch(srcMeta.url, {{ cache: 'force-cache' }});
            if (!resp.ok) throw new Error('Sample fetch failed: ' + resp.status + ' for ' + srcMeta.name);
            const arr = await resp.arrayBuffer();
            const decoded = await audioCtx.decodeAudioData(arr.slice(0));
            sampleBufferMap.set(srcMeta.name, decoded);
        }}
    }}

    function getNoteElementsForEvent(ev) {{
        const midiSet = new Set();
        const ids = Array.isArray(ev.midis) && ev.midis.length ? ev.midis : [ev.midi];
        for (const midi of ids) {{
            Array.from(document.querySelectorAll(`[data-midi="${{midi}}"]`)).forEach((el) => midiSet.add(el));
        }}
        if (midiSet.size > 0) return Array.from(midiSet);
        return Array.from(document.querySelectorAll(`[data-note-idx="${{ev.idx}}"], #note-node-${{ev.idx}}`));
    }}

    function getNoteElementsForMidis(midis, fallbackIdx) {{
        const midiSet = new Set();
        const ids = Array.isArray(midis) && midis.length ? midis : [];
        for (const midi of ids) {{
            Array.from(document.querySelectorAll(`[data-midi="${{midi}}"]`)).forEach((el) => midiSet.add(el));
        }}
        if (midiSet.size > 0) return Array.from(midiSet);
        if (fallbackIdx === undefined || fallbackIdx === null) return [];
        return Array.from(document.querySelectorAll(`[data-note-idx="${{fallbackIdx}}"], #note-node-${{fallbackIdx}}`));
    }}

    function isChannelOff(channel) {{
        if (!channelInstrumentMap) return false;
        const mapped = channelInstrumentMap[String(channel)];
        return typeof mapped === 'string' && mapped.toLowerCase() === 'off';
    }}

    function getChannelColor(channel) {{
        const entry = channelColorMap && channelColorMap[String(channel)];
        if (entry && entry.hex) return String(entry.hex);
        return '#ffe066';
    }}

    function clearHighlights() {{
        document.querySelectorAll('.active-note').forEach((el) => {{
            el.classList.remove('active-note');
            el.style.removeProperty('--active-fill');
            el.style.removeProperty('--active-stroke');
        }});
    }}

    function sleep(ms) {{
        return new Promise((resolve) => setTimeout(resolve, ms));
    }}

    function getSampleSourceForChannel(channel) {{
        const desired = channelInstrumentMap && Object.prototype.hasOwnProperty.call(channelInstrumentMap, String(channel))
            ? String(channelInstrumentMap[String(channel)])
            : '';
        if (desired.toLowerCase() === 'off') {{
            return [];
        }}
        if (desired) {{
            const match = sampleSources.find((s) => s && s.name === desired);
            if (match) return [match];
        }}
        return sampleSources;
    }}

    async function playWebSamples(notePayload, durationSec) {{
        const audibleSec = Math.max(0.06, durationSec * noteTailFactor);
        const notes = Array.isArray(notePayload) && notePayload.length
            ? notePayload
            : [{{ midi: Number(notePayload), channel: 0 }}];
        const voiceCount = Math.max(1, notes.length * Math.max(1, sampleSources.length));
        const perVoiceGain = Math.min(0.8, 1.1 / voiceCount);

        for (const noteItem of notes) {{
            const midi = Number(noteItem.midi);
            const channel = Number(noteItem.channel ?? 0);
            const targetSources = getSampleSourceForChannel(channel);
            for (const srcMeta of targetSources) {{
                const buffer = sampleBufferMap.get(srcMeta.name);
                if (!buffer) continue;

                const gain = audioCtx.createGain();
                gain.gain.setValueAtTime(0.0, audioCtx.currentTime);
                gain.gain.linearRampToValueAtTime(perVoiceGain, audioCtx.currentTime + 0.01);
                gain.gain.setTargetAtTime(perVoiceGain, audioCtx.currentTime + 0.02, 0.08);
                gain.gain.setTargetAtTime(0.001, audioCtx.currentTime + Math.max(0.05, durationSec * 0.95), 0.22);
                gain.connect(audioCtx.destination);

                const src = audioCtx.createBufferSource();
                src.buffer = buffer;
                src.playbackRate.value = Math.pow(2, (Number(midi) - Number(srcMeta.base_midi || 60)) / 12);
                src.connect(gain);
                activeSources.push(src);
                src.start();
                src.stop(audioCtx.currentTime + audibleSec);
            }}
        }}

        await sleep(durationSec * 1000);
    }}

    async function playSynth(midis, durationSec) {{
        const audibleSec = Math.max(0.06, durationSec * noteTailFactor);
        const notes = Array.isArray(midis) && midis.length ? midis : [{{ midi: Number(midis), channel: 0 }}];
        const perVoiceGain = Math.min(0.82, 1.0 / Math.max(1, notes.length));
        const waveByPreset = {{
            'Studio Sine': 'sine',
            'Clean Guitar': 'triangle',
            'Warm Lead': 'sawtooth',
            'Glass Bell': 'sine',
        }};
        for (const noteItem of notes) {{
            const midi = Number(noteItem.midi);
            const freq = 440 * Math.pow(2, (midi - 69) / 12);
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = waveByPreset[synthPreset] || 'triangle';
            osc.frequency.value = freq;
            gain.gain.setValueAtTime(0.0, audioCtx.currentTime);
            gain.gain.linearRampToValueAtTime(perVoiceGain, audioCtx.currentTime + 0.012);
            gain.gain.setTargetAtTime(perVoiceGain, audioCtx.currentTime + 0.02, 0.07);
            gain.gain.setTargetAtTime(0.001, audioCtx.currentTime + Math.max(0.05, durationSec * 0.95), 0.25);
            osc.connect(gain).connect(audioCtx.destination);
            activeSources.push(osc);
            osc.start();
            osc.stop(audioCtx.currentTime + audibleSec);
        }}
        await sleep(durationSec * 1000);
    }}

    function applyChannelHighlights(activeNotes, fallbackIdx) {{
        const seen = new Set();
        for (const noteItem of activeNotes) {{
            const midiNum = Number(noteItem.midi);
            const channel = Number(noteItem.channel ?? 0);
            const color = getChannelColor(channel);
            const els = getNoteElementsForMidis([midiNum], fallbackIdx);
            for (const el of els) {{
                if (seen.has(el)) continue;
                seen.add(el);
                el.style.setProperty('--active-fill', color);
                el.style.setProperty('--active-stroke', '#1f2937');
                el.classList.add('active-note');
            }}
        }}
    }}

    async function playSequence() {{
        if (!noteEvents.length) return;
        stopRequested = false;
        clearHighlights();
        lastPlayedMidis = [];

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
            activeSources = [];
            clearHighlights();
            const noteDuration = Number(ev.duration || noteDurations[ev.idx] || secondsPerNote);
            const chordMidis = Array.isArray(ev.midis) && ev.midis.length ? ev.midis : [ev.midi];
            const notePayload = Array.isArray(ev.notes) && ev.notes.length
                ? ev.notes.map((n) => ({{ midi: Number(n.midi), channel: Number(n.channel ?? 0) }}))
                : chordMidis.map((m) => ({{ midi: Number(m), channel: 0 }}));

            const activeNotes = notePayload.filter((n) => !isChannelOff(Number(n.channel ?? 0)));
            const activeMidis = Array.from(new Set(activeNotes.map((n) => Number(n.midi))));
            if (!activeNotes.length) {{
                await sleep(noteDuration * 1000);
                lastPlayedMidis = [];
                continue;
            }}

            const hasReplayPitch = activeMidis.some((m) => lastPlayedMidis.includes(m));
            if (hasReplayPitch) {{
                // Force a visible blink when a pitch is replayed in consecutive events.
                await sleep(28);
            }}

            applyChannelHighlights(activeNotes, ev.idx);

            try {{
                if (audioEngine === 'Public Web Samples' && sampleBufferMap.size) {{
                    await playWebSamples(activeNotes, noteDuration);
                }} else {{
                    await playSynth(activeNotes, noteDuration);
                }}
            }} catch (err) {{
                await playSynth(activeNotes, noteDuration);
            }}

            clearHighlights();
            lastPlayedMidis = activeMidis;
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
        activeSources.forEach((src) => {{
            try {{ src.stop(); }} catch (_) {{}}
        }});
        activeSources = [];
        clearHighlights();
        playBtn.disabled = false;
        setStatus('Stopped');
    }});

    // One-shot auto-trigger used by the page-level "Play All" button.
    if (playAllNonce > 0) {{
        setTimeout(() => {{
            if (!playBtn.disabled) playSequence();
        }}, 120);
    }}
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

# Apply any queued widget updates before keyed widgets are instantiated.
pending_widget_updates = st.session_state.pop("midi_pending_widget_updates", None)
if isinstance(pending_widget_updates, dict):
    for k, v in pending_widget_updates.items():
        st.session_state[k] = v

# Pre-widget defaults for keyed controls.
if "root_note" not in st.session_state:
    st.session_state["root_note"] = CHROMATIC_SHARPS[0]
if "scale_kind" not in st.session_state:
    st.session_state["scale_kind"] = list(SCALE_LIBRARY.keys())[0]
if "mode_name" not in st.session_state:
    st.session_state["mode_name"] = list(SCALE_LIBRARY[st.session_state["scale_kind"]].keys())[0]
if "playback_source" not in st.session_state:
    st.session_state["playback_source"] = "Scale path"
if "midi_source_name" not in st.session_state:
    st.session_state["midi_source_name"] = list(PUBLIC_MIDI_SOURCES.keys())[0]
if "midi_max_notes" not in st.session_state:
    st.session_state["midi_max_notes"] = 90
if "midi_unlimited_notes" not in st.session_state:
    st.session_state["midi_unlimited_notes"] = False
if "max_fret_value" not in st.session_state:
    st.session_state["max_fret_value"] = 12
if "view_modes" not in st.session_state:
    st.session_state["view_modes"] = ["Guitar Neck"]
if "keyboard_range_mode" not in st.session_state:
    st.session_state["keyboard_range_mode"] = "Full 88 Keys"

with st.sidebar:
    st.header("Selection")

    root = st.selectbox(
        "Root note",
        CHROMATIC_SHARPS,
        index=0,
        key="root_note",
    )

    scale_kind = st.selectbox(
        "Scale family",
        list(SCALE_LIBRARY.keys()),
        index=0,
        key="scale_kind",
        help="Pick the kind of scale first, then choose a specific scale or mode.",
    )

    mode = st.selectbox(
        "Scale / mode",
        list(SCALE_LIBRARY[scale_kind].keys()),
        index=0,
        key="mode_name",
    )

    playback_source = st.selectbox(
        "Playback source",
        ["Scale path", "Public MIDI"],
        index=0,
        key="playback_source",
        help="Choose generated scale playback, or play a public MIDI note sequence through the same views.",
    )

    midi_source_name = st.selectbox(
        "Public MIDI",
        list(PUBLIC_MIDI_SOURCES.keys()),
        index=0,
        key="midi_source_name",
        disabled=playback_source != "Public MIDI",
    )

    midi_max_notes = st.slider(
        "MIDI note limit",
        min_value=16,
        max_value=220,
        value=90,
        key="midi_max_notes",
        step=2,
        disabled=playback_source != "Public MIDI" or bool(st.session_state.get("midi_unlimited_notes", False)),
        help="Limits rendered/played note-on events to keep visualization responsive.",
    )

    midi_unlimited_notes = st.checkbox(
        "Unlimited MIDI notes",
        key="midi_unlimited_notes",
        disabled=playback_source != "Public MIDI",
        help="Parses all note-on events from the MIDI file. This can be slower on long songs.",
    )

    midi_speed = st.slider(
        "MIDI speed",
        min_value=0.25,
        max_value=2.00,
        value=1.00,
        step=0.05,
        disabled=playback_source != "Public MIDI",
        help="MIDI tempo multiplier. 1.00 = original, 2.00 = twice as fast, 0.50 = half speed.",
    )

    max_fret = st.slider(
        "Frets/Keys",
        min_value=5,
        max_value=24,
        value=12,
        key="max_fret_value",
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

    web_sample_sources = st.multiselect(
        "Web instruments",
        list(WEB_SAMPLE_SOURCES.keys()),
        default=[
            "Guitar Acoustic (A2 sample)",
            "Piano (C4 sample)",
            "Bass Electric (E1 sample)",
            "Blocks (Xylophone C5 sample)",
        ],
        disabled=audio_engine != "Public Web Samples",
        help="Select one or more web instruments to layer together. Selected instruments play simultaneously for each note.",
    )

    sound_preset = st.selectbox(
        "Sound preset",
        list(SOUND_PRESETS.keys()),
        index=1,
        help="Used when Audio source is Built-in Synth.",
        disabled=audio_engine != "Built-in Synth",
    )

    view_modes = st.multiselect(
        "Instrument views",
        list(VIEW_RENDERERS.keys()),
        default=["Guitar Neck"],
        key="view_modes",
        help="Choose one or more visualizations. Each selected view renders below with synchronized playback.",
    )

    keyboard_range_mode = st.selectbox(
        "Keyboard range",
        ["Full 88 Keys", "Auto-fit from notes"],
        index=0,
        key="keyboard_range_mode",
        help="Applies to Piano Keyboard view. Auto-fit zooms to the active note span.",
    )

    if audio_engine == "Public Web Samples":
        st.caption("Sources: ToneJS-Instruments samples (CC-BY 3.0), loaded from public GitHub URLs.")

scale_notes = build_scale(root, scale_kind, mode)

has_bass_view = "Bass Guitar Neck" in (view_modes or [])
selected_tuning = BASS_TUNING if has_bass_view else STANDARD_TUNING

path_notes = build_single_scale_path(
    root=root,
    scale_kind=scale_kind,
    mode_name=mode,
    max_fret=max_fret,
    position_span=position_span,
    tuning=selected_tuning,
)

midi_note_durations = None
midi_scale_hint = None
midi_playback_events = None
midi_channels = []
midi_channel_colors: dict[int, dict] = {}
if playback_source == "Public MIDI":
    midi_url = PUBLIC_MIDI_SOURCES.get(midi_source_name)
    try:
        with st.spinner("Loading and analyzing MIDI..."):
            midi_bytes = _fetch_public_midi_bytes(str(midi_url or ""))
            effective_midi_limit = None if midi_unlimited_notes else max(30, int(midi_max_notes))
            midi_events = parse_midi_note_on_events(midi_bytes, max_events=effective_midi_limit)
            midi_channels = detect_midi_channels(midi_events)
            midi_channel_colors = build_channel_color_map(midi_channels)
            midi_scale_hint = detect_midi_scale_hint(midi_bytes, midi_events)

            if midi_scale_hint:
                hint_root, hint_mode, _hint_source = midi_scale_hint
                pending_updates = {}

                apply_id = f"{midi_source_name}|{hint_root}|{hint_mode}"
                if st.session_state.get("midi_auto_scale_applied_id") != apply_id:
                    pending_updates["root_note"] = hint_root
                    pending_updates["scale_kind"] = "Diatonic Modes"
                    pending_updates["mode_name"] = hint_mode
                    pending_updates["midi_auto_scale_applied_id"] = apply_id

                root_fret_full = find_root_on_low_e(hint_root, 24, tuning=selected_tuning)
                if root_fret_full is not None and root_fret_full > int(max_fret):
                    fret_apply_id = f"{midi_source_name}|{hint_root}|{root_fret_full}|{len(selected_tuning)}"
                    if st.session_state.get("midi_auto_fret_applied_id") != fret_apply_id:
                        pending_updates["max_fret_value"] = int(root_fret_full)
                        pending_updates["midi_auto_fret_applied_id"] = fret_apply_id

                if pending_updates:
                    st.session_state["midi_pending_widget_updates"] = pending_updates
                    st.rerun()

        path_notes, midi_note_durations, midi_playback_events = build_path_from_midi_events(
            midi_events,
            tuning=selected_tuning,
            max_fret=max_fret,
            max_notes=(None if midi_unlimited_notes else int(midi_max_notes)),
        )
        speed = max(0.05, float(midi_speed or 1.0))
        if midi_note_durations:
            midi_note_durations = [max(0.06, min(2.0, d / speed)) for d in midi_note_durations]
        if midi_playback_events:
            for ev in midi_playback_events:
                base_dur = float(ev.get("duration", seconds_per_note) or seconds_per_note)
                ev["duration"] = max(0.06, min(2.0, base_dur / speed))
    except Exception as exc:
        st.warning(f"Could not load MIDI source: {exc}")
        path_notes = []
        midi_note_durations = []
        midi_playback_events = []
        midi_channels = []
        midi_channel_colors = {}

st.subheader(f"{root} {mode}")
st.caption(f"Scale family: {scale_kind}")
if playback_source == "Public MIDI":
    st.caption(f"MIDI source: {midi_source_name}")
    if midi_scale_hint:
        hint_root, hint_mode, hint_source = midi_scale_hint
        st.caption(f"MIDI key: {hint_root} {hint_mode} ({hint_source})")

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
    if playback_source == "Public MIDI":
        st.warning(
            "No playable MIDI notes were mapped to the current view. "
            "Try increasing Frets/Keys, selecting another MIDI file, or changing Instrument views."
        )
    else:
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

    if "play_all_counter" not in st.session_state:
        st.session_state.play_all_counter = 0
    if "play_all_pending" not in st.session_state:
        st.session_state.play_all_pending = False

    if not view_modes:
        st.warning("Select at least one Instrument view in the sidebar.")
    else:
        channel_instrument_map: dict[int, str] = {}
        if playback_source == "Public MIDI" and midi_channels and audio_engine == "Public Web Samples":
            with st.expander("MIDI channel instrument mapping", expanded=False):
                st.caption("Assign a web instrument per MIDI channel for multi-instrument files.")
                channel_options = ["Off", *list(WEB_SAMPLE_SOURCES.keys())]
                for ch in midi_channels:
                    key = f"midi_channel_instrument_{int(ch)}"
                    default_source = (web_sample_sources[0] if web_sample_sources else list(WEB_SAMPLE_SOURCES.keys())[0])
                    if key not in st.session_state or st.session_state.get(key) not in channel_options:
                        st.session_state[key] = default_source
                    color_info = midi_channel_colors.get(int(ch), {"name": "Color", "hex": "#ffe066"})
                    channel_instrument_map[int(ch)] = st.selectbox(
                        f"Channel {int(ch) + 1} - {color_info.get('name', 'Color')}",
                        options=channel_options,
                        index=channel_options.index(st.session_state[key]) if st.session_state[key] in channel_options else 0,
                        key=key,
                    )

        top_controls_col1, top_controls_col2 = st.columns([1, 4])
        with top_controls_col1:
            if st.button("▶ Play All", use_container_width=True):
                st.session_state.play_all_counter = int(st.session_state.play_all_counter) + 1
                st.session_state.play_all_pending = True

        auto_play_nonce = int(st.session_state.play_all_counter) if st.session_state.play_all_pending else 0

        for view_mode in view_modes:
            st.markdown(f"### {view_mode} + Synchronized Playback")

            st.components.v1.html(
                render_synced_player_html(
                    root=root,
                    mode_name=mode,
                    path_notes=path_notes,
                    max_fret=max_fret,
                    seconds_per_note=seconds_per_note,
                    audio_engine=audio_engine,
                    web_sample_sources=web_sample_sources,
                    sound_preset=sound_preset,
                    view_mode=view_mode,
                    note_durations=midi_note_durations,
                    play_all_nonce=auto_play_nonce,
                    show_all_notes=playback_source == "Public MIDI",
                    tuning=selected_tuning,
                    overlay_scale_notes=scale_notes if playback_source == "Public MIDI" else None,
                    overlay_root_note=root if playback_source == "Public MIDI" else None,
                    playback_events=midi_playback_events if playback_source == "Public MIDI" else None,
                    keyboard_range_mode=keyboard_range_mode,
                    channel_instrument_map=channel_instrument_map if playback_source == "Public MIDI" else None,
                    channel_color_map=midi_channel_colors if playback_source == "Public MIDI" else None,
                ),
                height=580,
                scrolling=False,
            )

        # Consume one-shot trigger so later reruns do not auto-play again.
        if st.session_state.play_all_pending:
            st.session_state.play_all_pending = False

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
