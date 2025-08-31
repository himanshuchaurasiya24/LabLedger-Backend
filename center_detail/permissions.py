# center_detail/permissions.py
from rest_framework import permissions

class CenterDetailPermission(permissions.BasePermission):
    """
    Superuser -> full CRUD
    Admin (is_admin=True) -> read + update
    Normal user -> read-only
    """

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        if getattr(request.user, "is_admin", False):
            return view.action in ["list", "retrieve", "update", "partial_update"]
        return view.action in ["list", "retrieve"]

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class SubscriptionSuperUserOnly(permissions.BasePermission):
    """Only superusers can do anything with Subscription."""

    def has_permission(self, request, view):
        return request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser
