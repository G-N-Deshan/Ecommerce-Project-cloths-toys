from django import forms
from .models import Review, ContactMessage, ServiceReview

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['name', 'email', 'rating', 'comment', 'uploadImages']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Your name'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Your email'}),
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': 'Your review'}),
            'uploadImages': forms.FileInput(attrs={'class': 'form-file'}),
        }
        
        
class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your Full Name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'your.email@example.com',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+1 (555) 123-4567',
                'type': 'tel',
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'What is this about?',
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 6,
                'placeholder': 'Tell us your message...',
            }),
        }


class ServiceReviewForm(forms.ModelForm):
    class Meta:
        model = ServiceReview
        fields = [
            'name',
            'email',
            'topic',
            'delivery_rating',
            'packaging_rating',
            'support_rating',
            'returns_rating',
            'comment',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Your name'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'Your email'}),
            'topic': forms.Select(attrs={'class': 'form-select'}),
            'delivery_rating': forms.Select(choices=[(i, str(i)) for i in range(1, 6)], attrs={'class': 'form-select'}),
            'packaging_rating': forms.Select(choices=[(i, str(i)) for i in range(1, 6)], attrs={'class': 'form-select'}),
            'support_rating': forms.Select(choices=[(i, str(i)) for i in range(1, 6)], attrs={'class': 'form-select'}),
            'returns_rating': forms.Select(choices=[(i, str(i)) for i in range(1, 6)], attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 5, 'placeholder': 'Tell us about your service experience'}),
        }