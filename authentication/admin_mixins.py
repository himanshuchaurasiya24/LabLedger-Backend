class CenterFilteredAdminMixin:
    """
    This mixin filters all views and forms to the user's assigned center,
    unless they are a superuser.
    """
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'center_detail') and request.user.center_detail:
            return qs.filter(center_detail=request.user.center_detail)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            user_center = getattr(request.user, 'center_detail', None)
            if user_center and hasattr(db_field.related_model, 'center_detail'):
                kwargs['queryset'] = db_field.related_model.objects.filter(center_detail=user_center)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_view_permission(self, request, obj=None):
        if obj is None or request.user.is_superuser:
            return True
        return obj.center_detail == request.user.center_detail

    def has_change_permission(self, request, obj=None):
        if obj is None or request.user.is_superuser:
            return True
        return obj.center_detail == request.user.center_detail

    def has_delete_permission(self, request, obj=None):
        if obj is None or request.user.is_superuser:
            return True
        return obj.center_detail == request.user.center_detail

    # --- ADD THIS NEW METHOD ---
    def has_module_permission(self, request):
        """
        Allows staff users to see the model on the admin index page.
        """
        # If the user is a superuser, they can definitely see it.
        if request.user.is_superuser:
            return True
        # Otherwise, if they have a center detail, they are a center admin
        # and should be able to see the module.
        return hasattr(request.user, 'center_detail') and request.user.center_detail is not None