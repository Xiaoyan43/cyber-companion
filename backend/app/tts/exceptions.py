from __future__ import annotations


class TTSError(Exception):
    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        status_code: int = 502,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code


class TTSConfigError(TTSError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=503)


class TTSDisabledError(TTSError):
    def __init__(self, message: str = "Text-to-speech is disabled by config.") -> None:
        super().__init__(message, status_code=503)
