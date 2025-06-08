

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

from django.conf import settings
from django.conf.urls.static import static

from authentication.views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', health_check),
    path('verify-auth/', ValidateTokenView.as_view(), name='validate-token'),
    path('auth/', include('authentication.urls')),  # Include authentication URLs
    path('center-details/', include('center_detail.urls')),  # Include center_detail URLs
    path('diagnosis/', include('diagnosis.urls')),  # Include diagnosis URLs
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),  # Get access & refresh tokens
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Refresh access token
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),  # Verify if token is valid
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)