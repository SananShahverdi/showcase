import sys
import types
from pathlib import Path

from ocw_smart_scraper.transcription import Transcriber


def test_transcriber_writes_transcript(tmp_path: Path, monkeypatch) -> None:
    fake_whisper = types.ModuleType("whisper")

    class DummyModel:
        def transcribe(self, file_path: str):  # pragma: no cover - simple stub
            return {"text": "dummy transcript"}

    def load_model(name: str, device: str):  # pragma: no cover - simple stub
        return DummyModel()

    fake_whisper.load_model = load_model  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)

    transcriber = Transcriber(config={"model": "base", "device": "cpu"})
    media_path = tmp_path / "sample.mp3"
    media_path.write_bytes(b"fake audio")

    transcript_path = transcriber.transcribe(media_path, output_dir=tmp_path)
    assert transcript_path is not None
    assert transcript_path.read_text(encoding="utf-8") == "dummy transcript"
