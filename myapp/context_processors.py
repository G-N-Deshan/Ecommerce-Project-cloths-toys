from .models import Cart, WishlistItem

# Breadcrumb mapping: URL path prefix -> (label, url)
BREADCRUMB_MAP = {
    '/about/': 'About Us',
    '/contact/': 'Contact',
    '/buy/': 'Shop',
    '/shop-offers/': 'Shop Offers',
    '/new_arrivals/': 'New Arrivals',
    '/cloths/': 'Cloths',
    '/kids_cloths/': 'Kids Cloths',
    '/women_cloths/': "Women's Cloths",
    '/mens_cloths/': "Men's Cloths",
    '/toys/': 'Toys',
    '/reviews/': 'Reviews',
    '/cart/': 'Cart',
    '/cart_details_page/': 'Cart Details',
    '/wishlist/': 'Wishlist',
    '/checkout/': 'Checkout',
    '/profile/': 'Profile',
    '/search/': 'Search',
    '/my-orders/': 'My Orders',
    '/login/': 'Login',
    '/signup/': 'Sign Up',
    '/dashboard/': 'Dashboard',
    '/payment/': 'Payment',
}


def global_context(request):
    """Provide cart_count, wishlist_count, and breadcrumbs to every template."""
    cart_count = 0
    wishlist_count = 0

    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                cart_count = cart.get_item_count()
            wishlist_count = WishlistItem.objects.filter(user=request.user).count()
        else:
            session_key = getattr(request.session, 'session_key', None)
            if session_key:
                cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
                if cart:
                    cart_count = cart.get_item_count()
    except Exception:
        pass

    # Auto-generate breadcrumbs
    path = request.path
    breadcrumbs = []
    if path != '/':
        label = BREADCRUMB_MAP.get(path)
        if label:
            breadcrumbs = [{'label': label, 'url': None}]
        elif path.startswith('/product/'):
            breadcrumbs = [{'label': 'Shop', 'url': '/buy/'}, {'label': 'Product Detail', 'url': None}]
        elif path.startswith('/order-tracking/'):
            breadcrumbs = [{'label': 'My Orders', 'url': '/my-orders/'}, {'label': 'Order Tracking', 'url': None}]
        elif path.startswith('/order-success/'):
            breadcrumbs = [{'label': 'Order Confirmed', 'url': None}]

    return {
        'cart_count': cart_count,
        'wishlist_count': wishlist_count,
        'breadcrumbs': breadcrumbs,
    }
