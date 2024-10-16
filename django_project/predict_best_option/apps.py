import os
from django.apps import AppConfig
from django.conf import settings
import keras

class PredictBestOptionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "predict_best_option"

    model_path = os.path.join(settings.MODELS, 'test_model.keras')
    model = keras.models.load_model(model_path)