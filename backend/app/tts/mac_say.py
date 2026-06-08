from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from backend.app.tts.base import TextToSpeechProvider
from backend.app.tts.exceptions import TTSError
from backend.app.tts.types import SynthesisRequest, SynthesisResult, TTSProviderStatus
from backend.app.tts.wav_utils import parse_wav_duration_ms

DEFAULT_VOICE = "Tingting"


class MacSayTTSProvider(TextToSpeechProvider):
    name = "mac_say"
    cloud = False

    def __init__(
        self,
        *,
        voice: str = DEFAULT_VOICE,
        enabled: bool = True,
    ) -> None:
        self._voice = voice
        self._enabled = enabled

    def _resolve_say_path(self) -> str:
        say_path = shutil.which("say")
        if not say_path:
            raise TTSError(
                "macOS `say` command is not available on this system.",
                provider=self.name,
                status_code=503,
            )
        return say_path

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        say_path = self._resolve_say_path()
        text = request.text

        tmp_fd, tmp_path_str = tempfile.mkstemp(suffix=".wav")
        os.close(tmp_fd)
        tmp_path = Path(tmp_path_str)

        try:
            completed = subprocess.run(
                [
                    say_path,
                    "-v",
                    self._voice,
                    "-o",
                    str(tmp_path),
                    "--file-format=WAVE",
                    "--data-format=LEI16@22050",
                    text,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                stderr = (completed.stderr or "").strip()
                raise TTSError(
                    f"macOS `say` synthesis failed: {stderr or 'unknown error'}",
                    provider=self.name,
                )

            audio_bytes = tmp_path.read_bytes()
            if not audio_bytes:
                raise TTSError(
                    "macOS `say` produced empty audio output.",
                    provider=self.name,
                )

            duration_ms = parse_wav_duration_ms(audio_bytes)
            return SynthesisResult(
                provider=self.name,
                model=f"mac-say-{self._voice}",
                audio_bytes=audio_bytes,
                mime_type="audio/wav",
                duration_ms=duration_ms,
                mock=False,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    def status(self) -> TTSProviderStatus:
        say_available = shutil.which("say") is not None
        return TTSProviderStatus(
            name=self.name,
            enabled=self._enabled,
            model=f"mac-say-{self._voice}",
            configured=say_available,
            api_key_present=False,
            placeholder=False,
            cloud=False,
        )
