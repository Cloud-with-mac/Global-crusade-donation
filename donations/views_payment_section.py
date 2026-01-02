# File: donations/views.py - PAYMENT PROCESSING SECTIONS ONLY
# Add these views to your existing views.py file

# ============================================
# PAYMENT PROCESSING VIEWS
# ============================================

from .payment_utils import PaystackPayment, FlutterwavePayment, generate_transaction_reference


def process_payment(request, donation_id):
    """
    Handle payment processing with multiple gateways (Paystack & Flutterwave)
    """
    donation = get_object_or_404(Donation, id=donation_id)
    
    # Get selected payment gateway from form (default to paystack)
    payment_gateway = request.POST.get('payment_gateway', 'paystack')
    
    if request.method == 'POST':
        try:
            # Generate unique transaction reference
            tx_ref = generate_transaction_reference(donation.id)
            donation.payment_reference = tx_ref
            donation.payment_gateway = payment_gateway
            donation.save()
            
            # Build callback/redirect URL
            callback_url = request.build_absolute_uri(
                f'/payment/verify/{donation.id}/'
            )
            
            # ============================================
            # PAYSTACK PAYMENT INITIALIZATION
            # ============================================
            if payment_gateway == 'paystack':
                paystack = PaystackPayment()
                
                response = paystack.initialize_payment(
                    email=donation.donor.email,
                    amount=donation.amount,
                    callback_url=callback_url,
                    metadata={
                        'donation_id': donation.id,
                        'donor_name': donation.donor.full_name,
                        'donation_type': donation.donation_type,
                        'custom_fields': [
                            {
                                'display_name': 'Donor Name',
                                'variable_name': 'donor_name',
                                'value': donation.donor.full_name
                            },
                            {
                                'display_name': 'Donation Type',
                                'variable_name': 'donation_type',
                                'value': donation.get_donation_type_display()
                            }
                        ]
                    }
                )
                
                if response.get('status'):
                    # Save Paystack reference
                    donation.payment_reference = response['data']['reference']
                    donation.save()
                    
                    # Redirect to Paystack payment page
                    return redirect(response['data']['authorization_url'])
                else:
                    error_msg = response.get('message', 'Payment initialization failed')
                    messages.error(request, f"Paystack Error: {error_msg}")
            
            # ============================================
            # FLUTTERWAVE PAYMENT INITIALIZATION
            # ============================================
            elif payment_gateway == 'flutterwave':
                flutterwave = FlutterwavePayment()
                
                response = flutterwave.initialize_payment(
                    email=donation.donor.email,
                    amount=donation.amount,
                    name=donation.donor.full_name,
                    phone=donation.donor.phone or '',
                    redirect_url=callback_url,
                    tx_ref=tx_ref,
                    metadata={
                        'donation_id': donation.id,
                        'donor_name': donation.donor.full_name,
                        'donation_type': donation.donation_type,
                    }
                )
                
                if response.get('status') == 'success':
                    # Redirect to Flutterwave payment page
                    return redirect(response['data']['link'])
                else:
                    error_msg = response.get('message', 'Payment initialization failed')
                    messages.error(request, f"Flutterwave Error: {error_msg}")
            
            else:
                messages.error(request, 'Invalid payment gateway selected')
            
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            donation.status = 'failed'
            donation.save()
    
    context = {
        'donation': donation,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        'flutterwave_public_key': settings.FLUTTERWAVE_PUBLIC_KEY,
    }
    return render(request, 'donations/process_payment.html', context)


def verify_payment(request, donation_id):
    """
    Verify payment from gateway callback/redirect
    Handles both Paystack and Flutterwave verification
    """
    donation = get_object_or_404(Donation, id=donation_id)
    
    try:
        # ============================================
        # PAYSTACK PAYMENT VERIFICATION
        # ============================================
        if donation.payment_gateway == 'paystack':
            # Get reference from URL query parameter
            reference = request.GET.get('reference')
            
            if not reference:
                messages.error(request, 'Payment reference not found')
                return redirect('donation_page')
            
            # Verify payment with Paystack
            paystack = PaystackPayment()
            response = paystack.verify_payment(reference)
            
            if response.get('status') and response['data']['status'] == 'success':
                # Payment successful
                donation.status = 'completed'
                donation.payment_reference = reference
                donation.completed_at = timezone.now()
                
                # Get amount from response (in kobo, convert to NGN)
                amount_paid = Decimal(response['data']['amount']) / 100
                
                # Verify amount matches (with small tolerance for fees)
                if abs(amount_paid - donation.amount) > Decimal('1.00'):
                    # Amount mismatch - log but still process
                    print(f"Amount mismatch: Expected {donation.amount}, Got {amount_paid}")
                
                donation.save()
                
                # Update crusade statistics
                stats = CrusadeStats.get_stats()
                stats.update_from_donations()
                
                # Send confirmation emails
                try:
                    from .email_utils import send_all_donation_emails
                    prayer_request = PrayerRequest.objects.filter(donation=donation).first()
                    send_all_donation_emails(donation, prayer_request)
                except Exception as e:
                    print(f"Error sending emails: {str(e)}")
                
                messages.success(request, 'Payment successful! Thank you for your donation.')
                return redirect('donation_success', donation_id=donation.id)
            
            elif response.get('data', {}).get('status') == 'abandoned':
                # Payment abandoned by user
                donation.status = 'pending'
                donation.save()
                messages.warning(request, 'Payment was not completed. Please try again.')
            
            else:
                # Payment failed
                donation.status = 'failed'
                donation.save()
                error_msg = response.get('message', 'Payment verification failed')
                messages.error(request, f'Payment failed: {error_msg}')
        
        # ============================================
        # FLUTTERWAVE PAYMENT VERIFICATION
        # ============================================
        elif donation.payment_gateway == 'flutterwave':
            # Get transaction ID from URL query parameter
            transaction_id = request.GET.get('transaction_id')
            tx_ref = request.GET.get('tx_ref')
            
            if not transaction_id:
                messages.error(request, 'Transaction ID not found')
                return redirect('donation_page')
            
            # Verify payment with Flutterwave
            flutterwave = FlutterwavePayment()
            response = flutterwave.verify_payment(transaction_id)
            
            if (response.get('status') == 'success' and 
                response['data']['status'] == 'successful'):
                
                # Additional security check: verify tx_ref matches
                if response['data']['tx_ref'] != donation.payment_reference:
                    messages.error(request, 'Transaction reference mismatch')
                    return redirect('donation_page')
                
                # Payment successful
                donation.status = 'completed'
                donation.completed_at = timezone.now()
                
                # Get amount from response
                amount_paid = Decimal(str(response['data']['amount']))
                
                # Verify amount matches
                if abs(amount_paid - donation.amount) > Decimal('1.00'):
                    print(f"Amount mismatch: Expected {donation.amount}, Got {amount_paid}")
                
                donation.save()
                
                # Update statistics
                stats = CrusadeStats.get_stats()
                stats.update_from_donations()
                
                # Send emails
                try:
                    from .email_utils import send_all_donation_emails
                    prayer_request = PrayerRequest.objects.filter(donation=donation).first()
                    send_all_donation_emails(donation, prayer_request)
                except Exception as e:
                    print(f"Error sending emails: {str(e)}")
                
                messages.success(request, 'Payment successful! Thank you for your donation.')
                return redirect('donation_success', donation_id=donation.id)
            
            elif response.get('data', {}).get('status') == 'cancelled':
                # Payment cancelled by user
                donation.status = 'pending'
                donation.save()
                messages.warning(request, 'Payment was cancelled. Please try again.')
            
            else:
                # Payment failed
                donation.status = 'failed'
                donation.save()
                error_msg = response.get('message', 'Payment verification failed')
                messages.error(request, f'Payment failed: {error_msg}')
        
        else:
            messages.error(request, 'Unknown payment gateway')
    
    except Exception as e:
        donation.status = 'failed'
        donation.save()
        messages.error(request, f'An error occurred during verification: {str(e)}')
    
    return redirect('donation_page')


# ============================================
# WEBHOOK HANDLERS (OPTIONAL BUT RECOMMENDED)
# ============================================

@csrf_exempt
def paystack_webhook(request):
    """
    Handle Paystack webhook events
    URL: /webhook/paystack/
    """
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    # Get signature from headers
    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
    
    if not signature:
        return HttpResponse(status=400)
    
    # Verify signature
    paystack = PaystackPayment()
    if not paystack.verify_webhook_signature(request.body, signature):
        return HttpResponse(status=400)
    
    # Process webhook event
    try:
        event = json.loads(request.body)
        
        if event.get('event') == 'charge.success':
            reference = event['data']['reference']
            
            # Find donation by reference
            try:
                donation = Donation.objects.get(payment_reference=reference)
                
                # Only update if not already completed
                if donation.status != 'completed':
                    donation.status = 'completed'
                    donation.completed_at = timezone.now()
                    donation.save()
                    
                    # Update stats
                    stats = CrusadeStats.get_stats()
                    stats.update_from_donations()
                    
                    # Send emails if not already sent
                    try:
                        from .email_utils import send_all_donation_emails
                        prayer_request = PrayerRequest.objects.filter(donation=donation).first()
                        send_all_donation_emails(donation, prayer_request)
                    except:
                        pass
                
            except Donation.DoesNotExist:
                pass
        
        return HttpResponse(status=200)
    
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return HttpResponse(status=500)


@csrf_exempt
def flutterwave_webhook(request):
    """
    Handle Flutterwave webhook events
    URL: /webhook/flutterwave/
    """
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    # Get signature from headers
    signature = request.META.get('HTTP_VERIF_HASH')
    
    if not signature:
        return HttpResponse(status=400)
    
    # Verify signature
    flutterwave = FlutterwavePayment()
    if signature != flutterwave.secret_key:
        return HttpResponse(status=400)
    
    # Process webhook event
    try:
        event = json.loads(request.body)
        
        if event.get('event') == 'charge.completed':
            tx_ref = event['data']['tx_ref']
            
            # Find donation by reference
            try:
                donation = Donation.objects.get(payment_reference=tx_ref)
                
                # Verify payment status
                if event['data']['status'] == 'successful' and donation.status != 'completed':
                    donation.status = 'completed'
                    donation.completed_at = timezone.now()
                    donation.save()
                    
                    # Update stats
                    stats = CrusadeStats.get_stats()
                    stats.update_from_donations()
                    
                    # Send emails
                    try:
                        from .email_utils import send_all_donation_emails
                        prayer_request = PrayerRequest.objects.filter(donation=donation).first()
                        send_all_donation_emails(donation, prayer_request)
                    except:
                        pass
                
            except Donation.DoesNotExist:
                pass
        
        return HttpResponse(status=200)
    
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return HttpResponse(status=500)
