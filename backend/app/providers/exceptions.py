class ProviderError(Exception):
    def __init__(self, message: str, *, provider: str | None = None, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code


class ProviderConfigError(ProviderError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=500)


class ProviderNotConfiguredError(ProviderError):
    def __init__(self, message: str, *, provider: str) -> None:
        super().__init__(message, provider=provider, status_code=503)


class ProviderRequestError(ProviderError):
    def __init__(self, message: str, *, provider: str) -> None:
        super().__init__(message, provider=provider, status_code=502)
