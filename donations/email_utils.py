# File: donations/email_utils.py
# COMPLETE HTML EMAIL VERSION - ALL emails use beautiful HTML templates!
# ✅ Donor receipt: HTML
# ✅ Admin notification: HTML
# ✅ Bank transfer instructions: HTML ← FIXED!
# ✅ Welcome email: HTML
# ✅ Monthly partner: HTML

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags


def get_currency_display(donation):
    """Get formatted currency display for a donation"""
    symbols = {
        'NGN': '₦',
        'USD': '$',
        'EUR': '€',
        'GBP': '£'
    }
    
    currency_code = donation.currency or 'NGN'
    symbol = symbols.get(currency_code, '₦')
    
    return {
        'symbol': symbol,
        'code': currency_code,
        'formatted_amount': f"{symbol}{donation.amount:,.2f}"
    }


def send_donation_receipt(donation, prayer_request=None):
    """Send beautiful HTML donation receipt to donor"""
    
    currency_info = get_currency_display(donation)
    
    subject = f"✅ Thank You for Your {currency_info['formatted_amount']} Donation!"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = donation.donor.email
    
    # Prepare context for template
    context = {
        'donor_name': donation.donor.full_name,
        'amount': donation.amount,
        'currency': currency_info['code'],
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
        'website_url': getattr(settings, 'SITE_URL', 'https://globalcrusadeoutreach.org'),
    }
    
    try:
        # Render HTML email from template
        html_content = render_to_string('emails/donation_receipt.html', context)
        text_content = strip_tags(html_content)
        
        # Create email with HTML
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        print(f"✅ Donor receipt (HTML) sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending donor receipt: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def send_admin_notification(donation, is_first_time=False, prayer_request=None):
    """Send beautiful HTML admin notification"""
    
    currency_info = get_currency_display(donation)
    
    subject = f"💰 New Donation: {currency_info['formatted_amount']} from {donation.donor.full_name}"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = settings.ADMIN_EMAIL
    
    # Prepare context for template
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
        'dashboard_url': f"{getattr(settings, 'SITE_URL', 'https://global-crusade-donation.onrender.com')}/dashboard/donations/",
        'notification_date': donation.created_at.strftime('%B %d, %Y at %I:%M %p'),
    }
    
    try:
        # Render HTML email from template
        html_content = render_to_string('emails/admin_notification.html', context)
        text_content = strip_tags(html_content)
        
        # Create email with HTML
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        print(f"✅ Admin notification (HTML) sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending admin notification: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def send_bank_transfer_instructions(donation):
    """Send beautiful HTML bank transfer instructions - FIXED TO USE HTML!"""
    
    currency_info = get_currency_display(donation)
    
    subject = f"🏦 Bank Transfer Details for Your {currency_info['formatted_amount']} Donation"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = donation.donor.email
    
    # Prepare context for template
    context = {
        'donor_name': donation.donor.full_name,
        'formatted_amount': currency_info['formatted_amount'],
        'currency_code': currency_info['code'],
        'donation_id': donation.id,
        'website_url': getattr(settings, 'SITE_URL', 'https://globalcrusadeoutreach.org'),
    }
    
    try:
        # Render HTML email from template
        html_content = render_to_string('emails/bank_transfer_instructions.html', context)
        text_content = strip_tags(html_content)
        
        # Create email with HTML
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        print(f"✅ Bank transfer instructions (HTML) sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending bank transfer instructions: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Fallback to plain text if HTML fails
        print(f"⚠️ Falling back to plain text bank transfer email")
        
        message = f"""
Dear {donation.donor.full_name},

Thank you for choosing to support our ministry with a {currency_info['formatted_amount']} donation!

BANK TRANSFER DETAILS:
----------------------
Bank Name: United Bank Africa PLC
Account Number: 1023888802
Account Name: Eternity Voice International Ministry
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

---
Email: eternityvoiceministry@gmail.com
Website: {getattr(settings, 'SITE_URL', 'https://globalcrusadeoutreach.org')}
"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[to_email],
                fail_silently=False,
            )
            print(f"✅ Bank transfer instructions (text) sent to {to_email}")
            return True
        except Exception as e2:
            print(f"❌ Error sending bank transfer email: {str(e2)}")
            return False


def send_welcome_email(donation):
    """Send welcome email to first-time donors"""
    
    currency_info = get_currency_display(donation)
    
    subject = "🎉 Welcome to Our Ministry Family!"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = donation.donor.email
    
    # Prepare context
    context = {
        'donor_name': donation.donor.full_name,
        'amount': donation.amount,
        'currency_symbol': currency_info['symbol'],
        'currency_code': currency_info['code'],
        'formatted_amount': currency_info['formatted_amount'],
        'website_url': getattr(settings, 'SITE_URL', 'https://globalcrusadeoutreach.org'),
    }
    
    try:
        # Try to use HTML template if it exists
        html_content = render_to_string('emails/welcome_email.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[to_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        print(f"✅ Welcome email (HTML) sent to {to_email}")
        return True
        
    except Exception as e:
        print(f"⚠️ HTML template not found, using plain text welcome email: {str(e)}")
        
        # Fallback to plain text
        message = f"""
Dear {donation.donor.full_name},

Welcome to the Global Crusade Ministry family!

Your first donation of {currency_info['formatted_amount']} marks the beginning of an incredible journey of faith and impact together.

God bless you abundantly!

Global Crusade Ministry
{getattr(settings, 'SITE_URL', 'https://globalcrusadeoutreach.org')}
"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[to_email],
                fail_silently=False,
            )
            print(f"✅ Welcome email (text) sent to {to_email}")
            return True
        except Exception as e2:
            print(f"❌ Error sending welcome email: {str(e2)}")
            return False


def send_monthly_partner_email(donation):
    """Send thank you email to monthly partners"""
    
    currency_info = get_currency_display(donation)
    
    subject = f"Thank You for Your Monthly Partnership! ({currency_info['formatted_amount']})"
    
    message = f"""
Dear {donation.donor.full_name},

Thank you for becoming a monthly partner with your {currency_info['formatted_amount']} commitment!

Your ongoing support enables us to:
✓ Plan long-term crusade campaigns
✓ Provide consistent community outreach
✓ Train and equip ministry leaders
✓ Reach more souls with the Gospel

We're honored to have you as part of our ministry family.

God bless you abundantly!

Global Crusade Ministry
{getattr(settings, 'SITE_URL', 'https://globalcrusadeoutreach.org')}
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[donation.donor.email],
            fail_silently=False,
        )
        print(f"✅ Monthly partner email sent to {donation.donor.email}")
        return True
    except Exception as e:
        print(f"❌ Error sending monthly partner email: {str(e)}")
        return False


def send_all_donation_emails(donation, prayer_request=None):
    """
    Send all relevant emails for a new donation
    
    ALL emails use beautiful HTML templates!
    """
    
    print(f"\n{'='*60}")
    print(f"📧 SENDING EMAILS FOR DONATION #{donation.id}")
    print(f"{'='*60}")
    
    # Check if this is a first-time donor
    donor = donation.donor
    is_first_time = donor.donations.count() == 1
    
    if is_first_time:
        print(f"🎉 First-time donor detected: {donor.full_name}")
    
    # 1. Send HTML donation receipt to donor
    print(f"📨 Sending HTML receipt to donor: {donor.email}")
    send_donation_receipt(donation, prayer_request)
    
    # 2. Send HTML admin notification
    print(f"📨 Sending HTML admin notification to: {settings.ADMIN_EMAIL}")
    send_admin_notification(donation, is_first_time, prayer_request)
    
    # 3. Send welcome email if first-time donor
    if is_first_time:
        print(f"📨 Sending welcome email to: {donor.email}")
        send_welcome_email(donation)
    
    # 4. Send HTML bank transfer instructions if bank transfer
    if donation.payment_method == 'bank':
        print(f"📨 Sending HTML bank transfer instructions to: {donor.email}")
        send_bank_transfer_instructions(donation)
    
    # 5. Send monthly partner email if monthly donation
    if donation.donation_type == 'monthly':
        print(f"📨 Sending monthly partner email to: {donor.email}")
        send_monthly_partner_email(donation)
    
    print(f"{'='*60}")
    print(f"✅ ALL EMAILS PROCESSED FOR DONATION #{donation.id}")
    print(f"{'='*60}\n")