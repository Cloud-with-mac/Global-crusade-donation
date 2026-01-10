from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.donation_page, name='donation_page'),
    path('donate/', views.donation_page, name='donation_page'),
    path('bank-transfer/<int:donation_id>/', views.bank_transfer_confirmation, name='bank_transfer_confirmation'),
    
    # Stripe URLs
    path('stripe/create-session/', views.create_stripe_session, name='create_stripe_session'),
    path('stripe/success/', views.stripe_success, name='stripe_success'),
    path('stripe/cancel/', views.stripe_cancel, name='stripe_cancel'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
    
    # Paystack URLs
    path('paystack/initialize/', views.paystack_initialize, name='paystack_initialize'),
    path('paystack/verify/', views.paystack_verify, name='paystack_verify'),
    path('paystack/webhook/', views.paystack_webhook, name='paystack_webhook'),
    
    # PayPal
    path('paypal/<int:donation_id>/', views.process_paypal, name='process_paypal'),
    
    # ✅ ADD THESE 2 MISSING URLs:
    path('donation/<int:donation_id>/verify/', views.manual_payment_verify, name='manual_payment_verify'),
    path('donation/<int:donation_id>/delete/', views.delete_donation, name='delete_donation'),
    
    # Admin Dashboard
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/donations/', views.donations_list, name='donations_list'),
    path('dashboard/donors/', views.donors_list, name='donors_list'),
    path('dashboard/prayers/', views.prayer_requests_list, name='prayer_requests_list'),
    path('dashboard/prayer/<int:prayer_id>/toggle/', views.mark_prayer_answered, name='mark_prayer_answered'),
    path('dashboard/settings/', views.dashboard_settings, name='dashboard_settings'),
    path('dashboard/logout/', views.dashboard_logout, name='dashboard_logout'),
    
    # Export
    path('export/donors/', views.export_donors_csv, name='export_donors_csv'),
    path('export/donations/', views.export_donations_csv, name='export_donations_csv'),
    
    # Auth
    path('login/', views.custom_login, name='custom_login'),
    
    # Ministry Pages
    path('home/', views.ministry_home, name='ministry_home'),
    path('about/', views.ministry_about, name='ministry_about'),
    path('crusades/', views.ministry_crusades, name='ministry_crusades'),
    path('testimonies/', views.ministry_testimonies, name='ministry_testimonies'),
    path('contact/', views.ministry_contact, name='ministry_contact'),
]