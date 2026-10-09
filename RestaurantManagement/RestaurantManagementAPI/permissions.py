from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated

from .roles import is_manager


class IsManager(BasePermission):
    message = 'Only managers can perform this action.'

    def has_permission(self, request, view):
        return is_manager(request.user)


class ManagerWriteMixin:
    """Any authenticated user may read; only managers may write."""

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsManager()]
