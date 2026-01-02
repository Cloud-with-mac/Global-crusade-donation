# File: donations/urls.py
# ADD THIS URL PATTERN FOR DELETE FUNCTIONALITY

from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.donation_page, name='donation_page'),
    path('bank-transfer/<int:donation_id>/', views.bank_transfer_confirmation, name='bank_transfer_confirmation'),
    path('paypal/<int:donation_id>/', views.process_paypal, name='process_paypal'),
    path('success/<int:donation_id>/', views.donation_success, name='donation_success'),
    
    # Admin dashboard
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/donors/', views.donors_list, name='donors_list'),
    path('dashboard/donations/', views.donations_list, name='donations_list'),
    path('dashboard/prayers/', views.prayer_requests_list, name='prayer_requests_list'),
    path('dashboard/prayer/<int:prayer_id>/toggle/', views.mark_prayer_answered, name='mark_prayer_answered'),
    path('dashboard/settings/', views.dashboard_settings, name='dashboard_settings'),
    path('dashboard/stats/update/', views.update_crusade_stats, name='update_crusade_stats'),
    
    # Donation verification & deletion
    path('dashboard/donation/<int:donation_id>/verify/', views.manual_payment_verify, name='manual_payment_verify'),
    path('dashboard/donation/<int:donation_id>/delete/', views.delete_donation, name='delete_donation'),  # ⭐ NEW!
    
    # Exports
    path('dashboard/export/donors/', views.export_donors_csv, name='export_donors_csv'),
    path('dashboard/export/donations/', views.export_donations_csv, name='export_donations_csv'),
    
    # Auth
    path('login/', views.custom_login, name='custom_login'),
    path('logout/', views.dashboard_logout, name='dashboard_logout'),
]