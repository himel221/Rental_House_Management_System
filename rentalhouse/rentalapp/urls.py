from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('', views.home, name='home'),
    path('register/', views.user_register, name='user_register'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('profile/', views.user_profile, name='user_profile'),
    
    # Dashboard URLs
    path('dashboard/tenant/', views.tenant_dashboard, name='tenant_dashboard'),
    path('dashboard/owner/', views.owner_dashboard, name='owner_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    
    # Property URLs
    path('properties/', views.property_search, name='property_search'),
    path('properties/<int:property_id>/', views.property_detail, name='property_detail'),
    path('my-properties/', views.property_list, name='property_list'),
    path('properties/add/', views.add_property, name='add_property'),
    path('properties/edit/<int:property_id>/', views.edit_property, name='edit_property'),
    path('properties/delete/<int:property_id>/', views.delete_property, name='delete_property'),
    
    # Booking URLs
    path('book/<int:property_id>/', views.book_property, name='book_property'),
    
    # Payment URLs
   # path('payment/<int:booking_id>/', views.make_payment, name='make_payment'),
   # path('payment/<int:booking_id>/pay/<int:payment_id>/', views.make_payment, name='make_payment_with_id'),
    
    # Complaint URLs
    path('complaints/submit/', views.submit_complaint, name='submit_complaint'),
    path('owner/complaints/', views.owner_complaints, name='owner_complaints'),
    path('owner/complaints/resolve/<int:complaint_id>/', views.quick_resolve_complaint, name='quick_resolve_complaint'),
    
    # Review URLs
    path('reviews/submit/<int:booking_id>/', views.submit_review, name='submit_review'),
    
    # Message URLs
    path('messages/send/', views.send_message, name='send_message'),
    path('messages/inbox/', views.inbox, name='inbox'),
    # Add this to your urlpatterns
path('messages/delete/<int:message_id>/', views.delete_message, name='delete_message'),
    
    # Notification URLs
    path('notifications/', views.view_notifications, name='view_notifications'),
    path('notifications/mark/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    
    # Booking management URLs
    path('booking/confirm/<int:booking_id>/', views.confirm_booking, name='confirm_booking'),
    path('booking/cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    
    # Owner specific URLs
    path('owner/bookings/', views.owner_booking_list, name='owner_booking_list'),
    path('owner/payments/', views.owner_payments, name='owner_payments'),
    path('owner/payment/confirm/<int:payment_id>/', views.confirm_payment, name='confirm_payment'),
    path('owner/payments/export/', views.export_payments_csv, name='export_payments_csv'),
    path('owner/payments/export/pdf/', views.export_payments_pdf, name='export_payments_pdf'),
    # SSLCommerz Payment Integration
    path('payment/sslcommerz/initiate/<int:booking_id>/', 
         views.initiate_sslcommerz_payment, name='initiate_sslcommerz_payment'),
    path('payment/sslcommerz/success/', views.sslcommerz_success, name='sslcommerz_success'),
    path('payment/sslcommerz/fail/', views.sslcommerz_fail, name='sslcommerz_fail'),
    path('payment/sslcommerz/cancel/', views.sslcommerz_cancel, name='sslcommerz_cancel'),
    path('payment/sslcommerz/ipn/', views.sslcommerz_ipn, name='sslcommerz_ipn'),




]