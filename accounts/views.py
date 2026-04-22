from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required 
from .forms import SignupForm, LoginForm
from .models import Profile
from django.contrib import messages

def signup_view(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = form.cleaned_data["full_name"]
            user.set_password(form.cleaned_data["password"])
            user.save()
            
            Profile.objects.create(
                user = user,
                full_name = form.cleaned_data["full_name"],
                address = form.cleaned_data["address"],
                phone = form.cleaned_data["phone"],
            )
            
            login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect('buy')
    else:
        form = SignupForm()
    return render(request, 'signup.html', {'form': form})
            
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)  # Changed this line
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, "Logged in successfully!")
            return redirect('buy')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})
    
def logout_view(request):
    logout(request)
    messages.info(request, "Logged out successfully!")
    return redirect('index')


@login_required(login_url='login')
def profile_view(request):
    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        profile = Profile.objects.create(
            user=request.user,
            full_name=request.user.username,
            address="",
            phone=""
        )
    return render(request, 'profile.html', {'profile': profile})