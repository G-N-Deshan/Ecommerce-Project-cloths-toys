from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    
    # Notification Preferences
    notify_orders = models.BooleanField(default=True)
    notify_promotions = models.BooleanField(default=True)
    notify_new_arrivals = models.BooleanField(default=True)
    notify_reviews = models.BooleanField(default=True)
    
    # Profile Picture
    image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    
    # Granular Category Preferences (comma-separated: 'men,women,kids,toys')
    notified_categories = models.CharField(max_length=255, default='men,women,kids,toys')
    
    def __str__(self):
        return self.user.username
    
# Create your models here.
