import numpy as np
import pytest

from asp1 import telemetry as t


@pytest.fixture(scope="module")
def model():
    return t.train_model(seed=5, frames=2000)


@pytest.mark.parametrize("text", ["", "a", "abababababab", "TOBEORNOTTOBEORTOBEORNOT", "star tracker reading steady\n" * 20])
def test_lzw_round_trip(text):
    assert t.lzw_decode(t.lzw_encode(text.encode())).decode() == text


def test_lzw_round_trip_random_bytes():
    data = bytes(np.random.default_rng(1).integers(0, 256, 5000, dtype=np.uint8))
    assert t.lzw_decode(t.lzw_encode(data)) == data


def test_arithmetic_code_round_trip_and_cost(model):
    source = t.FrameSource(np.random.default_rng(9), anomaly_rate=0.0)
    for frame in source.frames(300):
        tokens = t.words(frame.text)
        bits = t.arithmetic_encode(model, tokens)
        assert t.arithmetic_decode(model, bits) == tokens
        info = -sum(np.log2(model.probability(p, w)) for p, w in zip([t.START] + tokens, tokens + [t.END]))
        assert len(bits) <= info + 3  # within the coder's termination overhead


def test_model_never_sees_anomalies_and_scores_them_as_surprising(model):
    assert "unknown" not in model.index
    routine = t.FrameSource(np.random.default_rng(1), anomaly_rate=0.0).frames(200)
    assert max(model.perplexity(f.text) for f in routine) < 8
    assert model.perplexity("unknown object crossing field of view") > 30
    assert model.perplexity("bus voltage background quiet") > 8


def test_gate_is_lossless_and_flags_anomalies(model):
    frames = t.FrameSource(np.random.default_rng(4), anomaly_rate=0.2).frames(2000)
    score = t.evaluate_gate(model, frames, threshold=8.0)
    assert score.lossless
    assert score.recall_novel == 1.0
    assert score.recall_unusual == 1.0
    assert score.false_alarm_rate == 0.0
    # A fifth of these frames are anomalies, sent verbatim on purpose.
    assert score.gate_bits < score.raw_bits / 3
    assert score.gate_bits < score.lzw_frame_bits / 3


def test_unknown_words_are_always_sent_verbatim(model):
    gate = t.DownlinkGate(model, threshold=1e9)  # even with no perplexity limit
    packet = gate.encode("star tracker reading wobbly")
    assert packet.mode == "verbatim"
    assert gate.decode(packet) == "star tracker reading wobbly"
