import os
from django.apps import AppConfig
from django.conf import settings


class SoftwareAuctionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "software_auction"

    #model_path = os.path.join(settings.MODELS, 'test_model.keras')
    #model = keras.models.load_model(model_path)