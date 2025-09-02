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
        return self.has_permission(request, view)


class SubscriptionSuperUserOnly(permissions.BasePermission):
    """Only superusers can create/update/delete subscriptions."""

    def has_permission(self, request, view):
        return request.user.is_superuser

    def has_object_permission(self, request, view, obj):
        return request.user.is_superuser


# In center_detail/permissions.py

from rest_framework import permissions

class IsSubscriptionActive(permissions.BasePermission):
    """
    Custom permission to only allow users with an active subscription.
    This version correctly handles the one-to-many relationship.
    """
    message = 'Your subscription is inactive or has expired. Please renew to continue.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        try:
            # CORRECTED LINE: Access the first subscription from the collection
            subscription = request.user.center_detail.subscriptions.first()

            # Add a check to ensure a subscription actually exists
            if not subscription:
                return False

            # The rest of the logic remains the same
            is_active = subscription.is_active
            days_left_positive = subscription.days_left > 0

            return is_active and days_left_positive

        except AttributeError:
            # This will now correctly catch if a user has no center_detail
            return False

# from django.core.cache import cache
# from rest_framework import permissions

# class IsSubscriptionActive(permissions.BasePermission):
#     message = 'Your subscription is inactive or has expired. Please renew to continue.'

#     def has_permission(self, request, view):
#         if not request.user or not request.user.is_authenticated:
#             return False

#         # Create a unique cache key for the user's subscription status
#         cache_key = f'subscription_status_{request.user.id}'

#         # 1. Try to get the status from the cache first
#         is_valid = cache.get(cache_key)

#         if is_valid is None:
#             # 2. If not in cache (cache miss), query the DB
#             try:
#                 subscription = request.user.center_detail.subscription
#                 is_valid = subscription.is_active and subscription.days_left > 0
#             except AttributeError:
#                 is_valid = False

#             # 3. Store the result in the cache for 10 minutes (600 seconds)
#             cache.set(cache_key, is_valid, 600)

#         return is_valid