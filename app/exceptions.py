class ModelIsNotAvailable(Exception):
    """Raised when the ML model is not loaded or unreachable."""


class ErrorInPrediction(Exception):
    """Raised when an error occurs during model inference."""


class AdvertisementNotFoundError(Exception):
    """Raised when a requested item is not found."""


class InvalidCredentialsError(Exception):
    """Raised when login/password pair is not found."""


class AccountBlockedError(Exception):
    """Raised when the account is blocked."""


class InvalidTokenError(Exception):
    """Raised when a JWT token is invalid or expired."""
