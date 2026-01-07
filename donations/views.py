# File: donations/views.py
# COMPLETE VERSION WITH STRIPE + TESTIMONY + ALL EXISTING FEATURES
# - Stripe payment (UK entity)
# - PayPal.me redirect (already working)
# - Bank Transfer (already working)
# - Auto-currency detection
# - Auto-complete donations
# - Email sending
# - Testimony management

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.core.mail import send_mail
from .models import Donation, Donor, CrusadeStats, PrayerRequest, CrusadeFlyer, MinistryImage, Testimony
from .forms import DonationForm
from django.conf import settings
import json
import stripe

# Configure Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')


# ═══════════════════════════════════════════════════════════════
# STRIPE PAYMENT VIEWS (4 functions)
# ═══════════════════════════════════════════════════════════════

@csrf_exempt
def create_stripe_session(request):
    """Create Stripe Checkout Session"""
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    try:
        data = json.loads(request.body)
        amount = float(data.get('amount', 0))
        currency = data.get('currency', 'gbp').lower()
        name = data.get('name', '')
        email = data.get('email', '')
        prayer_request = data.get('prayer_request', '')  # ✅ GET PRAYER REQUEST
        
        if amount < 1:
            return JsonResponse({'error': 'Invalid amount'}, status=400)
        
        # Convert to pence/cents
        stripe_amount = int(amount * 100)
        
        print(f"💰 Creating Stripe session: {currency.upper()} {amount}")
        if prayer_request:
            print(f"🙏 Prayer request included: {prayer_request[:50]}...")
        
        # Create session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': currency,
                    'unit_amount': stripe_amount,
                    'product_data': {
                        'name': 'Global Crusade Ministry Donation',
                        'description': 'Your generous donation helps us bring hope worldwide',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{settings.SITE_URL}/stripe/success/?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{settings.SITE_URL}/stripe/cancel/',
            customer_email=email,
            metadata={
                'donor_name': name,
                'donor_email': email,
                'prayer_request': prayer_request,  # ✅ SAVE PRAYER REQUEST
            }
        )
        
        print(f"✅ Stripe session created: {session.id}")
        
        return JsonResponse({
            'id': session.id,
            'url': session.url
        })
        
    except Exception as e:
        print(f"❌ Error creating Stripe session: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


def stripe_success(request):
    """Stripe payment success"""
    
    session_id = request.GET.get('session_id')
    
    if not session_id:
        messages.error(request, 'Invalid session')
        return redirect('donation_page')
    
    try:
        # Retrieve session
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == 'paid':
            # Check if already recorded
            existing = Donation.objects.filter(payment_reference=session_id).first()
            if existing:
                return render(request, 'donations/stripe_success.html', {
                    'donation': existing
                })
            
            # Extract details
            amount = Decimal(str(session.amount_total / 100))
            currency = session.currency.upper()
            email = session.metadata.get('donor_email', session.customer_email)
            name = session.metadata.get('donor_name', 'Anonymous Donor')
            prayer_request_text = session.metadata.get('prayer_request', '')  # ✅ GET PRAYER REQUEST
            
            # Create donor
            donor, created = Donor.objects.get_or_create(
                email=email,
                defaults={
                    'full_name': name,
                    'country': 'United Kingdom'
                }
            )
            
            # Create donation
            donation = Donation.objects.create(
                donor=donor,
                amount=amount,
                currency=currency,
                donation_type='one-time',
                payment_method='card',
                payment_gateway='stripe',
                payment_reference=session_id,
                status='completed',
                completed_at=timezone.now()
            )
            
            print(f"✅ Stripe donation saved: #{donation.id} - {currency} {amount} from {name}")
            
            # ✅ CREATE PRAYER REQUEST IF PROVIDED
            prayer_request = None
            if prayer_request_text:
                prayer_request = PrayerRequest.objects.create(
                    donor=donor,
                    donation=donation,
                    request_text=prayer_request_text
                )
                print(f"🙏 Prayer request saved: {prayer_request_text[:50]}...")
            
            # Update stats
            stats = CrusadeStats.get_stats()
            stats.update_from_donations()
            
            # Send emails
            try:
                from .email_utils import send_all_donation_emails
                send_all_donation_emails(donation, prayer_request)  # ✅ PASS PRAYER REQUEST
            except Exception as e:
                print(f"⚠️ Error sending emails: {str(e)}")
            
            return render(request, 'donations/stripe_success.html', {
                'donation': donation
            })
        else:
            messages.warning(request, 'Payment not completed')
            return redirect('donation_page')
            
    except Exception as e:
        print(f"❌ Error processing Stripe success: {str(e)}")
        messages.error(request, 'Error processing payment')
        return redirect('donation_page')


def stripe_cancel(request):
    """Stripe payment cancelled"""
    messages.warning(request, 'Your payment was cancelled.')
    return redirect('donation_page')


@csrf_exempt
def stripe_webhook(request):
    """Stripe webhook handler"""
    
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    
    if not webhook_secret:
        return JsonResponse({'status': 'no_webhook_secret'})
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        
        print(f"🔔 Stripe webhook: {event['type']}")
        
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            
            # Check if exists
            existing = Donation.objects.filter(payment_reference=session.id).first()
            if existing:
                return JsonResponse({'status': 'already_processed'})
            
            # Process payment
            amount = Decimal(str(session.amount_total / 100))
            currency = session.currency.upper()
            email = session.metadata.get('donor_email', session.customer_email)
            name = session.metadata.get('donor_name', 'Anonymous Donor')
            prayer_request_text = session.metadata.get('prayer_request', '')  # ✅ GET PRAYER REQUEST
            
            donor, created = Donor.objects.get_or_create(
                email=email,
                defaults={
                    'full_name': name,
                    'country': 'United Kingdom'
                }
            )
            
            donation = Donation.objects.create(
                donor=donor,
                amount=amount,
                currency=currency,
                donation_type='one-time',
                payment_method='card',
                payment_gateway='stripe',
                payment_reference=session.id,
                status='completed',
                completed_at=timezone.now()
            )
            
            # ✅ CREATE PRAYER REQUEST IF PROVIDED
            prayer_request = None
            if prayer_request_text:
                prayer_request = PrayerRequest.objects.create(
                    donor=donor,
                    donation=donation,
                    request_text=prayer_request_text
                )
                print(f"🙏 Prayer request saved from webhook: {prayer_request_text[:50]}...")
            
            # Update stats
            stats = CrusadeStats.get_stats()
            stats.update_from_donations()
            
            # Send emails
            try:
                from .email_utils import send_all_donation_emails
                send_all_donation_emails(donation, prayer_request)  # ✅ PASS PRAYER REQUEST
            except Exception as e:
                print(f"⚠️ Error sending emails: {str(e)}")
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        print(f"❌ Webhook error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ═══════════════════════════════════════════════════
# CURRENCY AUTO-DETECTION
# ═══════════════════════════════════════════════════

def auto_detect_currency(amount, payment_method, country=None, donor_email=None):
    """Auto-detect currency based on payment method and context"""
    
    if payment_method == 'bank':
        return 'NGN'
    
    if amount >= 10000:
        return 'NGN'
    
    if country:
        country_lower = country.lower()
        if 'nigeria' in country_lower or 'ng' in country_lower:
            return 'NGN'
        elif any(eu_country in country_lower for eu_country in ['france', 'germany', 'spain', 'italy']):
            return 'EUR'
        elif 'uk' in country_lower or 'britain' in country_lower:
            return 'GBP'
    
    if donor_email:
        email_lower = donor_email.lower()
        if email_lower.endswith(('.ng', '.com.ng')):
            return 'NGN'
        elif email_lower.endswith('.uk'):
            return 'GBP'
    
    return 'USD'


def get_multi_currency_totals(donations):
    """Calculate totals per currency"""
    currency_totals = {}
    symbols = {'NGN': '₦', 'USD': '$', 'EUR': '€', 'GBP': '£'}
    
    for donation in donations:
        currency_code = donation.currency or 'NGN'
        
        if currency_code not in currency_totals:
            currency_totals[currency_code] = {
                'total': Decimal('0.00'),
                'symbol': symbols.get(currency_code, '₦'),
                'count': 0
            }
        
        currency_totals[currency_code]['total'] += donation.amount
        currency_totals[currency_code]['count'] += 1
    
    return currency_totals


# ============================================
# PUBLIC DONATION PAGES
# ============================================

def donation_page(request):
    """Main donation page"""
    
    stats = CrusadeStats.get_stats()
    crusade_flyers = CrusadeFlyer.objects.filter(is_active=True)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'bank')
        payment_gateway = request.POST.get('payment_gateway', 'bank')
        donation_type = request.POST.get('donation_type', 'one-time')
        amount_str = request.POST.get('amount')
        transaction_reference = request.POST.get('transaction_reference', '')
        
        # Get donor info
        if payment_method in ['bank', 'paypal']:
            email = request.POST.get('quick_email', request.POST.get('email', ''))
            full_name = request.POST.get('quick_name', request.POST.get('full_name', ''))
            phone = ''
            country = request.POST.get('country', 'Nigeria')
            message = request.POST.get('message', '')  # ✅ FIXED!
        else:
            email = request.POST.get('email', '')
            full_name = request.POST.get('full_name', '')
            phone = request.POST.get('phone', '')
            country = request.POST.get('country', '')
            message = request.POST.get('message', '')
        
        # Validate
        if not all([amount_str, email, full_name]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('donation_page')
        
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except (ValueError, TypeError):
            messages.error(request, 'Please enter a valid donation amount.')
            return redirect('donation_page')
        
        # Auto-detect currency
        currency = request.POST.get('currency', '')
        if not currency:
            currency = auto_detect_currency(amount, payment_method, country, email)
        
        # Create donor
        donor, created = Donor.objects.get_or_create(
            email=email,
            defaults={
                'full_name': full_name,
                'phone': phone,
                'country': country
            }
        )
        
        if not created:
            donor.full_name = full_name
            if phone:
                donor.phone = phone
            if country and country != 'Other':
                donor.country = country
            donor.save()
        
        # Create donation
        donation = Donation.objects.create(
            donor=donor,
            amount=amount,
            currency=currency,
            donation_type=donation_type,
            payment_method=payment_method,
            payment_gateway=payment_gateway,
            message=message,
            status='completed',
            completed_at=timezone.now()
        )
        
        if transaction_reference:
            donation.payment_reference = transaction_reference
        donation.save()
        
        # Update stats
        stats = CrusadeStats.get_stats()
        stats.update_from_donations()
        
        # Create prayer request
        prayer_request = None
        if message:
            prayer_request = PrayerRequest.objects.create(
                donor=donor,
                donation=donation,
                request_text=message
            )
        
        # Send emails
        try:
            from .email_utils import send_all_donation_emails
            send_all_donation_emails(donation, prayer_request)
        except Exception as e:
            print(f"❌ EMAIL ERROR: {e}")
        
        # Route based on payment method
        if payment_method == 'paypal':
            return redirect('process_paypal', donation_id=donation.id)
        elif payment_method == 'card':
            return redirect('process_payment', donation_id=donation.id)
        else:
            return redirect('bank_transfer_confirmation', donation_id=donation.id)
    
    context = {
        'form': DonationForm(),
        'stats': stats,
        'crusade_flyers': crusade_flyers,
        'stripe_public_key': getattr(settings, 'STRIPE_PUBLIC_KEY', ''),  # ✅ ADDED!
    }
    
    return render(request, 'donations/donation_page.html', context)


def bank_transfer_confirmation(request, donation_id):
    """Bank transfer confirmation page"""
    donation = get_object_or_404(Donation, id=donation_id)
    return render(request, 'donations/bank_transfer_confirmation.html', {
        'donation': donation,
    })


def process_paypal(request, donation_id):
    """PayPal.me redirect"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    paypal_username = getattr(settings, 'PAYPAL_ME_USERNAME', 'eternityvoice')
    amount = donation.amount
    currency_code = donation.currency or 'USD'
    paypal_url = f"https://paypal.me/{paypal_username}/{amount}{currency_code}"
    
    return redirect(paypal_url)


def donation_success(request, donation_id):
    """Donation success page"""
    donation = get_object_or_404(Donation, id=donation_id)
    return render(request, 'donations/success.html', {
        'donation': donation,
    })


@login_required
def manual_payment_verify(request, donation_id):
    """Admin manual verification"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    if request.method == 'POST':
        if donation.status != 'completed':
            donation.status = 'completed'
            donation.completed_at = timezone.now()
            donation.save()
            
            stats = CrusadeStats.get_stats()
            stats.update_from_donations()
            
            messages.success(request, f'Donation from {donation.donor.full_name} marked as completed!')
        else:
            messages.info(request, f'Donation from {donation.donor.full_name} is already completed.')
    
    return redirect('donations_list')


@login_required
def delete_donation(request, donation_id):
    """Delete donation"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    if request.method == 'POST':
        donor_name = donation.donor.full_name
        donor = donation.donor
        
        donation.delete()
        
        remaining_donations = donor.donations.count()
        
        if remaining_donations == 0:
            donor.delete()
            messages.success(request, f'Donation deleted. {donor_name} removed (no donations left).')
        else:
            messages.success(request, f'Donation deleted. {donor_name} has {remaining_donations} donation(s) remaining.')
        
        stats = CrusadeStats.get_stats()
        stats.update_from_donations()
        
        return redirect('donations_list')
    
    return redirect('donations_list')


# ============================================
# ADMIN DASHBOARD VIEWS
# ============================================

@login_required
def admin_dashboard(request):
    """Admin dashboard"""
    
    completed_donations = Donation.objects.filter(status='completed')
    currency_totals = get_multi_currency_totals(completed_donations)
    
    stats = {
        'total_donations': completed_donations.count(),
        'total_donors': Donor.objects.count(),
        'pending_donations': Donation.objects.filter(status='pending').count(),
        'prayer_requests': PrayerRequest.objects.filter(is_answered=False).count(),
    }
    
    recent_donations_qs = Donation.objects.select_related('donor').order_by('-created_at')[:10]
    recent_donations = []
    symbols = {'NGN': '₦', 'USD': '$', 'EUR': '€', 'GBP': '£'}
    
    for donation in recent_donations_qs:
        currency_code = donation.currency or 'NGN'
        symbol = symbols.get(currency_code, '₦')
        donation.currency_code = currency_code
        donation.currency_symbol = symbol
        donation.formatted_amount = f"{symbol}{donation.amount:,.2f}"
        recent_donations.append(donation)
    
    all_donors = Donor.objects.all()
    donors_with_totals = []
    for donor in all_donors:
        total = donor.total_donated
        if total > 0:
            donors_with_totals.append({'donor': donor, 'total': total})
    top_donors = sorted(donors_with_totals, key=lambda x: x['total'], reverse=True)[:10]
    
    recent_prayers = PrayerRequest.objects.select_related('donor').order_by('-created_at')[:5]
    crusade_stats = CrusadeStats.get_stats()
    
    context = {
        'stats': stats,
        'currency_totals': currency_totals,
        'recent_donations': recent_donations,
        'top_donors': top_donors,
        'recent_prayers': recent_prayers,
        'crusade_stats': crusade_stats,
    }
    
    return render(request, 'admin_dashboard/dashboard.html', context)


@login_required
def donors_list(request):
    """List all donors"""
    all_donors = Donor.objects.all().order_by('-created_at')
    symbols = {'NGN': '₦', 'USD': '$', 'EUR': '€', 'GBP': '£'}
    
    donors_with_stats = []
    active_count = 0
    
    for donor in all_donors:
        completed_donations = donor.donations.filter(status='completed')
        donation_count = completed_donations.count()
        
        currency_totals = {}
        for donation in completed_donations:
            currency_code = donation.currency or 'NGN'
            if currency_code not in currency_totals:
                currency_totals[currency_code] = {
                    'total': Decimal('0.00'),
                    'symbol': symbols.get(currency_code, '₦')
                }
            currency_totals[currency_code]['total'] += donation.amount
        
        primary_currency = 'NGN'
        primary_total = Decimal('0.00')
        primary_symbol = '₦'
        
        if currency_totals:
            primary_currency = max(currency_totals.items(), key=lambda x: x[1]['total'])[0]
            primary_total = currency_totals[primary_currency]['total']
            primary_symbol = currency_totals[primary_currency]['symbol']
        
        primary_amount = f"{primary_symbol}{primary_total:,.2f}"
        
        if donation_count > 0:
            active_count += 1
        
        donors_with_stats.append({
            'donor': donor,
            'donation_count': donation_count,
            'currency_breakdown': currency_totals,
            'primary_currency': primary_currency,
            'primary_amount': primary_amount,
            'primary_total': primary_total,
        })
    
    donors_with_stats.sort(key=lambda x: x['primary_total'], reverse=True)
    
    context = {
        'donors': donors_with_stats,
        'total_donors': all_donors.count(),
        'active_donors': active_count,
    }
    
    return render(request, 'admin_dashboard/donors_list.html', context)


@login_required
def donations_list(request):
    """List all donations"""
    status_filter = request.GET.get('status', 'all')
    donations_qs = Donation.objects.select_related('donor').order_by('-created_at')
    
    if status_filter != 'all':
        donations_qs = donations_qs.filter(status=status_filter)
    
    donations = []
    symbols = {'NGN': '₦', 'USD': '$', 'EUR': '€', 'GBP': '£'}
    
    for donation in donations_qs:
        currency_code = donation.currency or 'NGN'
        symbol = symbols.get(currency_code, '₦')
        donation.currency_code = currency_code
        donation.currency_symbol = symbol
        donation.formatted_amount = f"{symbol}{donation.amount:,.2f}"
        donations.append(donation)
    
    context = {
        'donations': donations,
        'status_filter': status_filter,
    }
    return render(request, 'admin_dashboard/donations_list.html', context)


@login_required
def prayer_requests_list(request):
    """List prayer requests"""
    prayer_requests_qs = PrayerRequest.objects.select_related('donor', 'donation').order_by('-created_at')
    
    # Add currency symbols
    symbols = {'NGN': '₦', 'USD': '$', 'EUR': '€', 'GBP': '£'}
    prayer_requests = []
    
    for prayer in prayer_requests_qs:
        if prayer.donation:
            currency_code = prayer.donation.currency or 'NGN'
            symbol = symbols.get(currency_code, '₦')
            amount = prayer.donation.amount
        else:
            currency_code = 'NGN'
            symbol = '₦'
            amount = 0
        
        prayer.currency_code = currency_code
        prayer.currency_symbol = symbol
        prayer.formatted_amount = f"{symbol}{amount:,.2f}" if amount > 0 else "N/A"
        prayer_requests.append(prayer)
    
    context = {
        'prayer_requests': prayer_requests,
        'total_count': len(prayer_requests),
        'unanswered_count': prayer_requests_qs.filter(is_answered=False).count(),
        'answered_count': prayer_requests_qs.filter(is_answered=True).count(),
    }
    return render(request, 'admin_dashboard/prayer_requests.html', context)


@login_required
def mark_prayer_answered(request, prayer_id):
    """Toggle prayer answered status"""
    prayer = get_object_or_404(PrayerRequest, id=prayer_id)
    prayer.is_answered = not prayer.is_answered
    if prayer.is_answered:
        prayer.answered_at = timezone.now()
    else:
        prayer.answered_at = None
    prayer.save()
    messages.success(request, 'Prayer request updated.')
    return redirect('prayer_requests_list')


@login_required
def update_crusade_stats(request):
    """Update crusade statistics"""
    if request.method == 'POST':
        stats = CrusadeStats.get_stats()
        stats.budgeted_amount = request.POST.get('budgeted_amount', stats.budgeted_amount)
        stats.crusades_planned = request.POST.get('crusades_planned', stats.crusades_planned)
        stats.save()
        stats.update_from_donations()
        messages.success(request, 'Crusade statistics updated!')
        return redirect('admin_dashboard')
    return redirect('admin_dashboard')


@login_required
def export_donors_csv(request):
    """Export donors CSV"""
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="donors.csv"'
    writer = csv.writer(response)
    writer.writerow(['Full Name', 'Email', 'Phone', 'Country', 'Total Donated', 'Donations Count', 'Joined Date'])
    
    donors = Donor.objects.all()
    for donor in donors:
        total = donor.total_donated
        count = donor.donations.filter(status='completed').count()
        writer.writerow([
            donor.full_name,
            donor.email,
            donor.phone or '',
            donor.country,
            total,
            count,
            donor.created_at.strftime('%Y-%m-%d')
        ])
    return response


@login_required
def export_donations_csv(request):
    """Export donations CSV"""
    import csv
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="donations.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Donor Name', 'Email', 'Amount', 'Currency', 'Gateway', 'Type', 'Payment Method', 'Status', 'Reference'])
    
    donations = Donation.objects.select_related('donor').order_by('-created_at')
    for donation in donations:
        writer.writerow([
            donation.created_at.strftime('%Y-%m-%d %H:%M'),
            donation.donor.full_name,
            donation.donor.email,
            donation.amount,
            donation.currency or 'NGN',
            donation.get_payment_gateway_display(),
            donation.get_donation_type_display(),
            donation.get_payment_method_display(),
            donation.get_status_display(),
            donation.payment_reference or ''
        ])
    return response


@login_required
def dashboard_logout(request):
    """Logout"""
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('donation_page')


def custom_login(request):
    """Custom login"""
    from django.contrib.auth import authenticate, login
    
    if request.user.is_authenticated:
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'admin_dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'admin_dashboard/login.html')


@login_required
def dashboard_settings(request):
    """Dashboard settings"""
    stats = CrusadeStats.get_stats()
    crusade_flyers = CrusadeFlyer.objects.all().order_by('display_order', '-created_at')
    
    ministry_images = {
        'hero': MinistryImage.objects.filter(image_type='hero'),
        'about': MinistryImage.objects.filter(image_type='about'),
        'crusade': MinistryImage.objects.filter(image_type='crusade'),
        'testimony': MinistryImage.objects.filter(image_type='testimony'),
        'gallery': MinistryImage.objects.filter(image_type='gallery'),
    }
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_stats':
            try:
                stats.budgeted_amount = Decimal(request.POST.get('budgeted_amount', stats.budgeted_amount))
                stats.crusades_planned = int(request.POST.get('crusades_planned', stats.crusades_planned))
                stats.countries_list = request.POST.get('countries_list', stats.countries_list)
                stats.save()
                stats.update_from_donations()
                messages.success(request, 'Settings updated successfully!')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid input. Please check your values.')
        
        elif action == 'upload_flyer':
            try:
                title = request.POST.get('flyer_title')
                description = request.POST.get('flyer_description', '')
                image = request.FILES.get('flyer_image')
                
                if title and image:
                    CrusadeFlyer.objects.create(
                        title=title,
                        description=description,
                        image=image,
                        is_active=True
                    )
                    messages.success(request, 'Crusade flyer uploaded successfully!')
                else:
                    messages.error(request, 'Please provide both title and image.')
            except Exception as e:
                messages.error(request, f'Error uploading flyer: {str(e)}')
        
        elif action == 'delete_flyer':
            flyer_id = request.POST.get('flyer_id')
            try:
                flyer = CrusadeFlyer.objects.get(id=flyer_id)
                flyer.delete()
                messages.success(request, 'Flyer deleted successfully!')
            except CrusadeFlyer.DoesNotExist:
                messages.error(request, 'Flyer not found.')
        
        elif action == 'toggle_flyer':
            flyer_id = request.POST.get('flyer_id')
            try:
                flyer = CrusadeFlyer.objects.get(id=flyer_id)
                flyer.is_active = not flyer.is_active
                flyer.save()
                status = "activated" if flyer.is_active else "deactivated"
                messages.success(request, f'Flyer {status} successfully!')
            except CrusadeFlyer.DoesNotExist:
                messages.error(request, 'Flyer not found.')
        
        elif action == 'upload_ministry_image':
            try:
                title = request.POST.get('image_title')
                description = request.POST.get('image_description', '')
                image_type = request.POST.get('image_type')
                image = request.FILES.get('ministry_image')
                
                if title and image and image_type:
                    MinistryImage.objects.create(
                        title=title,
                        description=description,
                        image=image,
                        image_type=image_type,
                        is_active=True
                    )
                    messages.success(request, f'✅ {title} uploaded successfully!')
                else:
                    messages.error(request, 'Please provide title, image type, and image file.')
            except Exception as e:
                messages.error(request, f'Error uploading image: {str(e)}')
        
        elif action == 'delete_ministry_image':
            image_id = request.POST.get('image_id')
            try:
                image = MinistryImage.objects.get(id=image_id)
                image.delete()
                messages.success(request, 'Image deleted successfully!')
            except MinistryImage.DoesNotExist:
                messages.error(request, 'Image not found.')
        
        elif action == 'toggle_ministry_image':
            image_id = request.POST.get('image_id')
            try:
                image = MinistryImage.objects.get(id=image_id)
                image.is_active = not image.is_active
                image.save()
                status = "activated" if image.is_active else "deactivated"
                messages.success(request, f'Image {status} successfully!')
            except MinistryImage.DoesNotExist:
                messages.error(request, 'Image not found.')
        
        elif action == 'add_testimony':
            try:
                name = request.POST.get('testimony_name')
                location = request.POST.get('testimony_location')
                text = request.POST.get('testimony_text')
                display_order = request.POST.get('display_order', 0)
                
                if name and location and text:
                    Testimony.objects.create(
                        name=name,
                        location=location,
                        testimony_text=text,
                        display_order=int(display_order),
                        is_active=True
                    )
                    messages.success(request, f'✅ Testimony from {name} added successfully!')
                else:
                    messages.error(request, 'Please fill all required fields.')
            except Exception as e:
                messages.error(request, f'Error adding testimony: {str(e)}')
        
        elif action == 'edit_testimony':
            testimony_id = request.POST.get('testimony_id')
            try:
                testimony = Testimony.objects.get(id=testimony_id)
                testimony.name = request.POST.get('testimony_name')
                testimony.location = request.POST.get('testimony_location')
                testimony.testimony_text = request.POST.get('testimony_text')
                testimony.display_order = int(request.POST.get('display_order', 0))
                testimony.save()
                messages.success(request, f'✅ Testimony from {testimony.name} updated!')
            except Testimony.DoesNotExist:
                messages.error(request, 'Testimony not found.')
            except Exception as e:
                messages.error(request, f'Error updating testimony: {str(e)}')
        
        elif action == 'delete_testimony':
            testimony_id = request.POST.get('testimony_id')
            try:
                testimony = Testimony.objects.get(id=testimony_id)
                name = testimony.name
                testimony.delete()
                messages.success(request, f'✅ Testimony from {name} deleted!')
            except Testimony.DoesNotExist:
                messages.error(request, 'Testimony not found.')
            except Exception as e:
                messages.error(request, f'Error deleting testimony: {str(e)}')
        
        elif action == 'toggle_testimony':
            testimony_id = request.POST.get('testimony_id')
            try:
                testimony = Testimony.objects.get(id=testimony_id)
                testimony.is_active = not testimony.is_active
                testimony.save()
                status = "activated" if testimony.is_active else "deactivated"
                messages.success(request, f'✅ Testimony {status}!')
            except Testimony.DoesNotExist:
                messages.error(request, 'Testimony not found.')
            except Exception as e:
                messages.error(request, f'Error toggling testimony: {str(e)}')
        
        return redirect('dashboard_settings')
    
    testimonies = Testimony.objects.all().order_by('display_order', '-created_at')
    
    context = {
        'stats': stats,
        'crusade_flyers': crusade_flyers,
        'ministry_images': ministry_images,
        'testimonies': testimonies,
    }
    return render(request, 'admin_dashboard/settings.html', context)


# ============================================
# MINISTRY PUBLIC PAGES
# ============================================

def ministry_home(request):
    """Homepage"""
    context = {
        'hero_image': MinistryImage.objects.filter(image_type='hero', is_active=True).first(),
        'gallery_images': MinistryImage.objects.filter(image_type='gallery', is_active=True)[:6],
    }
    return render(request, 'ministry/home.html', context)

def ministry_about(request):
    """About page"""
    context = {
        'about_images': MinistryImage.objects.filter(image_type='about', is_active=True),
    }
    return render(request, 'ministry/about.html', context)

def ministry_crusades(request):
    """Crusades page"""
    context = {
        'crusade_images': MinistryImage.objects.filter(image_type='crusade', is_active=True),
    }
    return render(request, 'ministry/crusades.html', context)

def ministry_testimonies(request):
    """Testimonies page"""
    context = {
        'testimony_images': MinistryImage.objects.filter(image_type='testimony', is_active=True),
        'testimonies': Testimony.objects.filter(is_active=True),
    }
    return render(request, 'ministry/testimonies.html', context)

def ministry_contact(request):
    """Contact page"""
    if request.method == 'POST':
        first_name = request.POST.get('firstName', '')
        last_name = request.POST.get('lastName', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        subject = request.POST.get('subject', '')
        message = request.POST.get('message', '')
        
        full_name = f"{first_name} {last_name}"
        
        email_subject = f"Contact Form: {subject}"
        email_body = f"""
New Contact Form Submission from Ministry Website

Name: {full_name}
Email: {email}
Phone: {phone}
Subject: {subject}

Message:
{message}

---
Sent from Global Crusade Ministry Contact Form
        """
        
        try:
            send_mail(
                email_subject,
                email_body,
                settings.EMAIL_HOST_USER,
                ['eternityvoiceministry@gmail.com'],
                fail_silently=False,
            )
            
            context = {
                'success': True,
                'name': full_name
            }
            return render(request, 'ministry/contact.html', context)
            
        except Exception as e:
            context = {
                'error': True,
                'message': 'Sorry, there was an error sending your message. Please try again or email us directly.'
            }
            return render(request, 'ministry/contact.html', context)
    
    return render(request, 'ministry/contact.html')