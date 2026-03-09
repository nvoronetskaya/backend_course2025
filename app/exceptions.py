class ModelIsNotAvailable(Exception):
    """Raised when the ML model is not loaded or unreachable."""


class ErrorInPrediction(Exception):
    """Raised when an error occurs during model inference."""


class AdvertisementNotFoundError(Exception):
    """Raised when a requested item is not found."""
