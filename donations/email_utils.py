# File: donations/email_utils.py
# OPTION A VERSION - USES SEPARATE CURRENCY, PAYMENT_GATEWAY, MESSAGE FIELDS
# ✅ FIXED: Added 'currency' variable to send_donation_receipt context (line 42)

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags


def get_currency_display(donation):
    """Get formatted currency display for a donation - OPTION A VERSION"""
    symbols = {
        'NGN': '₦',
        'USD': '$',
        'EUR': '€',
        'GBP': '£'
    }
    
    # ✅ Read from donation.currency field directly
    currency_code = donation.currency or 'NGN'
    symbol = symbols.get(currency_code, '₦')
    
    return {
        'symbol': symbol,
        'code': currency_code,
        'formatted_amount': f"{symbol}{donation.amount:,.2f}"
    }


def send_donation_receipt(donation, prayer_request=None):
    """Send donation receipt to donor - OPTION A VERSION"""
    
    # Get currency display
    currency_info = get_currency_display(donation)
    
    subject = f"Thank You for Your {currency_info['formatted_amount']} Donation!"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = donation.donor.email
    
    # Prepare context
    context = {
        'donor_name': donation.donor.full_name,
        'amount': donation.amount,
        'currency': currency_info['code'],  # ✅ FIXED: Added currency variable for template!
        'currency_symbol': currency_info['symbol'],
        'currency_code': currency_info['code'],
        'formatted_amount': currency_info['formatted_amount'],
        'donation_id': donation.id,
        'donation_date': donation.created_at.strftime('%B %d, %Y at %I:%M %p'),
        'donation_type': donation.get_donation_type_display(),
        'payment_method': donation.get_payment_method_display(),
        'payment_gateway': donation.get_payment_gateway_display(),
        'transaction_id': donation.payment_reference or donation.stripe_payment_id or 'Processing',
        'prayer_request': prayer_request.request_text if prayer_request else None,
    }
    
    # Render HTML email
    html_content = render_to_string('emails/donation_receipt.html', context)
    text_content = strip_tags(html_content)
    
    # Create email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=[to_email]
    )
    email.attach_alternative(html_content, "text/html")
    
    # Send email
    try:
        email.send()
        return True
    except Exception as e:
        print(f"Error sending donation receipt: {str(e)}")
        return False


def send_admin_notification(donation, is_first_time=False, prayer_request=None):
    """Send notification to admin about new donation - OPTION A VERSION"""
    
    # Get currency display
    currency_info = get_currency_display(donation)
    
    subject = f"🎉 New Donation Received: {currency_info['formatted_amount']}"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = settings.ADMIN_EMAIL
    
    # Prepare context
    context = {
        'amount': donation.amount,
        'currency_symbol': currency_info['symbol'],
        'currency_code': currency_info['code'],
        'formatted_amount': currency_info['formatted_amount'],
        'donor_name': donation.donor.full_name,
        'donor_email': donation.donor.email,
        'donor_phone': donation.donor.phone or 'Not provided',
        'donor_country': donation.donor.country,
        'is_first_time': is_first_time,
        'donation_id': donation.id,
        'donation_date': donation.created_at.strftime('%B %d, %Y at %I:%M %p'),
        'donation_type': donation.get_donation_type_display(),
        'payment_method': donation.get_payment_method_display(),
        'payment_gateway': donation.get_payment_gateway_display(),
        'transaction_id': donation.payment_reference or donation.stripe_payment_id or 'Pending',
        'prayer_request': prayer_request.request_text if prayer_request else None,
        'dashboard_url': f"{settings.SITE_URL}/dashboard/",
        'notification_date': donation.created_at.strftime('%B %d, %Y at %I:%M %p'),
    }
    
    # Render HTML email
    html_content = render_to_string('emails/admin_notification.html', context)
    text_content = strip_tags(html_content)
    
    # Create email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=[to_email]
    )
    email.attach_alternative(html_content, "text/html")
    
    # Send email
    try:
        email.send()
        return True
    except Exception as e:
        print(f"Error sending admin notification: {str(e)}")
        return False


def send_prayer_confirmation(donation, prayer_request):
    """Send prayer request confirmation to donor"""
    
    # Get currency display
    currency_info = get_currency_display(donation)
    
    subject = "🙏 We're Praying for You"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = donation.donor.email
    
    # Prepare context
    context = {
        'donor_name': donation.donor.full_name,
        'prayer_request': prayer_request.request_text,
        'website_url': settings.SITE_URL,
    }
    
    # Render HTML email
    html_content = render_to_string('emails/prayer_confirmation.html', context)
    text_content = strip_tags(html_content)
    
    # Create email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=[to_email]
    )
    email.attach_alternative(html_content, "text/html")
    
    # Send email
    try:
        email.send()
        return True
    except Exception as e:
        print(f"Error sending prayer confirmation: {str(e)}")
        return False


def send_welcome_email(donation):
    """Send welcome email to first-time donors - OPTION A VERSION"""
    
    # Get currency display
    currency_info = get_currency_display(donation)
    
    subject = "Welcome to Our Ministry Family! 🎉"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = donation.donor.email
    
    # Prepare context
    context = {
        'donor_name': donation.donor.full_name,
        'amount': donation.amount,
        'currency_symbol': currency_info['symbol'],
        'currency_code': currency_info['code'],
        'formatted_amount': currency_info['formatted_amount'],
        'website_url': settings.SITE_URL,
    }
    
    # Render HTML email
    html_content = render_to_string('emails/welcome_email.html', context)
    text_content = strip_tags(html_content)
    
    # Create email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=[to_email]
    )
    email.attach_alternative(html_content, "text/html")
    
    # Send email
    try:
        email.send()
        return True
    except Exception as e:
        print(f"Error sending welcome email: {str(e)}")
        return False


def send_monthly_partner_email(donation):
    """Send thank you email to monthly partners - OPTION A VERSION"""
    
    # Get currency display
    currency_info = get_currency_display(donation)
    
    subject = f"Thank You for Your Monthly Partnership! ({currency_info['formatted_amount']})"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = donation.donor.email
    
    # Prepare context
    context = {
        'donor_name': donation.donor.full_name,
        'amount': donation.amount,
        'currency_symbol': currency_info['symbol'],
        'currency_code': currency_info['code'],
        'formatted_amount': currency_info['formatted_amount'],
        'website_url': settings.SITE_URL,
    }
    
    # Simple text email for monthly partners
    message = f"""
Dear {donation.donor.full_name},

Thank you for becoming a monthly partner with your {currency_info['formatted_amount']} commitment!

Your ongoing support enables us to:
- Plan long-term crusade campaigns
- Provide consistent community outreach
- Train and equip ministry leaders
- Reach more souls with the Gospel

We're honored to have you as part of our ministry family.

God bless you abundantly!

Global Crusade Ministry
{settings.SITE_URL}
    """
    
    # Send email
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending monthly partner email: {str(e)}")
        return False


def send_bank_transfer_instructions(donation):
    """Send bank transfer instructions email - OPTION A VERSION"""
    
    # Get currency display
    currency_info = get_currency_display(donation)
    
    subject = f"Bank Transfer Details for Your {currency_info['formatted_amount']} Donation"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = donation.donor.email
    
    # Bank details
    bank_details = {
        'bank_name': 'United Bank Africa PLC',
        'account_number': '1023888802',
        'account_name': 'Eternity Voice International Ministry',
        'amount': currency_info['formatted_amount'],
    }
    
    message = f"""
Dear {donation.donor.full_name},

Thank you for choosing to support our ministry with a {currency_info['formatted_amount']} donation!

BANK TRANSFER DETAILS:
----------------------
Bank Name: {bank_details['bank_name']}
Account Number: {bank_details['account_number']}
Account Name: {bank_details['account_name']}
Amount to Transfer: {currency_info['formatted_amount']}

NEXT STEPS:
-----------
1. Make the bank transfer using the details above
2. Email us your transaction reference at: eternityvoiceministry@gmail.com
3. We'll confirm your donation and send you a receipt within 24 hours

Reference Number: DON-{donation.id}

If you have any questions, please contact us at +447411583033 or reply to this email.

Thank you for your generous support!

God bless you,
Global Crusade Ministry
{settings.SITE_URL}
    """
    
    # Send email
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending bank transfer instructions: {str(e)}")
        return False


def send_donation_completed_email(donation):
    """Send email when donation status changes to completed - OPTION A VERSION"""
    
    # Get currency display
    currency_info = get_currency_display(donation)
    
    subject = f"Your {currency_info['formatted_amount']} Donation is Confirmed! ✅"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = donation.donor.email
    
    message = f"""
Dear {donation.donor.full_name},

Great news! We've confirmed your {currency_info['formatted_amount']} donation.

Donation Details:
-----------------
Amount: {currency_info['formatted_amount']}
Date: {donation.created_at.strftime('%B %d, %Y')}
Reference: DON-{donation.id}
Type: {donation.get_donation_type_display()}

Your generous contribution is making a real difference in our global crusade ministry. Thank you for partnering with us to reach nations with the Gospel!

This donation is tax-deductible. Please retain this email for your records.

God bless you abundantly!

Global Crusade Ministry
{settings.SITE_URL}
    """
    
    # Send email
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending donation completed email: {str(e)}")
        return False


def send_all_donation_emails(donation, prayer_request=None):
    """
    Send all relevant emails for a new donation - OPTION A VERSION
    
    This is the main function to call when a donation is created.
    It will send:
    1. Receipt to donor
    2. Admin notification
    3. Prayer confirmation (if prayer request exists)
    4. Welcome email (if first-time donor)
    5. Monthly partner email (if monthly donation)
    6. Bank transfer instructions (if bank transfer)
    """
    
    # Check if this is a first-time donor
    donor = donation.donor
    is_first_time = donor.donations.count() == 1
    
    # 1. Send donation receipt
    send_donation_receipt(donation, prayer_request)
    
    # 2. Send admin notification
    send_admin_notification(donation, is_first_time, prayer_request)
    
    # 3. Send prayer confirmation if prayer request exists
    if prayer_request:
        send_prayer_confirmation(donation, prayer_request)
    
    # 4. Send welcome email if first-time donor
    if is_first_time:
        send_welcome_email(donation)
    
    # 5. Send monthly partner email if monthly donation
    if donation.donation_type == 'monthly':
        send_monthly_partner_email(donation)
    
    # 6. Send bank transfer instructions if bank transfer
    if donation.payment_method == 'bank':
        send_bank_transfer_instructions(donation)


def send_test_email(to_email):
    """Send a test email to verify email configuration"""
    
    subject = "Test Email from Ministry Donation System"
    message = """
This is a test email to verify your email configuration is working correctly.

If you received this email, your SMTP settings are configured properly!

Test Details:
-------------
From: Django Ministry Donation System
Time: Successfully sent
Status: ✅ Working

You can now proceed with confidence that your donation emails will be delivered.
    """
    
    from_email = settings.DEFAULT_FROM_EMAIL
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error sending test email: {str(e)}")
        return False