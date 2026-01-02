# File: donations/templatetags/currency_filters.py
# CUSTOM TEMPLATE FILTERS FOR CURRENCY DISPLAY

from django import template

register = template.Library()


@register.filter(name='get_currency_symbol')
def get_currency_symbol(payment_reference):
    """
    Extract currency symbol from payment_reference field
    
    Examples:
        "NGN|TRX123" → "₦"
        "USD|REF456" → "$"
        "NGN" → "₦"
        "USD" → "$"
        None → "$"
    """
    if not payment_reference:
        return '$'
    
    # Currency symbols
    symbols = {
        'NGN': '₦',
        'USD': '$',
        'EUR': '€',
        'GBP': '£'
    }
    
    # Extract currency code
    if '|' in payment_reference:
        currency = payment_reference.split('|')[0]
    else:
        currency = payment_reference
    
    return symbols.get(currency, '$')


@register.filter(name='get_currency_code')
def get_currency_code(payment_reference):
    """
    Extract currency code from payment_reference field
    
    Examples:
        "NGN|TRX123" → "NGN"
        "USD|REF456" → "USD"
        "NGN" → "NGN"
        None → "USD"
    """
    if not payment_reference:
        return 'USD'
    
    if '|' in payment_reference:
        return payment_reference.split('|')[0]
    else:
        return payment_reference


@register.filter(name='get_transaction_reference')
def get_transaction_reference(payment_reference):
    """
    Extract transaction reference from payment_reference field
    
    Examples:
        "NGN|TRX123" → "TRX123"
        "USD|REF456" → "REF456"
        "NGN" → ""
        None → ""
    """
    if not payment_reference:
        return ''
    
    if '|' in payment_reference:
        return payment_reference.split('|')[1]
    else:
        return ''


@register.filter(name='format_currency_amount')
def format_currency_amount(donation):
    """
    Format donation amount with correct currency symbol
    
    Example:
        donation with amount=300, payment_reference="NGN" → "₦300.00"
        donation with amount=100, payment_reference="USD|TRX" → "$100.00"
    """
    if not donation:
        return ''
    
    symbol = get_currency_symbol(donation.payment_reference)
    amount = donation.amount
    
    # Format with comma separators
    formatted_amount = f"{amount:,.2f}"
    
    return f"{symbol}{formatted_amount}"


@register.filter(name='get_currency_name')
def get_currency_name(payment_reference):
    """
    Get full currency name from payment_reference
    
    Examples:
        "NGN" → "Nigerian Naira"
        "USD" → "US Dollars"
    """
    if not payment_reference:
        return 'US Dollars'
    
    names = {
        'NGN': 'Nigerian Naira',
        'USD': 'US Dollars',
        'EUR': 'Euros',
        'GBP': 'British Pounds'
    }
    
    if '|' in payment_reference:
        currency = payment_reference.split('|')[0]
    else:
        currency = payment_reference
    
    return names.get(currency, 'US Dollars')