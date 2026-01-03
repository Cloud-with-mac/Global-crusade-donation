# File: donations/models.py
# Location: ministry_donation_site/donations/models.py
# UPDATED VERSION - WITH TESTIMONY MODEL ADDED

from django.db import models
from django.utils import timezone
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Donor(models.Model):
    """Model to store donor information"""
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, default='Nigeria')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.full_name
    
    @property
    def total_donated(self):
        """Calculate total amount donated by this donor"""
        return self.donations.filter(status='completed').aggregate(
            models.Sum('amount')
        )['amount__sum'] or 0


class Donation(models.Model):
    """Model to store donation transactions"""
    
    # Donation Type Choices
    DONATION_TYPE_CHOICES = [
        ('one-time', 'One-Time'),
        ('monthly', 'Monthly'),
    ]
    
    # Payment Method Choices
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Card'),
        ('paypal', 'PayPal'),
        ('bank', 'Bank Transfer'),
    ]
    
    # Payment Status Choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    # Payment Gateway Choices
    PAYMENT_GATEWAY_CHOICES = [
        ('paystack', 'Paystack'),
        ('flutterwave', 'Flutterwave'),
        ('stripe', 'Stripe'),
    ]
    
    # Relationships
    donor = models.ForeignKey(
        Donor, 
        on_delete=models.CASCADE, 
        related_name='donations'
    )
    
    # Currency Choices
    CURRENCY_CHOICES = [
        ('USD', 'US Dollar ($)'),
        ('NGN', 'Nigerian Naira (₦)'),
        ('EUR', 'Euro (€)'),
        ('GBP', 'British Pound (£)'),
    ]

    # Donation Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default='USD',
        help_text="Currency for this donation"
    )
    donation_type = models.CharField(
        max_length=20, 
        choices=DONATION_TYPE_CHOICES,
        default='one-time'
    )
    payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_METHOD_CHOICES,
        default='card'
    )
    message = models.TextField(blank=True, null=True, help_text="Prayer request or message")
    
    # Payment Gateway Information
    payment_gateway = models.CharField(
        max_length=20,
        choices=PAYMENT_GATEWAY_CHOICES,
        default='paystack',
        help_text="Payment gateway used for this donation"
    )
    
    payment_reference = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Unique payment reference from gateway"
    )
    
    stripe_payment_id = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Stripe payment intent ID (legacy)"
    )
    
    # Status and Timestamps
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.donor.full_name} - ${self.amount} ({self.get_payment_gateway_display()})"
    
    def save(self, *args, **kwargs):
        # Set completed_at when status changes to completed
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)


class CrusadeStats(models.Model):
    """Model to store crusade statistics displayed on the donation page"""
    total_raised = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0
    )
    total_donors = models.IntegerField(default=0)
    budgeted_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=50000
    )
    crusades_planned = models.IntegerField(default=12)
    
    # Countries list for crusades
    countries_list = models.TextField(
        blank=True, 
        null=True,
        help_text="Comma-separated list of countries (e.g., Nigeria, Ghana, Kenya)"
    )
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Crusade Statistics'
        verbose_name_plural = 'Crusade Statistics'
    
    def __str__(self):
        return f"Stats - Updated: {self.last_updated.strftime('%Y-%m-%d %H:%M')}"
    
    @classmethod
    def get_stats(cls):
        """Get or create the stats object (singleton pattern)"""
        stats, created = cls.objects.get_or_create(pk=1)
        return stats
    
    def update_from_donations(self):
        """Update stats based on actual donations"""
        completed_donations = Donation.objects.filter(status='completed')
        self.total_raised = completed_donations.aggregate(
            models.Sum('amount')
        )['amount__sum'] or 0
        self.total_donors = Donor.objects.count()
        self.save()
    
    def get_countries_list(self):
        """Return countries as a list"""
        if self.countries_list:
            return [country.strip() for country in self.countries_list.split(',')]
        return []


class PrayerRequest(models.Model):
    """Model to store prayer requests from donors"""
    donor = models.ForeignKey(
        Donor, 
        on_delete=models.CASCADE, 
        related_name='prayer_requests'
    )
    donation = models.ForeignKey(
        Donation, 
        on_delete=models.CASCADE, 
        blank=True, 
        null=True,
        related_name='prayer_requests'
    )
    request_text = models.TextField()
    is_answered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Prayer from {self.donor.full_name}"


class Newsletter(models.Model):
    """Model to store newsletter subscriptions"""
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-subscribed_at']
    
    def __str__(self):
        return self.email


class CrusadeFlyer(models.Model):
    """Model to store crusade flyer images"""
    title = models.CharField(
        max_length=200, 
        help_text="Flyer title (e.g., Nigeria Crusade 2025)"
    )
    image = models.ImageField(
        upload_to='crusade_flyers/', 
        help_text="Upload crusade flyer image"
    )
    description = models.TextField(
        blank=True, 
        null=True, 
        help_text="Optional description"
    )
    is_active = models.BooleanField(
        default=True, 
        help_text="Show on donation page"
    )
    display_order = models.IntegerField(
        default=0, 
        help_text="Order to display (lower = first)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Crusade Flyer'
        verbose_name_plural = 'Crusade Flyers'
    
    def __str__(self):
        return self.title


# ═══════════════════════════════════════════════════
# MINISTRY WEBSITE IMAGES
# ═══════════════════════════════════════════════════

class MinistryImage(models.Model):
    """
    Store images for the ministry website
    Different types: hero, about, crusade, testimony, gallery
    """
    IMAGE_TYPES = [
        ('hero', 'Homepage Hero Image'),
        ('about', 'About Page Image'),
        ('crusade', 'Crusade Event Image'),
        ('testimony', 'Testimony Image'),
        ('gallery', 'Ministry Gallery'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='ministry_images/')
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPES, default='gallery')
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Ministry Image'
        verbose_name_plural = 'Ministry Images'
    
    def __str__(self):
        return f"{self.get_image_type_display()} - {self.title}"


# ═══════════════════════════════════════════════════
# ⭐ NEW: TESTIMONY MODEL
# ═══════════════════════════════════════════════════

class Testimony(models.Model):
    """Model to store testimonies for the ministry website"""
    name = models.CharField(
        max_length=200, 
        help_text="Person's name (e.g., Mary Johnson)"
    )
    location = models.CharField(
        max_length=200, 
        help_text="City, Country (e.g., Lagos, Nigeria)"
    )
    testimony_text = models.TextField(
        help_text="The full testimony content"
    )
    is_active = models.BooleanField(
        default=True, 
        help_text="Show on website?"
    )
    display_order = models.IntegerField(
        default=0, 
        help_text="Lower numbers appear first"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = 'Testimony'
        verbose_name_plural = 'Testimonies'
    
    def __str__(self):
        return f"{self.name} - {self.location}"
    
    def get_initial(self):
        """Get first letter of name for avatar"""
        return self.name[0].upper() if self.name else "T"