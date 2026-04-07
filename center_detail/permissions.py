from rest_framework import permissions

class CenterDetailPermission(permissions.BasePermission):
    """Superuser: full CRUD, Admin: read+update, Normal: read-only"""

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        if getattr(request.user, "is_admin", False):
            return view.action in ["list", "retrieve", "update", "partial_update"]
        return view.action in ["list", "retrieve"]

    def has_object_permission(self, request, view, obj):
        if not self.has_permission(request, view):
            return False
        if request.user.is_superuser:
            return True
        user_center = getattr(request.user, 'center_detail', None)
        return user_center is not None and obj.pk == user_center.pk


class SubscriptionSuperUserOnly(permissions.BasePermission):
    """Only superusers can create/update/delete subscriptions."""

    def has_permission(self, request, view):
        return request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser


class IsUserNotLocked(permissions.BasePermission):
    """
    Custom permission to only allow users that are not locked.
    """
    # This message will be sent in the response if permission is denied
    message = 'Your account is locked. Please contact an administrator.'

    def has_permission(self, request, view):
        # The permission is only concerned with authenticated users
        if not request.user or not request.user.is_authenticated:
            return False

        # Return True if the user is NOT locked, and False otherwise.
        return not request.user.is_locked


class IsSubscriptionActive(permissions.BasePermission):
    """
    Custom permission to only allow users with an active subscription.
    This version correctly handles the one-to-many relationship.
    """
    message = 'Your subscription is inactive or has expired. Please renew to continue.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        try:
            center = request.user.center_detail
            return center.subscription_is_active

        except AttributeError:
            # This will now correctly catch if a user has no center_detail
            return False
