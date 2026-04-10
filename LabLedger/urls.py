

from django.contrib import admin
from authentication.admin import custom_admin_site
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

from django.conf import settings
from django.conf.urls.static import static

from authentication.views import *
from all_urls import (
    ROOT_ADMIN,
    ROOT_APP_INFO,
    ROOT_AUTH_INCLUDE,
    ROOT_CENTER_DETAILS_INCLUDE,
    ROOT_DIAGNOSIS_INCLUDE,
    ROOT_HEALTH,
    ROOT_TOKEN,
    ROOT_TOKEN_REFRESH,
    ROOT_TOKEN_VERIFY,
    ROOT_VERIFY_AUTH,
)

urlpatterns = [
    path(ROOT_ADMIN, custom_admin_site.urls),
    path(ROOT_HEALTH, health_check),
    path(ROOT_APP_INFO, AppInfoView.as_view(), name='app-info'),
    path(ROOT_VERIFY_AUTH, ValidateTokenView.as_view(), name='validate-token'),
    path(ROOT_AUTH_INCLUDE, include('authentication.urls')),  # Include authentication URLs
    path(ROOT_CENTER_DETAILS_INCLUDE, include('center_detail.urls')),  # Include center_detail URLs
    path(ROOT_DIAGNOSIS_INCLUDE, include('diagnosis.urls')),  # Include diagnosis URLs
    path(ROOT_TOKEN, CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),  # Get access & refresh tokens
    path(ROOT_TOKEN_REFRESH, TokenRefreshView.as_view(), name='token_refresh'),  # Refresh access token
    path(ROOT_TOKEN_VERIFY, TokenVerifyView.as_view(), name='token_verify'),  # Verify if token is valid
]
# change this to serve media files during development when deploying to production use a proper web server
# This will now work because DEBUG is True
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)