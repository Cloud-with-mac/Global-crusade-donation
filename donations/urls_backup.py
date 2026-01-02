# File: donations/urls.py
# Location: ministry_donation_site/donations/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ============================================
    # PUBLIC DONATION PAGES
    # ============================================
    path('', views.donation_page, name='donation_page'),
    path('success/<int:donation_id>/', views.donation_success, name='donation_success'),
    
    # ============================================
    # PAYMENT PROCESSING ROUTES
    # ============================================
    
    # Process payment - handles both Paystack and Flutterwave
    path('payment/process/<int:donation_id>/', views.process_payment, name='process_payment'),
    
    # Verify payment - callback after payment completion
    path('payment/verify/<int:donation_id>/', views.verify_payment, name='verify_payment'),
    
    # ============================================
    # WEBHOOK ENDPOINTS (FOR PAYSTACK & FLUTTERWAVE)
    # ============================================
    
    # Paystack webhook - receives payment notifications
    path('webhook/paystack/', views.paystack_webhook, name='paystack_webhook'),
    
    # Flutterwave webhook - receives payment notifications
    path('webhook/flutterwave/', views.flutterwave_webhook, name='flutterwave_webhook'),
    
    # ============================================
    # CUSTOM ADMIN DASHBOARD
    # ============================================
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/login/', views.custom_login, name='custom_login'),
    path('dashboard/logout/', views.dashboard_logout, name='dashboard_logout'),
    path('dashboard/settings/', views.dashboard_settings, name='dashboard_settings'),
    path('dashboard/donors/', views.donors_list, name='donors_list'),
    path('dashboard/donations/', views.donations_list, name='donations_list'),
    path('dashboard/prayers/', views.prayer_requests_list, name='prayer_requests_list'),
    path('dashboard/prayer/<int:prayer_id>/toggle/', views.mark_prayer_answered, name='mark_prayer_answered'),
    path('dashboard/stats/update/', views.update_crusade_stats, name='update_crusade_stats'),
    
    # ============================================
    # DATA EXPORT
    # ============================================
    path('dashboard/export/donors/', views.export_donors_csv, name='export_donors_csv'),
    path('dashboard/export/donations/', views.export_donations_csv, name='export_donations_csv'),
]