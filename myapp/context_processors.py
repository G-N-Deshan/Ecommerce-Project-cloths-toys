from .models import Cart, WishlistItem, LoyaltyProfile, SiteSettings, Order

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
            
            # Add order count for navbar badge
            order_count = Order.objects.filter(user=request.user).exclude(status='delivered').count()
            # If no active orders, show total count or just keep it simple
            if order_count == 0:
                order_count = Order.objects.filter(user=request.user).count()
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
        'loyalty_tier': profile.effective_tier if request.user.is_authenticated and 'profile' in locals() and profile else 'none',
        'loyalty_profile': profile if request.user.is_authenticated and 'profile' in locals() and profile else None,
        'gold_progress': min(100, (profile.total_points_earned / 10000) * 100) if request.user.is_authenticated and 'profile' in locals() and profile else 0,
        'points_until_gold': max(0, 10000 - profile.total_points_earned) if request.user.is_authenticated and 'profile' in locals() and profile else 10000,
        'order_count': order_count if request.user.is_authenticated else 0,
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
