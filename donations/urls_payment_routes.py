# File: donations/urls.py - UPDATED WITH PAYMENT ROUTES
# Update your existing urls.py with these payment routes

from django.urls import path
from . import views

urlpatterns = [
    # ============================================
    # PUBLIC DONATION PAGES
    # ============================================
    path('', views.donation_page, name='donation_page'),
    path('success/<int:donation_id>/', views.donation_success, name='donation_success'),
    
    # ============================================
    # PAYMENT PROCESSING ROUTES (NEW/UPDATED)
    # ============================================
    
    # Process payment - handles both Paystack and Flutterwave
    path('payment/process/<int:donation_id>/', views.process_payment, name='process_payment'),
    
    # Verify payment - callback after payment completion
    path('payment/verify/<int:donation_id>/', views.verify_payment, name='verify_payment'),
    
    # ============================================
    # WEBHOOK ENDPOINTS (OPTIONAL BUT RECOMMENDED)
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


# ============================================
# WEBHOOK URL SETUP GUIDE
# ============================================

"""
PAYSTACK WEBHOOK SETUP:
1. Go to https://dashboard.paystack.com/
2. Settings → API Keys & Webhooks
3. Click "Add Webhook URL"
4. Enter: https://yourdomain.com/webhook/paystack/
5. Select events or choose "All events"
6. Save

FLUTTERWAVE WEBHOOK SETUP:
1. Go to https://dashboard.flutterwave.com/
2. Settings → Webhooks
3. Add webhook URL: https://yourdomain.com/webhook/flutterwave/
4. Select events or choose "All events"
5. Copy the Secret Hash (this is your FLUTTERWAVE_SECRET_KEY)
6. Save

IMPORTANT FOR LOCAL TESTING:
- Webhooks won't work on localhost
- Use ngrok to expose your local server:
  1. Download ngrok: https://ngrok.com/
  2. Run: ngrok http 8000
  3. Use the ngrok URL for webhook: https://xxxx.ngrok.io/webhook/paystack/
  4. This allows testing webhooks locally

FOR PRODUCTION:
- Use your actual domain
- Make sure HTTPS is enabled
- Test webhooks using the gateway dashboard
"""
