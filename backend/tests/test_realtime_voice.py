import importlib
import sys

import pytest

pytest.importorskip("pipecat")
pytest.importorskip("pyaudio")


def test_run_voice_module_imports() -> None:
    module = importlib.import_module("backend.realtime.run_voice")
    assert callable(module.main)


def test_mac_say_tts_imports() -> None:
    module = importlib.import_module("backend.realtime.mac_say_tts")
    assert module.MacSayTTSService is not None


def test_doubao_tts_service_imports() -> None:
    module = importlib.import_module("backend.realtime.doubao_tts_service")
    assert module.DoubaoTTSService is not None
    assert module.SAMPLE_RATE == 24_000


def test_doubao_stt_service_imports() -> None:
    module = importlib.import_module("backend.realtime.doubao_stt_service")
    assert module.DoubaoFlashSTTService is not None
    assert module.INPUT_SAMPLE_RATE == 16_000


def test_voice_backend_toggle_accepts_streaming(monkeypatch) -> None:
    module = importlib.import_module("backend.realtime.run_voice")
    monkeypatch.setenv("CYBER_COMPANION_VOICE_STT", "doubao_stream")
    selected = module._voice_backend(
        "CYBER_COMPANION_VOICE_STT",
        allowed={"whisper", "doubao", "doubao_stream"},
        default="doubao",
    )
    assert selected == "doubao_stream"


def test_voice_backend_toggle_rejects_unknown(monkeypatch) -> None:
    module = importlib.import_module("backend.realtime.run_voice")
    monkeypatch.setenv("CYBER_COMPANION_VOICE_STT", "bogus")
    with pytest.raises(SystemExit):
        module._voice_backend(
            "CYBER_COMPANION_VOICE_STT",
            allowed={"whisper", "doubao", "doubao_stream"},
            default="doubao",
        )


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS `say` placeholder TTS")
def test_mac_say_tts_can_construct() -> None:
    from backend.realtime.mac_say_tts import MacSayTTSService

    service = MacSayTTSService()
    assert service._say_path
