# ============================================================
# Provider Exceptions — Unified error hierarchy
# ============================================================
# All providers throw exceptions from this hierarchy.
# Upper layers (Agent Runtime, API) only catch ProviderError.
# ============================================================


class ProviderError(Exception):
    pass


class ProviderNotFound(ProviderError):
    pass


class AuthenticationError(ProviderError):
    pass


class RateLimitError(ProviderError):
    pass


class ModelNotFoundError(ProviderError):
    pass


class ProviderConnectionError(ProviderError):
    pass