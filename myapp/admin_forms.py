from django import forms
from .models import (
    Cloths, Toy, Offers, NewArrivals, Order, 
    SiteBanner, SiteSettings, Inventory, ProductVariant
)

class ClothsForm(forms.ModelForm):
    class Meta:
        model = Cloths
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'desccription': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'long_description': forms.Textarea(attrs={'class': 'form-input', 'rows': 5}),
            'price': forms.TextInput(attrs={'class': 'form-input'}),
        }

class ToyForm(forms.ModelForm):
    class Meta:
        model = Toy
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'price': forms.NumberInput(attrs={'class': 'form-input'}),
        }

class OffersForm(forms.ModelForm):
    class Meta:
        model = Offers
        fields = '__all__'
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }

class NewArrivalsForm(forms.ModelForm):
    class Meta:
        model = NewArrivals
        fields = '__all__'
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
        }

class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = '__all__'
        widgets = {
            'sale_text': forms.TextInput(attrs={'class': 'form-input'}),
        }

class SiteBannerForm(forms.ModelForm):
    class Meta:
        model = SiteBanner
        fields = '__all__'
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'subtitle': forms.TextInput(attrs={'class': 'form-input'}),
        }

from .models import Coupon

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = '__all__'
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-input'}),
            'discount_type': forms.Select(attrs={'class': 'form-input'}),
            'discount_value': forms.NumberInput(attrs={'class': 'form-input'}),
            'min_order_amount': forms.NumberInput(attrs={'class': 'form-input'}),
            'max_uses': forms.NumberInput(attrs={'class': 'form-input'}),
            'valid_from': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'valid_until': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
        }
