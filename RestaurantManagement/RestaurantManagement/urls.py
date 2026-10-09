from django.contrib import admin
from django.urls import include, path, re_path
from djoser.views import UserViewSet

# Slash-less aliases so /api/users and /api/users/me work exactly as written in
# the spec (Djoser's router only registers the trailing-slash versions).
users_collection = UserViewSet.as_view({'get': 'list', 'post': 'create'})
users_me = UserViewSet.as_view(
    {'get': 'me', 'put': 'me', 'patch': 'me', 'delete': 'me'}
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),  # browsable API login

    # Djoser: registration, /api/users/me/, token login/logout
    re_path(r'^api/users/?$', users_collection),
    re_path(r'^api/users/me/?$', users_me),
    path('api/', include('djoser.urls')),
    path('', include('djoser.urls.authtoken')),      # /token/login/
    path('api/', include('djoser.urls.authtoken')),  # /api/token/login/ (alias)

    # Project endpoints
    path('api/', include('RestaurantManagementAPI.urls')),
]
