from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate


class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    full_name = forms.CharField(max_length=150)
    address = forms.CharField(max_length=255)
    phone = forms.CharField(max_length=20)
    
    class Meta:
        model = User
        fields = ['email', 'password']


class LoginForm(forms.Form):
    username = forms.CharField(label="Username (Full Name)")
    password = forms.CharField(widget=forms.PasswordInput)
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            self.user = authenticate(username=username, password=password)
            if self.user is None:
                raise forms.ValidationError("Invalid username or password")
        return self.cleaned_data
    
    def get_user(self):
        return self.user