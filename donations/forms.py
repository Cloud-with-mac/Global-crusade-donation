# File: donations/forms.py
# Location: ministry_donation_site/donations/forms.py

from django import forms
from .models import Donation, Donor


class DonationForm(forms.ModelForm):
    """Form for creating donations"""
    
    # Donor fields (we'll handle these manually)
    full_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Full Name',
            'class': 'text-input'
        })
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email Address',
            'class': 'text-input'
        })
    )
    
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Phone Number (Optional)',
            'class': 'text-input'
        })
    )
    
    country = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Country',
            'class': 'text-input'
        })
    )
    
    class Meta:
        model = Donation
        fields = ['amount', 'donation_type', 'payment_method', 'message']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'placeholder': '0.00',
                'class': 'amount-input',
                'step': '0.01',
                'min': '1'
            }),
            'donation_type': forms.RadioSelect(),
            'payment_method': forms.RadioSelect(),
            'message': forms.Textarea(attrs={
                'placeholder': 'Share your thoughts or prayer requests...',
                'class': 'textarea-input',
                'rows': 3
            }),
        }
    
    def save(self, commit=True):
        """Override save to handle donor creation"""
        # Get or create donor
        donor, created = Donor.objects.get_or_create(
            email=self.cleaned_data['email'],
            defaults={
                'full_name': self.cleaned_data['full_name'],
                'phone': self.cleaned_data['phone'],
                'country': self.cleaned_data['country'],
            }
        )
        
        # If donor exists, update their info
        if not created:
            donor.full_name = self.cleaned_data['full_name']
            donor.phone = self.cleaned_data['phone']
            donor.country = self.cleaned_data['country']
            donor.save()
        
        # Create donation
        donation = super().save(commit=False)
        donation.donor = donor
        
        if commit:
            donation.save()
        
        return donation