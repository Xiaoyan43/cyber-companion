from __future__ import annotations


class STTError(Exception):
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


class STTConfigError(STTError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=503)


class STTDisabledError(STTError):
    def __init__(self, message: str = "Speech-to-text is disabled by config.") -> None:
        super().__init__(message, status_code=503)
