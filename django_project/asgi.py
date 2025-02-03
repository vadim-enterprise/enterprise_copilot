# import os
# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# from django.urls import path
# from predict_best_option.transcription import Transcription

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AuthMiddlewareStack(
#         URLRouter([
#             path("ws/transcribe/", Transcription.as_asgi()),
#         ])
#     ),
# })

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from software_auction.routing import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})