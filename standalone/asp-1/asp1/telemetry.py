"""Downlink gate: routine frames as vocabulary indices, surprising frames verbatim.

A bigram language model, trained only on routine telemetry, scores each frame's
perplexity. Routine frames whose words are all in the vocabulary are arithmetic-coded
with that same model, so each costs about its information content in bits,
and the ground decodes it exactly with a copy of the model. Anything
surprising, or containing an unknown word, is sent verbatim with LZW
compression and flagged for attention. Both paths are lossless, so the gate
trades bandwidth only, never fidelity.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

import numpy as np

WORD = re.compile(r"[a-z]+")
START, UNKNOWN, END = "<s>", "<unk>", "</s>"

# --- Frame source ----------------------------------------------------------------------

SENSORS = ["star tracker", "sun sensor", "magnetometer", "plasma wave receiver", "dust detector", "cosmic ray telescope"]
WHEELS = ["one", "two", "three", "four"]
STEADY = ["steady", "nominal", "within limits", "unchanged"]
BACKGROUND = ["quiet", "steady", "low"]
ROUTINE = [
    lambda r: f"{r.choice(SENSORS)} reading {r.choice(STEADY)}",
    lambda r: f"reaction wheel {r.choice(WHEELS)} speed {r.choice(STEADY)}",
    lambda r: f"battery temperature {r.choice(STEADY)}",
    lambda r: f"bus voltage {r.choice(STEADY)}",
    lambda r: f"{r.choice(SENSORS)} background {r.choice(BACKGROUND)}",
    lambda r: f"attitude hold {r.choice(STEADY)}",
]
# Anomalies with words never seen in routine telemetry.
NOVEL = [
    "unknown object crossing field of view",
    "non gaussian burst detected in plasma wave receiver",
    "unexpected shadow occultation of reference star",
    "spectral line at unexpected wavelength",
    "transient flash in camera field",
    "dust impact rate spike",
]
# Anomalies made only of routine words, in combinations that never occur.
UNUSUAL = [
    lambda r: f"reaction wheel {r.choice(WHEELS)} background {r.choice(BACKGROUND)}",
    lambda r: f"battery temperature reading low",
    lambda r: f"bus voltage background quiet",
    lambda r: f"{r.choice(SENSORS)} speed unchanged",
    lambda r: f"attitude hold reading low",
]


@dataclass
class Frame:
    text: str
    kind: str  # "routine", "novel", or "unusual"

    @property
    def anomalous(self) -> bool:
        return self.kind != "routine"


class FrameSource:
    def __init__(self, rng: np.random.Generator, anomaly_rate: float = 0.03, unusual_share: float = 0.3) -> None:
        self.rng = rng
        self.anomaly_rate = anomaly_rate
        self.unusual_share = unusual_share

    def _pick(self, options):
        return options[int(self.rng.integers(len(options)))]

    def frame(self) -> Frame:
        if self.rng.random() >= self.anomaly_rate:
            return Frame(self._pick(ROUTINE)(self), "routine")
        if self.rng.random() < self.unusual_share:
            return Frame(self._pick(UNUSUAL)(self), "unusual")
        return Frame(self._pick(NOVEL), "novel")

    def choice(self, options):  # used by the templates
        return self._pick(options)

    def frames(self, n: int) -> list[Frame]:
        return [self.frame() for _ in range(n)]


# --- Language model ----------------------------------------------------------------------

def words(text: str) -> list[str]:
    return WORD.findall(text.lower())


class BigramModel:
    """Add-k smoothed bigram model over a closed vocabulary, <unk>, and an end-of-frame symbol."""

    def __init__(self, k: float = 0.1) -> None:
        self.k = k
        self.pairs: dict[str, Counter] = defaultdict(Counter)
        self.vocabulary: list[str] = []
        self.index: dict[str, int] = {}

    def fit(self, texts: list[str]) -> "BigramModel":
        counts = Counter()
        for text in texts:
            tokens = words(text)
            counts.update(tokens)
            for previous, current in zip([START] + tokens, tokens + [END]):
                self.pairs[previous][current] += 1
        self.vocabulary = sorted(counts)
        self.index = {word: i for i, word in enumerate(self.vocabulary)}
        self._tables: dict[str, tuple[list[int], int]] = {}
        return self

    @property
    def symbols(self) -> list[str]:
        """Everything the coder can emit: vocabulary words and the end marker."""
        return self.vocabulary + [END]

    def probability(self, previous: str, word: str) -> float:
        word = word if word in self.index or word == END else UNKNOWN
        following = self.pairs.get(previous, Counter())
        size = len(self.vocabulary) + 2  # plus <unk> and </s>
        return (following[word] + self.k) / (sum(following.values()) + self.k * size)

    def perplexity(self, text: str) -> float:
        """Per-word perplexity of the frame (the end marker is not counted)."""
        tokens = words(text)
        if not tokens:
            return float("inf")
        contexts = [START] + [t if t in self.index else UNKNOWN for t in tokens[:-1]]
        log2 = sum(math.log2(self.probability(c, w)) for c, w in zip(contexts, tokens))
        return 2.0 ** (-log2 / len(tokens))

    def frequencies(self, previous: str) -> tuple[list[int], int]:
        """Integer frequencies over `symbols` in this context, all at least 1, for the arithmetic coder."""
        if previous not in self._tables:
            following = self.pairs.get(previous, Counter())
            freqs = [following[s] * 10 + 1 for s in self.symbols]
            total = sum(freqs)
            if total > MAX_TOTAL:  # keep the coder's precision
                freqs = [max(1, f * MAX_TOTAL // total) for f in freqs]
            cumulative = [0]
            for f in freqs:
                cumulative.append(cumulative[-1] + f)
            self._tables[previous] = (cumulative, cumulative[-1])
        return self._tables[previous]


# --- Arithmetic coding ---------------------------------------------------------------------

PRECISION = 32
FULL = (1 << PRECISION) - 1
HALF = 1 << (PRECISION - 1)
QUARTER = 1 << (PRECISION - 2)
MAX_TOTAL = 1 << 16


def arithmetic_encode(model: BigramModel, tokens: list[str]) -> list[int]:
    """Encode in-vocabulary tokens plus the end marker to a bit list (Witten, Neal and Cleary, 1987)."""
    low, high, pending, bits = 0, FULL, 0, []

    def emit(bit: int) -> None:
        nonlocal pending
        bits.append(bit)
        bits.extend([1 - bit] * pending)
        pending = 0

    previous = START
    for symbol in tokens + [END]:
        cumulative, total = model.frequencies(previous)
        i = model.symbols.index(symbol)
        span = high - low + 1
        high = low + span * cumulative[i + 1] // total - 1
        low = low + span * cumulative[i] // total
        while True:
            if high < HALF:
                emit(0)
            elif low >= HALF:
                emit(1)
                low, high = low - HALF, high - HALF
            elif low >= QUARTER and high < HALF + QUARTER:
                pending += 1
                low, high = low - QUARTER, high - QUARTER
            else:
                break
            low, high = 2 * low, 2 * high + 1
        previous = symbol
    pending += 1
    emit(0 if low < QUARTER else 1)
    return bits


def arithmetic_decode(model: BigramModel, bits: list[int]) -> list[str]:
    low, high, value, position = 0, FULL, 0, 0

    def next_bit() -> int:
        nonlocal position
        bit = bits[position] if position < len(bits) else 0
        position += 1
        return bit

    for _ in range(PRECISION):
        value = (value << 1) | next_bit()
    previous, output = START, []
    while True:
        cumulative, total = model.frequencies(previous)
        span = high - low + 1
        target = ((value - low + 1) * total - 1) // span
        i = next(j for j in range(len(cumulative) - 1) if cumulative[j + 1] > target)
        high = low + span * cumulative[i + 1] // total - 1
        low = low + span * cumulative[i] // total
        while True:
            if high < HALF:
                pass
            elif low >= HALF:
                low, high, value = low - HALF, high - HALF, value - HALF
            elif low >= QUARTER and high < HALF + QUARTER:
                low, high, value = low - QUARTER, high - QUARTER, value - QUARTER
            else:
                break
            low, high, value = 2 * low, 2 * high + 1, (2 * value) | next_bit()
        symbol = model.symbols[i]
        if symbol == END:
            return output
        output.append(symbol)
        previous = symbol


# --- Codecs --------------------------------------------------------------------------------

def lzw_encode(data: bytes) -> list[int]:
    table = {bytes([i]): i for i in range(256)}
    current, codes = b"", []
    for value in data:
        extended = current + bytes([value])
        if extended in table:
            current = extended
        else:
            codes.append(table[current])
            table[extended] = len(table)
            current = bytes([value])
    if current:
        codes.append(table[current])
    return codes


def lzw_decode(codes: list[int]) -> bytes:
    if not codes:
        return b""
    table = {i: bytes([i]) for i in range(256)}
    previous = table[codes[0]]
    output = [previous]
    for code in codes[1:]:
        entry = table[code] if code in table else previous + previous[:1]
        output.append(entry)
        table[len(table)] = previous + entry[:1]
        previous = entry
    return b"".join(output)


def lzw_bits(codes: list[int]) -> int:
    """Variable-width codes: each code uses as many bits as the table size at that moment requires."""
    bits, table_size = 0, 256
    for i, _ in enumerate(codes):
        bits += max(9, math.ceil(math.log2(table_size + 1)))
        if i < len(codes) - 1:
            table_size += 1
    return bits


# --- Gate ------------------------------------------------------------------------------

@dataclass
class Packet:
    mode: str  # "coded" or "verbatim"
    payload: list[int]  # code bits, or LZW codes
    bits: int
    perplexity: float

    @property
    def flagged(self) -> bool:
        return self.mode == "verbatim"


class DownlinkGate:
    MODE_BITS = 1
    LENGTH_BITS = 8  # LZW code count for verbatim frames; coded frames end with their own marker

    def __init__(self, model: BigramModel, threshold: float) -> None:
        self.model = model
        self.threshold = threshold

    def encode(self, text: str) -> Packet:
        perplexity = self.model.perplexity(text)
        tokens = words(text)
        canonical = " ".join(tokens) == text
        if canonical and perplexity <= self.threshold and all(t in self.model.index for t in tokens):
            code = arithmetic_encode(self.model, tokens)
            return Packet("coded", code, self.MODE_BITS + len(code), perplexity)
        codes = lzw_encode(text.encode())
        return Packet("verbatim", codes, self.MODE_BITS + self.LENGTH_BITS + lzw_bits(codes), perplexity)

    def decode(self, packet: Packet) -> str:
        if packet.mode == "coded":
            return " ".join(arithmetic_decode(self.model, packet.payload))
        return lzw_decode(packet.payload).decode()


def raw_bits(text: str) -> int:
    return 8 * len(text.encode())


@dataclass
class GateScore:
    threshold: float
    frames: int
    anomalies: int
    raw_bits: int
    lzw_frame_bits: int
    lzw_batch_bits: int
    index_bits: int
    gate_bits: int
    recall_novel: float
    recall_unusual: float
    false_alarm_rate: float
    lossless: bool

    @property
    def ratio_vs_raw(self) -> float:
        return self.raw_bits / self.gate_bits

    @property
    def ratio_vs_lzw_batch(self) -> float:
        return self.lzw_batch_bits / self.gate_bits


def evaluate_gate(model: BigramModel, frames: list[Frame], threshold: float) -> GateScore:
    gate = DownlinkGate(model, threshold)
    packets = [gate.encode(f.text) for f in frames]
    novel = [p.flagged for f, p in zip(frames, packets) if f.kind == "novel"]
    unusual = [p.flagged for f, p in zip(frames, packets) if f.kind == "unusual"]
    routine = [p.flagged for f, p in zip(frames, packets) if f.kind == "routine"]
    batch = lzw_encode("\n".join(f.text for f in frames).encode())
    return GateScore(
        threshold=threshold,
        frames=len(frames),
        anomalies=len(novel) + len(unusual),
        raw_bits=sum(raw_bits(f.text) for f in frames),
        lzw_frame_bits=sum(DownlinkGate.MODE_BITS + DownlinkGate.LENGTH_BITS + lzw_bits(lzw_encode(f.text.encode())) for f in frames),
        lzw_batch_bits=lzw_bits(batch),
        index_bits=sum(p.bits if p.flagged else DownlinkGate.MODE_BITS + DownlinkGate.LENGTH_BITS + len(words(f.text)) * math.ceil(math.log2(len(model.vocabulary))) for f, p in zip(frames, packets)),
        gate_bits=sum(p.bits for p in packets),
        recall_novel=float(np.mean(novel)) if novel else float("nan"),
        recall_unusual=float(np.mean(unusual)) if unusual else float("nan"),
        false_alarm_rate=float(np.mean(routine)) if routine else float("nan"),
        lossless=all(gate.decode(p) == f.text for f, p in zip(frames, packets)),
    )


def train_model(seed: int, frames: int = 3000) -> BigramModel:
    """Fit on routine frames only: the model never sees an anomaly."""
    source = FrameSource(np.random.default_rng(seed), anomaly_rate=0.0)
    return BigramModel().fit([f.text for f in source.frames(frames)])
