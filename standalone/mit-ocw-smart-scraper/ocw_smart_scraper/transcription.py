"""Audio/video transcription utilities using Whisper."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class Transcriber:
    """Wrapper around Whisper for optional transcription."""

    def __init__(self, *, config: Dict[str, any]) -> None:
        self.config = config
        try:
            import whisper  # type: ignore

            self._whisper = whisper
        except Exception:
            self._whisper = None
            logger.warning("Whisper not available; audio transcription disabled")

    def transcribe(self, media_path: Path, *, output_dir: Path) -> Optional[Path]:
        if not self._whisper:
            return None

        model_name = self.config.get("model", "base")
        device = self.config.get("device", "cpu")

        model = self._whisper.load_model(model_name, device=device)  # type: ignore[attr-defined]
        logger.debug("Transcribing %s with whisper-%s on %s", media_path.name, model_name, device)
        result = model.transcribe(str(media_path))  # type: ignore[attr-defined]

        transcript_dir = output_dir / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = transcript_dir / f"{media_path.stem}.txt"
        transcript_path.write_text(result.get("text", ""), encoding="utf-8")
        return transcript_path
