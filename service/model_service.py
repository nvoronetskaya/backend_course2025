from model.request import PredictRequest
from model.response import PredictResponse

class ModelService:
    """
    Service class for managing model operations

    This service handles model prediction
    """
    def __init__(self, model_repository):
        self.model_repository = model_repository
        self.model = None
    
    def load_or_train_model(self):
        model = self.model_repository.load_or_train_model()
        self.model = model

    def load_model(self):
        model = self.model_repository.load_model()
        self.model = model
    
    def train_model(self):
        model = self.model_repository.train_model()
        self.model = model

    def load_or_train_model(self):
        model = self.model_repository.load_or_train_model()
        self.model = model
    
    def predict(self, request: PredictRequest):
        """
        Generate prediction. For now works without the model for prediction, uses naive approach

        Args:
            request (PredictRequest): Request containing input data for prediction

        Returns:
            bool: If an item ad has errors
        """
        if self.model is None:
            raise FileNotFoundError('Модель не загружена.')
        model_input = self.prepare_features(request)
        probas = self.model_repository.predict(input=model_input, model=self.model)

        return PredictResponse(
            is_violation=probas[1] > probas[0],
            probability=probas[1]
        )
    
    def prepare_features(self, request):
        is_verified_float = 1.0 if request.is_verified_seller else 0.0
        images_qty = min(request.images_qty, 10) / 10.0
        description = len(request.description) / 1000.0
        category = request.category / 100.0
        return [is_verified_float, images_qty, description, category]
