# File: donations/models.py - PAYMENT GATEWAY FIELD UPDATE
# Add these fields to your existing Donation model

class Donation(models.Model):
    # ... your existing fields ...
    
    # PAYMENT GATEWAY CHOICES
    PAYMENT_GATEWAY_CHOICES = [
        ('paystack', 'Paystack'),
        ('flutterwave', 'Flutterwave'),
        ('stripe', 'Stripe'),  # Keep for legacy/testing
    ]
    
    # NEW FIELDS TO ADD:
    
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
        help_text="Unique payment reference from gateway (tx_ref for Flutterwave, reference for Paystack)"
    )
    
    # ... rest of your existing fields ...
    
    def __str__(self):
        return f"{self.donor.full_name} - ${self.amount} ({self.get_payment_gateway_display()})"


# AFTER UPDATING THE MODEL, RUN THESE COMMANDS:
"""
python manage.py makemigrations
python manage.py migrate
"""

# This will add the new fields to your database
# Existing donations will default to 'paystack' gateway
