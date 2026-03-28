from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, LoginSlideshowImage



@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'phone_number', 'first_name', 'last_name', 'dpu', 'region', 'unit', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'is_admin', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone_number')}),
        (_('Role & Permissions'), {'fields': ('role', 'is_active', 'is_staff', 'is_admin', 'is_superuser')}),
        (_('Deployment'), {'fields': ('dpu', 'region', 'unit')}),
        (_('Security'), {'fields': ('is_locked', 'locked_until', 'failed_login_attempts')}),
        (_('Important dates'), {'fields': ('last_login', 'created_at')}),
        (_('Other'), {'fields': ('is_first_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'phone_number', 'role', 'password1', 'password2','dpu','region', 'unit'),
        }),
    )

    readonly_fields = ('created_at', 'last_login')
    filter_horizontal = ('groups', 'user_permissions')

    def save_model(self, request, obj, form, change):
        # Trigger model-level clean() so the "at least one location" rule is
        # enforced even when creating/editing users from the Django admin panel.
        obj.full_clean()
        super().save_model(request, obj, form, change)
        
        
@admin.register(LoginSlideshowImage)
class LoginSlideshowImageAdmin(admin.ModelAdmin):
    list_display  = ['id', 'caption', 'order', 'is_active', 'uploaded_at']
    list_editable = ['order', 'is_active']
    ordering      = ['order', 'uploaded_at']
