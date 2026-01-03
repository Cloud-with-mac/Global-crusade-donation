# File: donations/urls.py
# CLEAN VERSION - NO DUPLICATES, ALL VIEWS MATCH

from django.urls import path
from . import views

urlpatterns = [
    # ═══════════════════════════════════════════════
    # MINISTRY WEBSITE PAGES (at root)
    # ═══════════════════════════════════════════════
    path('', views.ministry_home, name='ministry_home'),
    path('about/', views.ministry_about, name='ministry_about'),
    path('crusades/', views.ministry_crusades, name='ministry_crusades'),
    path('testimonies/', views.ministry_testimonies, name='ministry_testimonies'),
    path('contact/', views.ministry_contact, name='ministry_contact'),
    
    # ═══════════════════════════════════════════════
    # PUBLIC DONATION PAGES
    # ═══════════════════════════════════════════════
    path('donate/', views.donation_page, name='donation_page'),
    path('donate/bank-transfer/<int:donation_id>/', views.bank_transfer_confirmation, name='bank_transfer_confirmation'),
    path('donate/paypal/<int:donation_id>/', views.process_paypal, name='process_paypal'),
    path('donate/success/<int:donation_id>/', views.donation_success, name='donation_success'),
    
    # ═══════════════════════════════════════════════
    # ADMIN DASHBOARD
    # ═══════════════════════════════════════════════
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/donors/', views.donors_list, name='donors_list'),
    path('dashboard/donations/', views.donations_list, name='donations_list'),
    path('dashboard/prayers/', views.prayer_requests_list, name='prayer_requests_list'),
    path('dashboard/prayer/<int:prayer_id>/toggle/', views.mark_prayer_answered, name='mark_prayer_answered'),
    path('dashboard/settings/', views.dashboard_settings, name='dashboard_settings'),
    path('dashboard/stats/update/', views.update_crusade_stats, name='update_crusade_stats'),
    
    # Donation management
    path('dashboard/donation/<int:donation_id>/verify/', views.manual_payment_verify, name='manual_payment_verify'),
    path('dashboard/donation/<int:donation_id>/delete/', views.delete_donation, name='delete_donation'),
    
    # Exports
    path('dashboard/export/donors/', views.export_donors_csv, name='export_donors_csv'),
    path('dashboard/export/donations/', views.export_donations_csv, name='export_donations_csv'),
    
    # ═══════════════════════════════════════════════
    # AUTHENTICATION
    # ═══════════════════════════════════════════════
    path('login/', views.custom_login, name='custom_login'),
    path('logout/', views.dashboard_logout, name='dashboard_logout'),
]