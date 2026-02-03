from pathlib import Path
from repository.model_repository import ModelRepository
import pickle
from sklearn.linear_model import LogisticRegression
import logging
import mlflow
import numpy as np
from mlflow.tracking import MlflowClient
import uuid

logger = logging.getLogger(__name__)

class MlflowModelRepository(ModelRepository):
    def __init__(self, tracking_uri):
        mlflow.set_tracking_uri(tracking_uri)
        self.mlflow_client = MlflowClient(tracking_uri)

    def train_model(self, path="logreg"):
        """Обучает простую модель на синтетических данных."""
        np.random.seed(42)
        # Признаки: [is_verified_seller, images_qty, description_length, category]
        X = np.random.rand(1000, 4)
        # Целевая переменная: 1 = нарушение, 0 = нет нарушения
        y = (X[:, 0] < 0.3) & (X[:, 1] < 0.2)
        y = y.astype(int)
        
        model = LogisticRegression()
        model.fit(X, y)
        run_name = f"train_{uuid.uuid4().hex[:8]}"
        with mlflow.start_run(run_name=run_name) as run:
            try:
                mlflow.log_params({"model_class": "LogisticRegression"})
                train_accuracy = model.score(X, y)
                mlflow.log_metric("train_accuracy", train_accuracy)
                mlflow.sklearn.log_model(model, artifact_path="main_model")
                model_uri = f"runs:/{run.info.run_id}/main_model"
                version = mlflow.register_model(model_uri, path)
                self.mlflow_client.transition_model_version_stage(
                    name=path,
                    version=version.version,
                    stage="Production",
                    archive_existing_versions=True,
                )
            except Exception as e:
                raise RuntimeError(f'Failed to train and save MlFlow model. Reason: {str(e)}')
            return model

    def save_model(self, model, path="logreg"):
        run_name = f"save_{uuid.uuid4().hex[:8]}"
        with mlflow.start_run(run_name=run_name) as run:
            try:
                mlflow.sklearn.log_model(model, artifact_path="main_model")
                model_uri = f"runs:/{run.info.run_id}/main_model"
                version = mlflow.register_model(model_uri, path)
                self.mlflow_client.transition_model_version_stage(
                    name=path,
                    version=version.version,
                    stage="Production",
                    archive_existing_versions=True,
                )
            except Exception as e:
                raise RuntimeError(f'Failed to save MlFlow model. Reason: {str(e)}')

    def load_model(self, path="logreg"):
        model_uri = f"models:/{path}/Production"
        try:
            model = mlflow.sklearn.load_model(model_uri)
            return model
        except Exception as e:
            raise RuntimeError(f'Failed to load MlFlow model. Reason: {str(e)}')
    
    def load_or_train_model(self, path="logreg"):
        try:
            model = self.load_model(path)
        except Exception:
            model = self.train_model(path)
        return model
    
    def predict(self, input, model):
        return model.predict_proba(np.array(input, dtype=float).reshape(1, -1))[0]
