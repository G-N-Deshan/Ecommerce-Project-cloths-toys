from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='accounts_signup'),
    path('login/', views.login_view, name='accounts_login'),
    path('logout/', views.logout_view, name='accounts_logout'),
    path("profile/", views.profile_view, name="accounts_profile"),
]