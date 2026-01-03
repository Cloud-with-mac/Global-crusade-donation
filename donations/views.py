# File: donations/views.py
# COMPLETE VERSION WITH TESTIMONY MANAGEMENT
# - Auto-detects correct currency (NGN, USD, EUR, GBP)
# - Auto-completes all donations immediately (no pending status)
# - Auto-deletes donors when they have no donations left
# - ⭐ TESTIMONY MANAGEMENT INCLUDED
# - Updates dashboard totals automatically
# - Sends emails immediately

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.core.mail import send_mail
from .models import Donation, Donor, CrusadeStats, PrayerRequest, CrusadeFlyer, MinistryImage, Testimony  # ⭐ TESTIMONY ADDED
from .forms import DonationForm
from django.conf import settings




# ═══════════════════════════════════════════════════
# CURRENCY AUTO-DETECTION
# ═══════════════════════════════════════════════════

def auto_detect_currency(amount, payment_method, country=None, donor_email=None):
    """
    Automatically detect the correct currency based on:
    1. Payment method (bank transfer in Nigeria = NGN)
    2. Amount patterns (large amounts in Nigeria = NGN)
    3. Country
    4. Donor location hints
    """
    
    # Rule 1: Bank transfers in Nigeria are always NGN
    if payment_method == 'bank':
        return 'NGN'
    
    # Rule 2: Large amounts (>10,000) are typically NGN
    if amount >= 10000:
        return 'NGN'
    
    # Rule 3: Country-based detection
    if country:
        country_lower = country.lower()
        if 'nigeria' in country_lower or 'ng' in country_lower:
            return 'NGN'
        elif any(eu_country in country_lower for eu_country in ['france', 'germany', 'spain', 'italy', 'netherlands', 'belgium']):
            return 'EUR'
        elif 'uk' in country_lower or 'britain' in country_lower or 'england' in country_lower:
            return 'GBP'
    
    # Rule 4: Email domain hints
    if donor_email:
        email_lower = donor_email.lower()
        if email_lower.endswith(('.ng', '.com.ng')):
            return 'NGN'
        elif email_lower.endswith(('.eu', '.fr', '.de', '.es', '.it')):
            return 'EUR'
        elif email_lower.endswith('.uk'):
            return 'GBP'
    
    # Rule 5: Default to USD for international/unknown
    return 'USD'


# ═══════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════

def get_multi_currency_totals(donations):
    """Calculate totals per currency from completed donations"""
    currency_totals = {}
    
    symbols = {
        'NGN': '₦',
        'USD': '$',
        'EUR': '€',
        'GBP': '£'
    }
    
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
    """Main donation page with AUTO-CURRENCY + AUTO-COMPLETE"""
    
    stats = CrusadeStats.get_stats()
    crusade_flyers = CrusadeFlyer.objects.filter(is_active=True)
    
    if request.method == 'POST':
        # Get form data
        payment_method = request.POST.get('payment_method', 'bank')
        payment_gateway = request.POST.get('payment_gateway', 'paystack')
        donation_type = request.POST.get('donation_type', 'one-time')
        amount_str = request.POST.get('amount')
        transaction_reference = request.POST.get('transaction_reference', '')
        
        # Get donor info
        if payment_method in ['bank', 'paypal']:
            email = request.POST.get('quick_email', request.POST.get('email', ''))
            full_name = request.POST.get('quick_name', request.POST.get('full_name', ''))
            phone = ''
            country = request.POST.get('country', 'Nigeria')
            message = ''
        else:
            email = request.POST.get('email', '')
            full_name = request.POST.get('full_name', '')
            phone = request.POST.get('phone', '')
            country = request.POST.get('country', '')
            message = request.POST.get('message', '')
        
        # Validate required fields
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
        
        # ⭐ AUTO-DETECT CURRENCY
        currency = request.POST.get('currency', '')
        
        if not currency:
            currency = auto_detect_currency(
                amount=amount,
                payment_method=payment_method,
                country=country,
                donor_email=email
            )
            print(f"🔍 Auto-detected currency: {currency} (Amount: {amount}, Method: {payment_method}, Country: {country})")
        
        # Create or get donor
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
        
        # ⭐ CREATE DONATION AS COMPLETED IMMEDIATELY
        donation = Donation.objects.create(
            donor=donor,
            amount=amount,
            currency=currency,
            donation_type=donation_type,
            payment_method=payment_method,
            payment_gateway=payment_gateway,
            message=message,
            status='completed',  # ✅ AUTO-COMPLETE!
            completed_at=timezone.now()  # ✅ SET TIMESTAMP!
        )
        
        if transaction_reference:
            donation.payment_reference = transaction_reference
        
        donation.save()
        
        # Log what was saved
        symbols = {'NGN': '₦', 'USD': '$', 'EUR': '€', 'GBP': '£'}
        symbol = symbols.get(currency, '₦')
        print(f"✅ Donation auto-completed: ID={donation.id}, Amount={symbol}{amount:,.2f}, Currency={currency}, Status=completed")
        
        # ⭐ AUTO-UPDATE STATS IMMEDIATELY
        stats = CrusadeStats.get_stats()
        stats.update_from_donations()
        print(f"✅ Dashboard stats updated automatically!")
        
        # Create prayer request if message provided
        prayer_request = None
        if message:
            prayer_request = PrayerRequest.objects.create(
                donor=donor,
                donation=donation,
                request_text=message
            )
        
        # ⭐ SEND ALL EMAILS IMMEDIATELY
        try:
            from .email_utils import send_all_donation_emails
            send_all_donation_emails(donation, prayer_request)
            print(f"✅ Confirmation emails sent!")
        except Exception as e:
            print(f"⚠️ Email sending failed: {e}")
            pass
        
        # Route based on payment method
        if payment_method == 'paypal':
            return redirect('process_paypal', donation_id=donation.id)
        elif payment_method == 'card':
            return redirect('process_payment', donation_id=donation.id)
        else:
            return redirect('bank_transfer_confirmation', donation_id=donation.id)
    
    else:
        form = DonationForm()
    
    context = {
        'form': form,
        'stats': stats,
        'crusade_flyers': crusade_flyers,
    }
    
    return render(request, 'donations/donation_page.html', context)


def bank_transfer_confirmation(request, donation_id):
    """Confirmation page for bank transfer donations"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    context = {
        'donation': donation,
    }
    return render(request, 'donations/bank_transfer_confirmation.html', context)


def process_paypal(request, donation_id):
    """Process PayPal payment - PayPal.me redirect"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    paypal_username = getattr(settings, 'PAYPAL_ME_USERNAME', 'eternityvoice')
    
    amount = donation.amount
    currency_code = donation.currency or 'USD'
    paypal_url = f"https://paypal.me/{paypal_username}/{amount}{currency_code}"
    
    return redirect(paypal_url)


def donation_success(request, donation_id):
    """Donation success page"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    context = {
        'donation': donation,
    }
    return render(request, 'donations/success.html', context)


@login_required
def manual_payment_verify(request, donation_id):
    """
    Admin manually verifies a donation (legacy - all donations auto-complete now)
    Kept for backwards compatibility
    """
    donation = get_object_or_404(Donation, id=donation_id)
    
    if request.method == 'POST':
        # If somehow a donation is still pending, mark it completed
        if donation.status != 'completed':
            donation.status = 'completed'
            donation.completed_at = timezone.now()
            donation.save()
            
            # Update stats
            stats = CrusadeStats.get_stats()
            stats.update_from_donations()
            
            messages.success(request, f'Donation from {donation.donor.full_name} marked as completed!')
        else:
            messages.info(request, f'Donation from {donation.donor.full_name} is already completed.')
    
    return redirect('donations_list')


@login_required
def delete_donation(request, donation_id):
    """Delete a donation and auto-delete donor if they have no more donations"""
    donation = get_object_or_404(Donation, id=donation_id)
    
    if request.method == 'POST':
        donor_name = donation.donor.full_name
        donor = donation.donor  # ✅ Save reference to donor BEFORE deleting donation
        
        # Delete the donation
        donation.delete()
        
        # ✅ AUTO-DELETE DONOR IF NO DONATIONS LEFT
        remaining_donations = donor.donations.count()
        
        if remaining_donations == 0:
            # Donor has no more donations, delete them
            donor.delete()
            messages.success(request, f'Donation deleted. {donor_name} removed (no donations left).')
            print(f"✅ Auto-deleted donor: {donor_name} (0 donations remaining)")
        else:
            # Donor still has donations, keep them
            messages.success(request, f'Donation deleted. {donor_name} has {remaining_donations} donation(s) remaining.')
            print(f"✅ Kept donor: {donor_name} ({remaining_donations} donations remaining)")
        
        # Update stats after deletion
        stats = CrusadeStats.get_stats()
        stats.update_from_donations()
        
        return redirect('donations_list')
    
    return redirect('donations_list')


# ============================================
# ADMIN DASHBOARD VIEWS
# ============================================

@login_required
def admin_dashboard(request):
    """Custom admin dashboard view - CURRENCY AWARE"""
    
    completed_donations = Donation.objects.filter(status='completed')
    
    # Multi-currency totals
    currency_totals = get_multi_currency_totals(completed_donations)
    
    # Calculate statistics
    stats = {
        'total_donations': completed_donations.count(),
        'total_donors': Donor.objects.count(),
        'pending_donations': Donation.objects.filter(status='pending').count(),
        'prayer_requests': PrayerRequest.objects.filter(is_answered=False).count(),
    }
    
    # Recent donations with currency info
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
    
    # Top donors
    all_donors = Donor.objects.all()
    donors_with_totals = []
    for donor in all_donors:
        total = donor.total_donated
        if total > 0:
            donors_with_totals.append({
                'donor': donor,
                'total': total
            })
    top_donors = sorted(donors_with_totals, key=lambda x: x['total'], reverse=True)[:10]
    
    # Recent prayer requests
    recent_prayers = PrayerRequest.objects.select_related('donor').order_by('-created_at')[:5]
    
    # Get crusade stats
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
    """List all donors - CURRENCY AWARE WITH MULTI-CURRENCY BREAKDOWN"""
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
    """List all donations - CURRENCY AWARE"""
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
    """List all prayer requests"""
    prayer_requests = PrayerRequest.objects.select_related('donor').order_by('-created_at')
    
    total_count = prayer_requests.count()
    unanswered_count = prayer_requests.filter(is_answered=False).count()
    answered_count = prayer_requests.filter(is_answered=True).count()
    
    context = {
        'prayer_requests': prayer_requests,
        'total_count': total_count,
        'unanswered_count': unanswered_count,
        'answered_count': answered_count,
    }
    return render(request, 'admin_dashboard/prayer_requests.html', context)


@login_required
def mark_prayer_answered(request, prayer_id):
    """Mark a prayer request as answered"""
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
    """Export donors to CSV"""
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
    """Export donations to CSV - CURRENCY AWARE"""
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
    """Logout from dashboard"""
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('donation_page')


def custom_login(request):
    """Custom login page for dashboard"""
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
    """Dashboard settings page with ministry image uploads AND TESTIMONY MANAGEMENT"""
    stats = CrusadeStats.get_stats()
    crusade_flyers = CrusadeFlyer.objects.all().order_by('display_order', '-created_at')
    
    # ⭐ GET MINISTRY IMAGES BY TYPE
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
        
        # ⭐ MINISTRY IMAGE HANDLERS
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
        
        # ═══════════════════════════════════════════════════════════════
        # ⭐⭐⭐ TESTIMONY HANDLERS - ADDED! ⭐⭐⭐
        # ═══════════════════════════════════════════════════════════════
        
        # Add Testimony
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
        
        # Edit Testimony
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
        
        # Delete Testimony
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
        
        # Toggle Testimony Active Status
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
    
    # ⭐ GET TESTIMONIES FOR CONTEXT
    testimonies = Testimony.objects.all().order_by('display_order', '-created_at')
    
    context = {
        'stats': stats,
        'crusade_flyers': crusade_flyers,
        'ministry_images': ministry_images,
        'testimonies': testimonies,  # ⭐ TESTIMONY ADDED!
    }
    return render(request, 'admin_dashboard/settings.html', context)


# ============================================
# MINISTRY PUBLIC PAGES
# ============================================

def ministry_home(request):
    """Homepage with uploaded images"""
    context = {
        'hero_image': MinistryImage.objects.filter(image_type='hero', is_active=True).first(),
        'gallery_images': MinistryImage.objects.filter(image_type='gallery', is_active=True)[:6],
    }
    return render(request, 'ministry/home.html', context)

def ministry_about(request):
    """About page with uploaded images"""
    context = {
        'about_images': MinistryImage.objects.filter(image_type='about', is_active=True),
    }
    return render(request, 'ministry/about.html', context)

def ministry_crusades(request):
    """Crusades page with uploaded images"""
    context = {
        'crusade_images': MinistryImage.objects.filter(image_type='crusade', is_active=True),
    }
    return render(request, 'ministry/crusades.html', context)

def ministry_testimonies(request):
    """Testimonies page with uploaded images AND database testimonies"""
    context = {
        'testimony_images': MinistryImage.objects.filter(image_type='testimony', is_active=True),
        'testimonies': Testimony.objects.filter(is_active=True),  # ⭐ TESTIMONY ADDED!
    }
    return render(request, 'ministry/testimonies.html', context)

def ministry_contact(request):
    """Contact page with working form"""
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