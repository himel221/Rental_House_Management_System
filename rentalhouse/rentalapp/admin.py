from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import *

class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'status', 'is_active', 'created_at')
    list_filter = ('user_type', 'status', 'is_active', 'created_at')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'last_login')
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone', 'profile_picture')}),
        ('Permissions', {'fields': ('user_type', 'status', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'created_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'user_type', 'is_staff', 'is_superuser'),
        }),
    )

class TenantAdmin(admin.ModelAdmin):
    list_display = ('tenant_id', 'get_user_email', 'emergency_contact', 'employment_status')
    search_fields = ('user__first_name', 'user__last_name', 'user__email')
    readonly_fields = ('tenant_id',)
    
    def get_user_email(self, obj):
        try:
            return obj.user.email if obj.user else 'N/A'
        except Exception:
            return 'N/A'
    get_user_email.short_description = 'Email'

class OwnerAdmin(admin.ModelAdmin):
    list_display = ('owner_id', 'get_user_email', 'company_name', 'verification_status')
    search_fields = ('user__first_name', 'user__last_name', 'company_name')
    readonly_fields = ('owner_id',)
    
    def get_user_email(self, obj):
        try:
            return obj.user.email if obj.user else 'N/A'
        except Exception:
            return 'N/A'
    get_user_email.short_description = 'Email'

class PropertyAdmin(admin.ModelAdmin):
    list_display = ('property_id', 'title', 'get_owner', 'city', 'property_type', 'rent_amount', 'status')
    list_filter = ('property_type', 'status', 'city')
    search_fields = ('title', 'city', 'address')
    readonly_fields = ('property_id', 'created_at')
    
    def get_owner(self, obj):
        try:
            return str(obj.owner) if obj.owner else 'N/A'
        except Exception:
            return 'N/A'
    get_owner.short_description = 'Owner'

class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_id', 'get_tenant', 'get_property', 'start_date', 'end_date', 'booking_status')
    list_filter = ('booking_status', 'start_date')
    search_fields = ('tenant__user__first_name', 'property__title')
    readonly_fields = ('booking_id', 'created_at')
    
    def get_tenant(self, obj):
        try:
            return str(obj.tenant.user) if obj.tenant and obj.tenant.user else 'N/A'
        except Exception:
            return 'N/A'
    get_tenant.short_description = 'Tenant'
    
    def get_property(self, obj):
        try:
            return str(obj.property.title) if obj.property else 'N/A'
        except Exception:
            return 'N/A'
    get_property.short_description = 'Property'

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'get_tenant', 'amount', 'payment_status', 'due_date')
    list_filter = ('payment_status', 'payment_method')
    search_fields = ('tenant__user__first_name', 'transaction_id')
    readonly_fields = ('payment_id', 'created_at')
    
    def get_tenant(self, obj):
        try:
            return str(obj.tenant.user) if obj.tenant and obj.tenant.user else 'N/A'
        except Exception:
            return 'N/A'
    get_tenant.short_description = 'Tenant'

class ComplaintAdmin(admin.ModelAdmin):
    list_display = ('complaint_id', 'title', 'get_tenant', 'get_property', 'type', 'priority', 'status')
    list_filter = ('type', 'priority', 'status')
    search_fields = ('title', 'tenant__user__first_name')
    readonly_fields = ('complaint_id', 'created_at')
    
    def get_tenant(self, obj):
        try:
            return str(obj.tenant.user) if obj.tenant and obj.tenant.user else 'N/A'
        except Exception:
            return 'N/A'
    get_tenant.short_description = 'Tenant'
    
    def get_property(self, obj):
        try:
            return str(obj.property.title) if obj.property else 'N/A'
        except Exception:
            return 'N/A'
    get_property.short_description = 'Property'

class ReviewsRatingsAdmin(admin.ModelAdmin):
    list_display = ('review_id', 'get_tenant', 'get_property', 'rating', 'is_approved')
    list_filter = ('rating', 'is_approved', 'created_at')
    search_fields = ('tenant__user__first_name', 'property__title')
    readonly_fields = ('review_id', 'created_at')
    
    def get_tenant(self, obj):
        try:
            return str(obj.tenant.user) if obj.tenant and obj.tenant.user else 'N/A'
        except Exception:
            return 'N/A'
    get_tenant.short_description = 'Tenant'
    
    def get_property(self, obj):
        try:
            return str(obj.property.title) if obj.property else 'N/A'
        except Exception:
            return 'N/A'
    get_property.short_description = 'Property'

class NotificationsAdmin(admin.ModelAdmin):
    list_display = ('notification_id', 'get_user', 'type', 'title', 'is_read', 'sent_at')
    list_filter = ('type', 'is_read', 'sent_at')
    search_fields = ('user__first_name', 'title', 'message')
    readonly_fields = ('notification_id', 'sent_at')
    
    def get_user(self, obj):
        try:
            return str(obj.user) if obj.user else 'N/A'
        except Exception:
            return 'N/A'
    get_user.short_description = 'User'

class PropertyImagesAdmin(admin.ModelAdmin):
    list_display = ('image_id', 'get_property', 'caption', 'is_primary', 'uploaded_at')
    list_filter = ('is_primary', 'uploaded_at')
    search_fields = ('property__title', 'caption')
    readonly_fields = ('image_id', 'uploaded_at')
    
    def get_property(self, obj):
        try:
            return str(obj.property.title) if obj.property else 'N/A'
        except Exception:
            return 'N/A'
    get_property.short_description = 'Property'

# Register all models
admin.site.register(Users, UserAdmin)
admin.site.register(Tenants, TenantAdmin)
admin.site.register(Owners, OwnerAdmin)
admin.site.register(Properties, PropertyAdmin)
admin.site.register(Bookings, BookingAdmin)
admin.site.register(Payments, PaymentAdmin)
admin.site.register(ComplaintsRequests, ComplaintAdmin)
admin.site.register(ReviewsRatings, ReviewsRatingsAdmin)
admin.site.register(Notifications, NotificationsAdmin)
admin.site.register(PropertyImages, PropertyImagesAdmin)

# Customize admin site
admin.site.site_header = "Rental Management System Admin"
admin.site.site_title = "Rental Management System"
admin.site.index_title = "Welcome to Rental Management System Admin Panel"