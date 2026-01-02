# File: donations/admin.py
# OPTION A VERSION - USES SEPARATE FIELDS FROM MODELS

from django.contrib import admin
from django.utils.html import format_html
from .models import Donor, Donation, CrusadeStats, PrayerRequest, Newsletter, CrusadeFlyer


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'phone', 'country', 'created_at']
    list_filter = ['country', 'created_at']
    search_fields = ['full_name', 'email', 'phone']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('full_name', 'email', 'phone', 'country')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    # ✅ USES ACTUAL FIELDS: currency, payment_gateway, message
    list_display = ['donor', 'formatted_amount', 'currency', 'donation_type', 'payment_gateway', 'payment_method', 'status', 'created_at']
    list_filter = ['status', 'currency', 'donation_type', 'payment_method', 'payment_gateway', 'created_at']
    search_fields = ['donor__full_name', 'donor__email', 'payment_reference']
    readonly_fields = ['created_at', 'completed_at']

    fieldsets = (
        ('Donor Information', {
            'fields': ('donor',)
        }),
        ('Donation Details', {
            'fields': ('amount', 'currency', 'donation_type', 'message')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_gateway', 'payment_reference', 'stripe_payment_id', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_completed', 'mark_as_failed']
    
    # ✅ Custom method to show formatted amount with currency symbol
    def formatted_amount(self, obj):
        """Display amount with currency symbol"""
        symbols = {
            'NGN': '₦',
            'USD': '$',
            'EUR': '€',
            'GBP': '£'
        }
        symbol = symbols.get(obj.currency, '$')
        
        return format_html(
            '<strong style="color: #10b981;">{}{:,.2f}</strong>',
            symbol, obj.amount
        )
    formatted_amount.short_description = 'Amount'
    formatted_amount.admin_order_field = 'amount'
    
    def mark_as_completed(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for donation in queryset:
            donation.status = 'completed'
            donation.completed_at = timezone.now()
            donation.save()
            updated += 1
        
        # ⭐ Update stats after marking as completed
        from .models import CrusadeStats
        stats = CrusadeStats.get_stats()
        stats.update_from_donations()
        
        self.message_user(request, f'{updated} donation(s) marked as completed.')
    mark_as_completed.short_description = 'Mark selected donations as completed'
    
    def mark_as_failed(self, request, queryset):
        updated = queryset.update(status='failed')
        self.message_user(request, f'{updated} donation(s) marked as failed.')
    mark_as_failed.short_description = 'Mark selected donations as failed'


@admin.register(CrusadeStats)
class CrusadeStatsAdmin(admin.ModelAdmin):
    list_display = ['total_raised', 'total_donors', 'budgeted_amount', 'crusades_planned', 'last_updated']
    readonly_fields = ['last_updated']
    
    fieldsets = (
        ('Current Statistics', {
            'fields': ('total_raised', 'total_donors')
        }),
        ('Goals and Targets', {
            'fields': ('budgeted_amount', 'crusades_planned', 'countries_list')
        }),
        ('Metadata', {
            'fields': ('last_updated',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one stats object
        return not CrusadeStats.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of stats
        return False


@admin.register(PrayerRequest)
class PrayerRequestAdmin(admin.ModelAdmin):
    list_display = ['donor', 'is_answered', 'created_at', 'answered_at']
    list_filter = ['is_answered', 'created_at']
    search_fields = ['donor__full_name', 'donor__email', 'request_text']
    readonly_fields = ['created_at', 'answered_at']
    
    fieldsets = (
        ('Prayer Request', {
            'fields': ('donor', 'donation', 'request_text')
        }),
        ('Status', {
            'fields': ('is_answered',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'answered_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_answered', 'mark_as_unanswered']
    
    def mark_as_answered(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(is_answered=True, answered_at=timezone.now())
        self.message_user(request, f'{updated} prayer request(s) marked as answered.')
    mark_as_answered.short_description = 'Mark selected requests as answered'
    
    def mark_as_unanswered(self, request, queryset):
        updated = queryset.update(is_answered=False, answered_at=None)
        self.message_user(request, f'{updated} prayer request(s) marked as unanswered.')
    mark_as_unanswered.short_description = 'Mark selected requests as unanswered'


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ['email', 'is_active', 'subscribed_at']
    list_filter = ['is_active', 'subscribed_at']
    search_fields = ['email']
    readonly_fields = ['subscribed_at']
    
    actions = ['activate_subscriptions', 'deactivate_subscriptions']
    
    def activate_subscriptions(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} subscription(s) activated.')
    activate_subscriptions.short_description = 'Activate selected subscriptions'
    
    def deactivate_subscriptions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} subscription(s) deactivated.')
    deactivate_subscriptions.short_description = 'Deactivate selected subscriptions'


@admin.register(CrusadeFlyer)
class CrusadeFlyerAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'display_order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']
    list_editable = ['is_active', 'display_order']
    
    fieldsets = (
        ('Flyer Information', {
            'fields': ('title', 'description', 'image')
        }),
        ('Display Settings', {
            'fields': ('is_active', 'display_order')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )