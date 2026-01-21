from model.request import PredictRequest

class ModelService:
    """
    Service class for managing model operations

    This service handles model prediction
    """

    def predict(self, request: PredictRequest):
        """
        Generate prediction. For now works without the model for prediction, uses naive approach

        Args:
            request (PredictRequest): Request containing input data for prediction

        Returns:
            bool: If an item ad has errors
        """
        is_correct = request.is_verified_seller or request.images_qty > 0
        return not is_correct
