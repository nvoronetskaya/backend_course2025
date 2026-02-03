from pathlib import Path
from repository.model_repository import ModelRepository
import pickle
from sklearn.linear_model import LogisticRegression
import numpy as np

class LocalModelRepository(ModelRepository):
    def train_model(self):
        """Обучает простую модель на синтетических данных."""
        np.random.seed(42)
        # Признаки: [is_verified_seller, images_qty, description_length, category]
        X = np.random.rand(1000, 4)
        # Целевая переменная: 1 = нарушение, 0 = нет нарушения
        y = (X[:, 0] < 0.3) & (X[:, 1] < 0.2)
        y = y.astype(int)
        
        model = LogisticRegression()
        model.fit(X, y)
        return model

    def save_model(self, model, path="model.pkl"):
        with open(path, "wb") as f:
            pickle.dump(model, f)

    def load_model(self, path="model.pkl"):
        with open(path, "rb") as f:
            return pickle.load(f)
    
    def load_or_train_model(self, path="model.pkl"):
        path_obj = Path(path)
        if path_obj.exists():
            return self.load_model(path)
        model = self.train_model()
        self.save_model(model, path)
        return model
    
    def predict(self, input, model):
        return model.predict_proba(np.array(input, dtype=float).reshape(1, -1))[0]
