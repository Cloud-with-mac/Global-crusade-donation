# File: donations/payment_utils.py
# Location: ministry_donation_site/donations/payment_utils.py

"""
Payment Gateway Utilities
Handles payment operations for Paystack and Flutterwave
"""

import requests
import json
import hashlib
import hmac
import time
from django.conf import settings
from decimal import Decimal


class PaystackPayment:
    """
    Handle Paystack payment operations
    Documentation: https://paystack.com/docs/api/
    """
    
    BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.public_key = settings.PAYSTACK_PUBLIC_KEY
    
    def initialize_payment(self, email, amount, callback_url, metadata=None):
        """
        Initialize a payment transaction
        
        Args:
            email (str): Customer email
            amount (Decimal/float): Amount in NGN (will be converted to kobo)
            callback_url (str): URL to redirect after payment
            metadata (dict): Additional data to store with transaction
        
        Returns:
            dict: Response from Paystack API
            {
                'status': True/False,
                'message': 'Authorization URL created',
                'data': {
                    'authorization_url': 'https://checkout.paystack.com/...',
                    'access_code': 'xxx',
                    'reference': 'xxx'
                }
            }
        """
        url = f"{self.BASE_URL}/transaction/initialize"
        
        # Convert amount to kobo (smallest currency unit)
        # 1 NGN = 100 kobo
        amount_in_kobo = int(float(amount) * 100)
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }
        
        data = {
            "email": email,
            "amount": amount_in_kobo,
            "callback_url": callback_url,
            "metadata": metadata or {},
            "currency": "NGN",  # You can change to USD if needed
            "channels": ["card", "bank", "ussd", "qr", "mobile_money", "bank_transfer"]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'status': False,
                'message': f'Network error: {str(e)}'
            }
    
    def verify_payment(self, reference):
        """
        Verify a payment transaction
        
        Args:
            reference (str): Transaction reference from Paystack
        
        Returns:
            dict: Payment verification response
            {
                'status': True/False,
                'message': 'Verification successful',
                'data': {
                    'status': 'success',
                    'reference': 'xxx',
                    'amount': 100000,
                    'customer': {...},
                    ...
                }
            }
        """
        url = f"{self.BASE_URL}/transaction/verify/{reference}"
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'status': False,
                'message': f'Network error: {str(e)}'
            }
    
    def verify_webhook_signature(self, payload, signature):
        """
        Verify webhook signature from Paystack
        
        Args:
            payload (bytes): Raw request body
            signature (str): X-Paystack-Signature header value
        
        Returns:
            bool: True if signature is valid
        """
        computed_signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        return computed_signature == signature


class FlutterwavePayment:
    """
    Handle Flutterwave payment operations
    Documentation: https://developer.flutterwave.com/docs
    """
    
    BASE_URL = "https://api.flutterwave.com/v3"
    
    def __init__(self):
        self.secret_key = settings.FLUTTERWAVE_SECRET_KEY
        self.public_key = settings.FLUTTERWAVE_PUBLIC_KEY
        self.encryption_key = settings.FLUTTERWAVE_ENCRYPTION_KEY
    
    def initialize_payment(self, email, amount, name, phone, redirect_url, tx_ref, metadata=None):
        """
        Initialize a payment transaction
        
        Args:
            email (str): Customer email
            amount (Decimal/float): Amount in NGN
            name (str): Customer full name
            phone (str): Customer phone number
            redirect_url (str): URL to redirect after payment
            tx_ref (str): Unique transaction reference
            metadata (dict): Additional data
        
        Returns:
            dict: Response from Flutterwave API
            {
                'status': 'success',
                'message': 'Hosted Link',
                'data': {
                    'link': 'https://checkout.flutterwave.com/...'
                }
            }
        """
        url = f"{self.BASE_URL}/payments"
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }
        
        data = {
            "tx_ref": tx_ref,
            "amount": str(amount),
            "currency": "NGN",  # Can be USD, EUR, GBP, etc.
            "redirect_url": redirect_url,
            "payment_options": "card,banktransfer,ussd,mobilemoneyghana,mobilemoneyuganda",
            "customer": {
                "email": email,
                "name": name,
                "phonenumber": phone or "",
            },
            "customizations": {
                "title": "Global Crusade Ministry",
                "description": "Donation for crusade ministry",
                "logo": "",  # Add your logo URL here (e.g., https://yourdomain.com/logo.png)
            },
            "meta": metadata or {},
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'status': 'error',
                'message': f'Network error: {str(e)}'
            }
    
    def verify_payment(self, transaction_id):
        """
        Verify a payment transaction
        
        Args:
            transaction_id (str): Transaction ID from Flutterwave
        
        Returns:
            dict: Payment verification response
            {
                'status': 'success',
                'message': 'Transaction fetched successfully',
                'data': {
                    'status': 'successful',
                    'amount': 1000,
                    'currency': 'NGN',
                    ...
                }
            }
        """
        url = f"{self.BASE_URL}/transactions/{transaction_id}/verify"
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'status': 'error',
                'message': f'Network error: {str(e)}'
            }
    
    def verify_webhook_signature(self, payload, signature):
        """
        Verify webhook signature from Flutterwave
        
        Args:
            payload (dict): Webhook payload
            signature (str): verif-hash header value
        
        Returns:
            bool: True if signature is valid
        """
        # Flutterwave uses a simple hash comparison
        return signature == self.secret_key


def generate_transaction_reference(donation_id):
    """
    Generate unique transaction reference for payments
    
    Args:
        donation_id (int): Donation ID
    
    Returns:
        str: Unique reference (e.g., DON-123-1640000000)
    """
    timestamp = int(time.time())
    return f"DON-{donation_id}-{timestamp}"


def convert_ngn_to_usd(amount_ngn, rate=None):
    """
    Convert NGN to USD (optional utility)
    
    Args:
        amount_ngn (Decimal): Amount in NGN
        rate (Decimal): Exchange rate (NGN to USD), defaults to ~750
    
    Returns:
        Decimal: Amount in USD
    """
    if rate is None:
        rate = Decimal('750')  # Update with current rate
    
    return amount_ngn / rate


def convert_usd_to_ngn(amount_usd, rate=None):
    """
    Convert USD to NGN (optional utility)
    
    Args:
        amount_usd (Decimal): Amount in USD
        rate (Decimal): Exchange rate (USD to NGN), defaults to ~750
    
    Returns:
        Decimal: Amount in NGN
    """
    if rate is None:
        rate = Decimal('750')  # Update with current rate
    
    return amount_usd * rate
