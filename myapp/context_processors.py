from .models import Cart, WishlistItem, LoyaltyProfile, SiteSettings

def global_context(request):
    cart_count = 0
    wishlist_count = 0
    loyalty_points = 0

    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                cart_count = cart.get_item_count()

            wishlist_count = WishlistItem.objects.filter(user=request.user).count()

            profile = LoyaltyProfile.objects.filter(user=request.user).first()
            if profile:
                loyalty_points = int(profile.current_points)
        else:
            session_key = getattr(request.session, 'session_key', None)
            if session_key:
                cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
                if cart:
                    cart_count = cart.get_item_count()
    except Exception:
        pass

    try:
        settings_obj = SiteSettings.get_settings()
    except Exception:
        settings_obj = None

    return {
        'cart_count': cart_count,
        'wishlist_count': wishlist_count,
        'loyalty_points': loyalty_points,
        'site_settings': settings_obj,
    }

def site_settings(request):
    """
    Makes site_settings globally available in all templates.
    """
    try:
        return {'site_settings': SiteSettings.get_settings()}
    except:
        return {}
