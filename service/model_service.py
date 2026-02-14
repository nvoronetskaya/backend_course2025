from dto.request import PredictRequest
from dto.response import PredictResponse

class ModelService:
    """
    Service class for managing model operations

    This service handles model prediction
    """
    def __init__(self, model_repository, item_repository, moderation_repository, model=None):
        self.model_repository = model_repository
        self.item_repository = item_repository
        self.moderation_repository = moderation_repository
        self.model = model
    
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
    
    async def get_prediction_for_item(self, item_id):
        item = await self.item_repository.get_item(item_id)
        if item is None:
            return None
        request = PredictRequest(
            item_id = item.id,
            name = item.name,
            description = item.description,
            category = item.category,
            images_qty = item.images_qty
        )
        return self.predict(request)

    async def get_moderation_task_id_for_item(self, item_id):
        item = await self.item_repository.get_item(item_id)
        if item is None:
            return None
        task_id = await self.moderation_repository.create_moderation(item_id)
        return task_id
    
    async def get_moderation_result(self, task_id):
        return await self.moderation_repository.get_moderation(task_id)