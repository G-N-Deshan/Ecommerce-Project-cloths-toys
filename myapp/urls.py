from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),

    # Use contact_us as the single contact endpoint (GET+POST)
    path('contact/', views.contact_us, name='contact_us'),
    path('contact-success/', views.contact_success, name='contact_success'),

    path('buy/', views.buy, name='buy'),
    path('shop-offers/', views.shop_offers, name='shop_offers'),
    path('new_arrivals/', views.new_arrivals, name='new_arrivals'),

    path('login/', views.user_login, name='login'),
    path('signup/', views.user_signup, name='signup'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),

    path('product/<str:product_type>/<int:product_id>/', views.product_detail, name='product_detail'),

    path('cloths/', views.cloths, name='cloths'),
    path('toys/', views.toys_page, name='toys_page'),  # keep only one toys route

    path('kids_cloths/', views.kids_cloths, name='kids_cloths'),
    path('women_cloths/', views.women_cloths, name='women_cloths'),
    path('mens_cloths/', views.mens_cloths, name='mens_cloths'),

    path('reviews/', views.reviews, name='reviews'),
    path('review-success/', views.review_success, name='review_success'),

    path('cart/', views.cart_page, name='cart'),
    path('cart/add/<str:item_type>/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:cart_item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('cart/get/', views.get_cart_data, name='get_cart_data'),
    path('cart_details_page/', views.cart_details, name='cart_details'),

    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/<str:item_type>/<int:item_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:wishlist_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/move-to-cart/<int:wishlist_id>/', views.move_to_cart, name='move_to_cart'),

    path('checkout/', views.checkout, name='checkout'),
    path('order-success/<str:order_number>/', views.order_success, name='order_success'),

    # Profile Management URLs
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('profile/notification-preferences/', views.notification_preferences, name='notification_preferences'),
    path('profile/update-email/', views.update_email, name='update_email'),

    # Search
    path('search/', views.search, name='search'),

    # Order Tracking & My Orders
    path('my-orders/', views.my_orders, name='my_orders'),
    path('order-tracking/<str:order_number>/', views.order_tracking, name='order_tracking'),
    path('reorder/<str:order_number>/', views.reorder, name='reorder'),

    # Coupon Validation (AJAX)
    path('validate-coupon/', views.validate_coupon, name='validate_coupon'),

    # Product Variants (AJAX)
    path('product-variants/<int:product_id>/', views.get_product_variants, name='get_product_variants'),

    # Admin Dashboard
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Payment (Stripe)
    path('payment/', views.payment_page, name='payment_page'),
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-cancel/', views.payment_cancel, name='payment_cancel'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),

    # Live Stock API
    path('api/stock-status/', views.stock_status_api, name='stock_status_api'),

    # REST API
    path('api/products/', views.api_products, name='api_products'),

    # Real-time update polling
    path('check-updates/', views.check_updates, name='check_updates'),

    # Password Reset (Django built-in)
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset.html',
        email_template_name='password_reset_email.html',
        subject_template_name='password_reset_subject.txt',
        success_url='/password-reset/done/',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html',
        success_url='/password-reset-complete/',
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html',
    ), name='password_reset_complete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

