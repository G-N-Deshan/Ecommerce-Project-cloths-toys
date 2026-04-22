from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import (
    Card, Offers, NewArrivals, Cloths, Review, Toy,
    ContactMessage, ProductImage, Inventory, Coupon,
    ProductVariant, OrderTracking, Order, SiteUpdate,
)

_WATCHED_MODELS = (
    Card, Offers, NewArrivals, Cloths, Review, Toy,
    ContactMessage, ProductImage, Inventory, Coupon,
    ProductVariant, OrderTracking, Order,
)


def _touch_site(sender, **kwargs):
    try:
        SiteUpdate.touch()
    except Exception:
        pass  # DB may not be ready during migrations


for _model in _WATCHED_MODELS:
    post_save.connect(_touch_site, sender=_model)
    post_delete.connect(_touch_site, sender=_model)
