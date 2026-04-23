from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from .models import (Card, Offers, NewArrivals, Cloths, Review, ContactMessage, Toy,
                     WishlistItem, Cart, CartItem, Order, OrderItem, ProductReview,
                     ProductImage, Inventory, Coupon, ProductVariant, OrderTracking,
                     SiteUpdate, ServiceReview, NewsletterSubscription,
                     LoyaltyProfile, LoyaltyHistory)
from .forms import ReviewForm, ContactForm, ServiceReviewForm
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from decimal import Decimal
import uuid
import re
import stripe
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Sum as models_sum, F
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.template.loader import render_to_string


# Helper function for cart management
def get_or_create_cart(request):
    """Get or create cart for user or session"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key

        # Safe lookup + create (don't use user__isnull in get_or_create create kwargs)
        cart = Cart.objects.filter(session_key=session_key, user__isnull=True).first()
        if not cart:
            cart = Cart.objects.create(session_key=session_key, user=None)

    return cart


def parse_catalog_price(raw_value):
    if raw_value is None:
        return 0.0
    text = str(raw_value).strip()
    if not text:
        return 0.0
    text = re.sub(r'[^0-9,.-]', '', text).replace(',', '')
    try:
        return float(text) if text else 0.0
    except ValueError:
        return 0.0


def parse_query_float(raw_value):
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return None


# Loyalty Program Helpers
def get_loyalty_profile(user):
    profile, created = LoyaltyProfile.objects.get_or_create(user=user)
    return profile


@login_required(login_url='login')
def loyalty_dashboard(request):
    profile = get_loyalty_profile(request.user)
    history = profile.history.all().order_by('-created_at')
    
    # Calculate progress to next tier
    next_tier = None
    next_tier_points = 0
    progress = 0
    
    if profile.tier == 'bronze':
        next_tier = 'Silver'
        next_tier_points = 1000
    elif profile.tier == 'silver':
        next_tier = 'Gold'
        next_tier_points = 5000
        
    if next_tier_points > 0:
        progress = min(100, (profile.total_points_earned / next_tier_points) * 100)

    context = {
        'profile': profile,
        'history': history,
        'next_tier': next_tier,
        'next_tier_points': next_tier_points,
        'progress': progress,
    }
    return render(request, 'loyalty_dashboard.html', context)


@require_POST
@login_required(login_url='login')
def redeem_loyalty_points(request):
    """Convert points into a coupon"""
    try:
        data = json.loads(request.body)
        points_to_redeem = int(data.get('points', 0))
        
        if points_to_redeem < 500:
            return JsonResponse({'success': False, 'error': 'Minimum 500 points required for redemption.'}, status=400)
            
        profile = get_loyalty_profile(request.user)
        
        if profile.current_points < points_to_redeem:
            return JsonResponse({'success': False, 'error': 'Insufficient points.'}, status=400)
            
        # Calculate discount: 10 points = Rs. 1.0 (500 pts = Rs 50)
        discount_value = points_to_redeem // 10
        
        # Create a unique coupon code
        import uuid
        coupon_code = f"REWARD-{uuid.uuid4().hex[:6].upper()}"
        
        from django.utils import timezone
        from datetime import timedelta
        
        coupon = Coupon.objects.create(
            code=coupon_code,
            discount_type='fixed',
            discount_value=Decimal(str(discount_value)),
            min_order_amount=Decimal(str(discount_value * 5)),
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=30),
            is_active=True
        )
        
        # Deduct points
        profile.current_points -= points_to_redeem
        profile.save()
        
        # Add history
        LoyaltyHistory.objects.create(
            profile=profile,
            points=-points_to_redeem,
            description=f"Redeemed points for coupon {coupon_code} (Rs. {discount_value} off)"
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Successfully redeemed! Your code: {coupon_code}',
            'coupon_code': coupon_code,
            'new_points': profile.current_points
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def ai_chat(request):
    """Smart Concierge AI Assistant Logic"""
    try:
        data = json.loads(request.body)
        query = data.get('message', '').lower().strip()
        
        if not query:
            return JsonResponse({'message': "I'm your G11 Assistant! How can I help you today?"})

        # 1. Simple FAQ logic
        if any(word in query for word in ['ship', 'delivery', 'track', 'arrive']):
            return JsonResponse({
                'message': "🎁 **Shipping Info:** We offer standard delivery (3-5 days) and Express (1-2 days). You'll get a tracking link via email as soon as we dispatch your order!",
                'products': []
            })
            
        if any(word in query for word in ['return', 'refund', 'exchange', 'policy']):
            return JsonResponse({
                'message': "🔄 **Returns:** We have a worry-free 30-day return policy. Just ensure the items are unused and have their original tags.",
                'products': []
            })
            
        if any(word in query for word in ['size', 'chart', 'fit', 'measurement']):
            return JsonResponse({
                'message': "📏 **Sizing:** Most of our clothes are true-to-size. You can find a specific size guide on every product detail page!",
                'products': []
            })

        if any(word in query for word in ['style', 'match', 'advice', 'wear', 'combine', 'outfit']):
            return JsonResponse({
                'message': "👗 **Style Advice:** For a balanced look, try pairing our bold patterned tops with neutral-colored pants. Soft pastels work great for spring, while deep indigo and mustard are perfect for cooler seasons! Need a specific match? Tell me what color you're starting with.",
                'products': []
            })

        # 2. Product Search Logic
        import re
        
        # Extract numbers (potentially ages)
        ages = re.findall(r'\b\d+\b', query)
        
        stop_words = {'i', 'want', 'need', 'to', 'buy', 'shop', 'for', 'a', 'the', 'is', 'find', 'me', 'some', 'looking', 'gift', 'present', 'year', 'years', 'old'}
        raw_words = query.split()
        keywords = [word for word in raw_words if word not in stop_words and not word.isdigit()]
        
        if not keywords and not ages:
            return JsonResponse({
                'message': "I'm ready to help! You can ask me for product recommendations (e.g., 'blue dresses') or gift ideas by age.",
                'products': []
            })

        # Initialize Q objects
        toy_q = Q()
        cloth_q = Q()

        # Handle gender/category mapping
        if any(w in raw_words for w in ['boy', 'boys', 'son', 'male']):
            toy_q |= Q(category__icontains='educational') | Q(category__icontains='building')
            cloth_q |= Q(category__icontains='kids-men') | Q(category__icontains='men')
        if any(w in raw_words for w in ['girl', 'girls', 'daughter', 'female']):
            toy_q |= Q(category__icontains='creative') | Q(category__icontains='plush')
            cloth_q |= Q(category__icontains='kids-girl') | Q(category__icontains='women')

        # Handle age matching
        for age in ages:
            toy_q |= Q(age_range__icontains=age)
            # For clothes, we search description/name for age mentioned
            cloth_q |= Q(name__icontains=age) | Q(desccription__icontains=age)

        # Keyword matching
        for kw in keywords:
            if len(kw) > 2:
                toy_q |= Q(name__icontains=kw) | Q(description__icontains=kw) | Q(category__icontains=kw)
                cloth_q |= Q(name__icontains=kw) | Q(desccription__icontains=kw) | Q(category__icontains=kw)

        toys = Toy.objects.filter(toy_q).distinct()[:3]
        cloths = Cloths.objects.filter(cloth_q).distinct()[:3]
        
        products = []
        for t in toys:
            products.append({
                'name': t.name,
                'price': f"Rs. {t.price}",
                'url': f"/product/toy/{t.id}/",
                'image': t.imageUrl.url if t.imageUrl else ''
            })
        for c in cloths:
            products.append({
                'name': c.name,
                'price': c.price2 or c.price1 or c.price,
                'url': f"/product/cloth/{c.id}/",
                'image': c.imageUrl.url if c.imageUrl else ''
            })

        if products:
            return JsonResponse({
                'message': f"✨ I've curated a few items for you based on **'{query}'**. Hope you love them!",
                'products': products
            })
        else:
            if any(w in raw_words for w in ['why', 'how', 'explain', 'what']):
                return JsonResponse({
                    'message': "🤔 I'm still learning! Right now, I can find products by color, category, or age (like 'blue dress' or 'toys for 3 year old'). I can also help with shipping and return info. What can I help you find?",
                    'products': []
                })
            
            return JsonResponse({
                'message': "🔍 I couldn't find an exact match for that specific request, but check out these **New Arrivals** — they're trending right now!",
                'products': []
            })

    except Exception as e:
        return JsonResponse({'message': "Oops! I hit a snag. Please try again or contact support."}, status=500)


# Create your views here.


@require_POST
def subscribe_newsletter(request):
    email = request.POST.get('email', '').strip()
    if not email:
        return JsonResponse({'status': 'error', 'message': 'Please provide a valid email.'}, status=400)
    
    # Simple email validation
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return JsonResponse({'status': 'error', 'message': 'Please provide a valid email format.'}, status=400)

    try:
        if NewsletterSubscription.objects.filter(email=email).exists():
            return JsonResponse({'status': 'info', 'message': 'You are already subscribed!'})
            
        NewsletterSubscription.objects.create(email=email)
        return JsonResponse({'status': 'success', 'message': 'Thank you for subscribing! Check your inbox soon.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Something went wrong. Please try again later.'}, status=500)


def index(request):
    offers = Offers.objects.all()
    arrivals = NewArrivals.objects.all()
    cards = Card.objects.all()
    wishlist_items = []
    wishlist_count = 0
    cart_count = 0
    
    # Get cart count
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_count = cart.get_item_count()
        except Cart.DoesNotExist:
            cart_count = 0
    else:
        if request.session.session_key:
            try:
                cart = Cart.objects.get(session_key=request.session.session_key, user__isnull=True)
                cart_count = cart.get_item_count()
            except Cart.DoesNotExist:
                cart_count = 0
    
    if request.user.is_authenticated:
        user_wishlist = WishlistItem.objects.filter(user=request.user)
        wishlist_count = user_wishlist.count()
        
        # Prepare wishlist data for template
        for item in user_wishlist[:6]:  # Show only first 6 items on home page
            wishlist_items.append({
                'id': item.id,
                'name': item.get_item().name,
                'price': item.get_price(),
                'image': item.get_item().imageUrl.url if item.get_item().imageUrl else '',
                'category': item.get_category(),
                'item_type': item.item_type,
            })
    
    context = {
        'cards': cards,
        'offers': offers,
        'arrivals': arrivals,
        'wishlist_items': wishlist_items,
        'wishlist_count': wishlist_count,
        'cart_count': cart_count,
    }
    
    return render(request, 'index.html', context)

def about(request):
    cart_count = 0
    try:
        cart_count = get_or_create_cart(request).get_item_count()
    except Exception:
        cart_count = 0

    approved_reviews = ServiceReview.objects.filter(is_approved=True)
    total_reviews = approved_reviews.count()

    summary = {
        'total_reviews': total_reviews,
        'average_rating': 0,
        'recommend_percent': 0,
        'delivery_avg': 0,
        'support_avg': 0,
    }

    if total_reviews:
        aggregate = approved_reviews.aggregate(
            average_rating=Avg('overall_rating'),
            delivery_avg=Avg('delivery_rating'),
            support_avg=Avg('support_rating'),
        )
        recommend_count = approved_reviews.filter(overall_rating__gte=4).count()
        summary = {
            'total_reviews': total_reviews,
            'average_rating': round(float(aggregate.get('average_rating') or 0), 1),
            'recommend_percent': round((recommend_count * 100) / total_reviews),
            'delivery_avg': round(float(aggregate.get('delivery_avg') or 0), 1),
            'support_avg': round(float(aggregate.get('support_avg') or 0), 1),
        }

    return render(request, 'about.html', {
        'cart_count': cart_count,
        'service_summary': summary,
        'latest_service_reviews': approved_reviews[:3],
    })

def contact(request):
    return render(request, 'contact.html')


def buy(request):
    offers = Offers.objects.annotate(avg_rating=Avg('product_reviews__rating'), review_count=Count('product_reviews')).order_by('-id')
    arrivals = NewArrivals.objects.annotate(avg_rating=Avg('product_reviews__rating'), review_count=Count('product_reviews')).order_by('-id')

    top_rated_offers = offers.filter(review_count__gt=0).order_by('-avg_rating', '-review_count', '-id')[:4]
    most_reviewed_arrivals = arrivals.filter(review_count__gt=0).order_by('-review_count', '-avg_rating', '-id')[:4]
    
    # Get cart count
    cart_count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            cart_count = cart.get_item_count()
        except Cart.DoesNotExist:
            cart_count = 0
    
    context = {
        'offers': offers,
        'kids_arrivals': arrivals,
        'top_rated_offers': top_rated_offers,
        'most_reviewed_arrivals': most_reviewed_arrivals,
        'total_products': offers.count() + arrivals.count(),
        'cart_count': cart_count,
    }
    
    return render(request, 'buy.html', context)

def shop_offers(request):
    offers_qs = Offers.objects.annotate(
        avg_rating=Avg('product_reviews__rating'),
        review_count=Count('product_reviews')
    ).order_by('-id')

    category = request.GET.get('category', 'all')
    search = (request.GET.get('search') or '').strip()
    sort = request.GET.get('sort', 'latest')

    filtered = offers_qs
    if category in {'kids', 'men', 'women'}:
        filtered = filtered.filter(category=category)

    if search:
        filtered = filtered.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(offers_badge__icontains=search)
        )

    if sort == 'rating':
        filtered = filtered.order_by('-avg_rating', '-review_count', '-id')
    elif sort == 'popular':
        filtered = filtered.order_by('-review_count', '-avg_rating', '-id')
    else:
        filtered = filtered.order_by('-id')

    paginator = Paginator(filtered, 9)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'shop_offers.html', {
        'all_offers': page_obj,
        'selected_category': category,
        'search_query': search,
        'selected_sort': sort,
        'is_paginated': paginator.num_pages > 1,
        'total_offers': offers_qs.count(),
        'total_filtered': filtered.count(),
        'kids_count': offers_qs.filter(category='kids').count(),
        'men_count': offers_qs.filter(category='men').count(),
        'women_count': offers_qs.filter(category='women').count(),
    })
    
def new_arrivals(request):
    arrivals_qs = NewArrivals.objects.annotate(
        avg_rating=Avg('product_reviews__rating'),
        review_count=Count('product_reviews')
    ).order_by('-id')

    category = request.GET.get('category', 'all')
    search = (request.GET.get('search') or '').strip()
    sort = request.GET.get('sort', 'latest')

    filtered = arrivals_qs
    if category in {'kids', 'men', 'women'}:
        filtered = filtered.filter(category=category)

    if search:
        filtered = filtered.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(offers_badge__icontains=search)
        )

    if sort == 'rating':
        filtered = filtered.order_by('-avg_rating', '-review_count', '-id')
    elif sort == 'popular':
        filtered = filtered.order_by('-review_count', '-avg_rating', '-id')
    else:
        filtered = filtered.order_by('-id')

    paginator = Paginator(filtered, 9)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'new_arrivals.html', {
        'all_arrivals': page_obj,
        'selected_category': category,
        'search_query': search,
        'selected_sort': sort,
        'is_paginated': paginator.num_pages > 1,
        'total_arrivals': arrivals_qs.count(),
        'total_filtered': filtered.count(),
        'kids_count': arrivals_qs.filter(category='kids').count(),
        'men_count': arrivals_qs.filter(category='men').count(),
        'women_count': arrivals_qs.filter(category='women').count(),
    })


# Authentication views
def user_login(request):
    # Check if user is being redirected from cart or other protected page
    next_url = request.GET.get('next', '')
    if next_url and 'cart' in next_url.lower():
        # Show info message only when coming from cart
        pass  # Message will be shown after POST if login fails
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            auth_login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Transfer session cart to user cart
            if not request.session.session_key:
                request.session.create()
            session_key = request.session.session_key
            
            try:
                session_cart = Cart.objects.get(session_key=session_key, user__isnull=True)
                user_cart, created = Cart.objects.get_or_create(user=user)
                
                # Move items from session cart to user cart
                for item in session_cart.items.all():
                    item.cart = user_cart
                    item.save()
                
                session_cart.delete()
            except Cart.DoesNotExist:
                pass
            
            next_url = request.POST.get('next', 'index')
            if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                next_url = 'index'
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password')
    
    # Show message if coming from cart
    if 'cart' in next_url.lower():
        messages.info(request, 'Please login to view your cart')
    
    return render(request, 'login.html')


def user_signup(request):
    def render_signup_with_data(data=None):
        return render(request, 'signup.html', {
            'signup_data': data or {},
        })

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        signup_data = {
            'username': (request.POST.get('username') or '').strip(),
            'full_name': (request.POST.get('full_name') or '').strip(),
            'email': (request.POST.get('email') or '').strip(),
            'address': (request.POST.get('address') or '').strip(),
            'phone': (request.POST.get('phone') or '').strip(),
        }
        
        if password != password2:
            messages.error(request, 'Passwords do not match')
            return render_signup_with_data(signup_data)
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render_signup_with_data(signup_data)
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered')
            return render_signup_with_data(signup_data)
        
        # Validate password strength
        try:
            validate_password(password, user=User(username=username, email=email))
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, error)
            return render_signup_with_data(signup_data)
        
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        
        auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, 'Account created successfully!')
        return redirect('index')
    
    return render_signup_with_data()


@require_POST
def user_logout(request):
    auth_logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('index')


def profile(request):
    if not request.user.is_authenticated:
        messages.warning(request, 'Please login to view your profile')
        return redirect('login')
    
    # Get user's order count
    order_count = Order.objects.filter(user=request.user).count()
    
    # Get user's review count (reviews by this user's email or name)
    review_count = Review.objects.filter(email=request.user.email).count()
    
    # Get user's wishlist count
    wishlist_count = WishlistItem.objects.filter(user=request.user).count()
    
    # Get recent reviews by user
    user_reviews = Review.objects.filter(email=request.user.email)[:5]
    
    # Get cart count for navigation
    cart_count = 0
    try:
        cart = Cart.objects.get(user=request.user)
        cart_count = cart.get_item_count()
    except Cart.DoesNotExist:
        cart_count = 0
    
    # Calculate satisfaction (mock - could be based on actual data)
    satisfaction = "98%"
    if order_count == 0:
        satisfaction = "N/A"
    
    context = {
        'order_count': order_count,
        'review_count': review_count,
        'wishlist_count': wishlist_count,
        'user_reviews': user_reviews,
        'cart_count': cart_count,
        'satisfaction': satisfaction,
    }
    
    return render(request, 'profile.html', context)

def product_detail(request, product_type, product_id):
    product = None
    back_url = '/'
    back_label = 'Home'
    category_label = ''
    related_products = []
    cart_count = 0

    # Get cart count
    cart = get_or_create_cart(request)
    cart_count = cart.get_item_count()

    # ── Fetch the product ──
    if product_type == 'offer':
        product = get_object_or_404(Offers, id=product_id)
        back_url = '/shop-offers/'
        back_label = 'Shop Offers'
        category_label = product.get_category_display() if product.category else 'Offer'
        related_products = list(
            Offers.objects.filter(category=product.category).exclude(id=product.id)[:4]
        )
    elif product_type == 'arrival':
        product = get_object_or_404(NewArrivals, id=product_id)
        back_url = '/new_arrivals/'
        back_label = 'New Arrivals'
        category_label = product.get_category_display() if product.category else 'Arrival'
        related_products = list(
            NewArrivals.objects.filter(category=product.category).exclude(id=product.id)[:4]
        )
    elif product_type == 'toy':
        product = get_object_or_404(Toy, id=product_id)
        back_url = '/toys/'
        back_label = 'Toys'
        category_label = product.get_category_display()
        related_products = list(
            Toy.objects.filter(category=product.category).exclude(id=product.id)[:4]
        )
    elif product_type == 'cloth':
        product = get_object_or_404(Cloths, id=product_id)
        cat = product.category
        if cat in ('kids-men', 'kids-girl'):
            back_url = '/kids_cloths/'
            back_label = 'Kids Cloths'
        elif cat == 'women':
            back_url = '/women_cloths/'
            back_label = "Women's Cloths"
        else:
            back_url = '/mens_cloths/'
            back_label = "Men's Cloths"
        category_label = product.get_category_display()
        related_products = list(
            Cloths.objects.filter(category=product.category).exclude(id=product.id)[:4]
        )
    else:
        messages.error(request, 'Invalid product type')
        return redirect('index')

    # ── Reviews ──
    fk_field = product_type  # FK field name matches product_type: cloth, toy, offer, arrival
    reviews = ProductReview.objects.filter(product_type=product_type, **{fk_field: product})
    review_count = reviews.count()
    avg_rating = 0
    if review_count:
        avg_rating = round(sum(r.rating for r in reviews) / review_count, 1)
    rating_dist = {i: reviews.filter(rating=i).count() for i in range(5, 0, -1)}

    # ── Handle review POST ──
    review_error = ''
    if request.method == 'POST':
        r_name = request.POST.get('reviewer_name', '').strip()
        r_rating = request.POST.get('review_rating')
        r_title = request.POST.get('review_title', '').strip()
        r_comment = request.POST.get('review_comment', '').strip()
        if r_name and r_rating and r_comment:
            ProductReview.objects.create(
                product_type=product_type,
                **{fk_field: product},
                user=request.user if request.user.is_authenticated else None,
                name=r_name,
                rating=int(r_rating),
                title=r_title,
                comment=r_comment,
            )
            return redirect('product_detail', product_type=product_type, product_id=product_id)
        else:
            review_error = 'Please fill in your name, rating, and comment.'

    # ── Check wishlist ──
    in_wishlist = False
    if request.user.is_authenticated and product_type in ('cloth', 'toy'):
        fk = {'cloth': product} if product_type == 'cloth' else {'toy': product}
        in_wishlist = WishlistItem.objects.filter(user=request.user, **fk).exists()

    # Normalize name (Offers/NewArrivals use 'title', Cloths/Toy use 'name')
    product_name = getattr(product, 'name', '') or getattr(product, 'title', '')

    # Normalize description (Cloths model has typo 'desccription')
    product_description = getattr(product, 'description', '') or getattr(product, 'desccription', '')

    # Rich detail fields for the Detail tab
    long_description = getattr(product, 'long_description', '') or ''
    features_raw = getattr(product, 'features', '') or ''
    features_list = [f.strip() for f in features_raw.split('\n') if f.strip()] if features_raw else []
    material = getattr(product, 'material', '') or ''
    care_instructions = getattr(product, 'care_instructions', '') or ''
    sizes_available = getattr(product, 'sizes_available', '') or ''
    safety_info = getattr(product, 'safety_info', '') or ''
    dimensions = getattr(product, 'dimensions', '') or ''

    # Normalize price (Offers/NewArrivals have price2/price1, Cloths have price1, Toys have price)
    product_display_price = getattr(product, 'price2', None) or getattr(product, 'price1', None) or getattr(product, 'price', '') or ''

    # ── Gallery images ──
    gallery_images = ProductImage.objects.filter(product_type=product_type, **{fk_field: product})

    # ── Product variants (cloth only) ──
    variants = []
    if product_type == 'cloth':
        variants = list(product.variants.all())

    # ── Inventory status ──
    inventory = None
    try:
        inventory = product.inventory
    except Exception:
        pass

    # ── Ratings summary ──
    rating_summary = reviews.aggregate(avg=Avg('rating'), count=Count('id'))
    avg_rating = round(rating_summary['avg'], 1) if rating_summary['avg'] else 0
    review_count = rating_summary['count']
    rating_dist = {i: reviews.filter(rating=i).count() for i in range(5, 0, -1)}

    return render(request, 'product_detail.html', {
        'product': product,
        'product_type': product_type,
        'product_name': product_name,
        'product_description': product_description,
        'back_url': back_url,
        'back_label': back_label,
        'category_label': category_label,
        'related_products': related_products,
        'reviews': reviews,
        'review_count': review_count,
        'avg_rating': avg_rating,
        'rating_dist': rating_dist,
        'review_error': review_error,
        'in_wishlist': in_wishlist,
        'cart_count': cart_count,
        'long_description': long_description,
        'features_list': features_list,
        'material': material,
        'care_instructions': care_instructions,
        'sizes_available': sizes_available,
        'safety_info': safety_info,
        'dimensions': dimensions,
        'gallery_images': gallery_images,
        'variants': variants,
        'inventory': inventory,
        'product_display_price': product_display_price,
    })


def cloths(request):
    queryset = Cloths.objects.all().annotate(
        avg_rating=Avg('product_reviews__rating'),
        review_count=Count('product_reviews'),
    )

    search = request.GET.get('q', '').strip()
    category = request.GET.get('category', 'all')
    subcategory = request.GET.get('subcategory', 'all')
    sort = request.GET.get('sort', 'featured')

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(desccription__icontains=search)
            | Q(subcategory__icontains=search)
        )

    if category == 'kids':
        queryset = queryset.filter(category__in=['kids-men', 'kids-girl'])
    elif category in ['men', 'women', 'kids-men', 'kids-girl']:
        queryset = queryset.filter(category=category)

    if subcategory and subcategory != 'all':
        queryset = queryset.filter(subcategory=subcategory)

    items = list(queryset)
    for item in items:
        item.numeric_price = parse_catalog_price(item.price2 or item.price1 or item.price)

    if sort == 'price_asc':
        items.sort(key=lambda item: item.numeric_price)
    elif sort == 'price_desc':
        items.sort(key=lambda item: item.numeric_price, reverse=True)
    elif sort == 'name_asc':
        items.sort(key=lambda item: item.name.lower())
    elif sort == 'name_desc':
        items.sort(key=lambda item: item.name.lower(), reverse=True)
    elif sort == 'oldest':
        items.sort(key=lambda item: item.id)
    else:
        items.sort(key=lambda item: item.id, reverse=True)

    paginator = Paginator(items, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    top_rated_qs = Cloths.objects.annotate(
        avg_rating=Avg('product_reviews__rating'),
        review_count=Count('product_reviews'),
    ).filter(review_count__gt=0).order_by('-avg_rating', '-review_count', '-id')[:4]

    recommended_qs = Cloths.objects.annotate(
        avg_rating=Avg('product_reviews__rating'),
        review_count=Count('product_reviews'),
    )

    if category == 'kids':
        recommended_qs = recommended_qs.filter(category__in=['kids-men', 'kids-girl'])
    elif category in ['men', 'women', 'kids-men', 'kids-girl']:
        recommended_qs = recommended_qs.filter(category=category)

    if subcategory and subcategory != 'all':
        recommended_qs = recommended_qs.filter(subcategory=subcategory)

    recommended_items = list(recommended_qs.exclude(id__in=[item.id for item in page_obj]).order_by('-id')[:8])
    if len(recommended_items) < 8:
        fallback_items = Cloths.objects.annotate(
            avg_rating=Avg('product_reviews__rating'),
            review_count=Count('product_reviews'),
        ).exclude(id__in=[item.id for item in recommended_items]).order_by('-id')[:8 - len(recommended_items)]
        recommended_items.extend(list(fallback_items))

    for item in top_rated_qs:
        item.numeric_price = parse_catalog_price(item.price2 or item.price1 or item.price)
    for item in recommended_items:
        item.numeric_price = parse_catalog_price(item.price2 or item.price1 or item.price)

    all_items = Cloths.objects.all()
    category_counts = {
        'men': all_items.filter(category='men').count(),
        'women': all_items.filter(category='women').count(),
        'kids': all_items.filter(category__in=['kids-men', 'kids-girl']).count(),
    }

    available_subcategories = set(
        Cloths.objects.exclude(subcategory='').values_list('subcategory', flat=True)
    )
    subcategory_options = [
        option for option in Cloths.SUBCATEGORY_CHOICES
        if option[0] and option[0] in available_subcategories
    ]

    prices = [item.numeric_price for item in items if item.numeric_price > 0]
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 0

    cart_count = 0
    try:
        cart_count = get_or_create_cart(request).get_item_count()
    except Exception:
        cart_count = 0

    return render(request, 'cloths.html', {
        'cloths_items': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'selected_category': category,
        'selected_subcategory': subcategory,
        'selected_sort': sort,
        'search_query': search,
        'subcategory_options': subcategory_options,
        'category_counts': category_counts,
        'products_count': len(items),
        'price_min': min_price,
        'price_max': max_price,
        'top_rated_products': top_rated_qs,
        'recommended_products': recommended_items,
        'cart_count': cart_count,
    })

def toys(request):  
    return render(request, 'toys.html')

    
def kids_cloths(request):
    def parse_price(raw_value):
        if raw_value is None:
            return 0.0
        text = str(raw_value).strip()
        if not text:
            return 0.0
        text = re.sub(r'[^0-9,.-]', '', text).replace(',', '')
        try:
            return float(text) if text else 0.0
        except ValueError:
            return 0.0

    def parse_float(raw_value):
        try:
            return float(raw_value)
        except (TypeError, ValueError):
            return None

    gender = request.GET.get('gender', 'all')
    subcategory = request.GET.get('subcategory', 'all')
    sort = request.GET.get('sort', 'featured')
    min_price = parse_float(request.GET.get('min_price'))
    max_price = parse_float(request.GET.get('max_price'))
    search = request.GET.get('q', '').strip()

    kids_queryset = Cloths.objects.filter(category__in=['kids-men', 'kids-girl']).annotate(avg_rating=Avg('product_reviews__rating'), review_count=Count('product_reviews'))

    if gender in ['kids-men', 'kids-girl']:
        kids_queryset = kids_queryset.filter(category=gender)

    if subcategory and subcategory != 'all':
        kids_queryset = kids_queryset.filter(subcategory=subcategory)

    if search:
        kids_queryset = kids_queryset.filter(name__icontains=search)

    all_filtered_items = list(kids_queryset)

    for item in all_filtered_items:
        item.numeric_price = parse_price(item.price2 or item.price1 or item.price)

    if min_price is not None:
        all_filtered_items = [item for item in all_filtered_items if item.numeric_price >= min_price]
    if max_price is not None:
        all_filtered_items = [item for item in all_filtered_items if item.numeric_price <= max_price]

    if sort == 'price_asc':
        all_filtered_items.sort(key=lambda item: item.numeric_price)
    elif sort == 'price_desc':
        all_filtered_items.sort(key=lambda item: item.numeric_price, reverse=True)
    elif sort == 'name_asc':
        all_filtered_items.sort(key=lambda item: item.name.lower())
    elif sort == 'name_desc':
        all_filtered_items.sort(key=lambda item: item.name.lower(), reverse=True)
    elif sort == 'newest':
        all_filtered_items.sort(key=lambda item: item.id, reverse=True)
    elif sort == 'oldest':
        all_filtered_items.sort(key=lambda item: item.id)
    else:
        all_filtered_items.sort(key=lambda item: item.id, reverse=True)

    kids_girls_cloths = [item for item in all_filtered_items if item.category == 'kids-girl']
    kids_cloths = [item for item in all_filtered_items if item.category == 'kids-men']

    # Pagination
    paginator = Paginator(all_filtered_items, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    cart_count = 0
    try:
        cart_count = get_or_create_cart(request).get_item_count()
    except Exception:
        cart_count = 0

    subcategory_options = [
        option for option in Cloths.SUBCATEGORY_CHOICES if option[0]
    ]

    return render(request, 'kids_cloths.html', {
        'kids_cloths': kids_cloths,
        'kids_girls_cloths': kids_girls_cloths,
        'all_kids_cloths': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'selected_gender': gender,
        'selected_subcategory': subcategory,
        'selected_sort': sort,
        'selected_min_price': request.GET.get('min_price', ''),
        'selected_max_price': request.GET.get('max_price', ''),
        'search_query': search,
        'subcategory_options': subcategory_options,
        'cart_count': cart_count,
    })

def women_cloths(request):
    base_queryset = Cloths.objects.filter(category='women').annotate(avg_rating=Avg('product_reviews__rating'), review_count=Count('product_reviews'))

    search = request.GET.get('q', '').strip()
    subcategory = request.GET.get('subcategory', 'all')
    sort = request.GET.get('sort', 'featured')
    min_price = parse_query_float(request.GET.get('min_price'))
    max_price = parse_query_float(request.GET.get('max_price'))

    filtered = base_queryset
    if search:
        filtered = filtered.filter(name__icontains=search)
    if subcategory and subcategory != 'all':
        filtered = filtered.filter(subcategory=subcategory)

    products = list(filtered)
    for product in products:
        product.numeric_price = parse_catalog_price(product.price2 or product.price1 or product.price)

    if min_price is not None:
        products = [product for product in products if product.numeric_price >= min_price]
    if max_price is not None:
        products = [product for product in products if product.numeric_price <= max_price]

    if sort == 'price_asc':
        products.sort(key=lambda item: item.numeric_price)
    elif sort == 'price_desc':
        products.sort(key=lambda item: item.numeric_price, reverse=True)
    elif sort == 'name_asc':
        products.sort(key=lambda item: item.name.lower())
    elif sort == 'name_desc':
        products.sort(key=lambda item: item.name.lower(), reverse=True)
    elif sort == 'oldest':
        products.sort(key=lambda item: item.id)
    else:
        products.sort(key=lambda item: item.id, reverse=True)

    sections_map = {}
    for item in products:
        slug = item.subcategory if item.subcategory else 'styles'
        label = item.get_subcategory_display() if item.subcategory else 'Featured Styles'
        if slug not in sections_map:
            sections_map[slug] = {
                'slug': slug,
                'label': label,
                'items': [],
            }
        sections_map[slug]['items'].append(item)

    sections = list(sections_map.values())
    sections.sort(key=lambda entry: entry['label'].lower())

    subcategory_values = set(base_queryset.values_list('subcategory', flat=True))
    filter_subcategories = [
        option for option in Cloths.SUBCATEGORY_CHOICES
        if option[0] and option[0] in subcategory_values
    ]

    cart_count = 0
    try:
        cart_count = get_or_create_cart(request).get_item_count()
    except Exception:
        cart_count = 0

    # Pagination
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'women_cloths.html', {
        'women_cloths': page_obj,
        'sections': sections,
        'filter_subcategories': filter_subcategories,
        'selected_subcategory': subcategory,
        'selected_sort': sort,
        'selected_min_price': request.GET.get('min_price', ''),
        'selected_max_price': request.GET.get('max_price', ''),
        'search_query': search,
        'cart_count': cart_count,
        'is_paginated': paginator.num_pages > 1,
    })


def mens_cloths(request):
    base_queryset = Cloths.objects.filter(category='men').annotate(avg_rating=Avg('product_reviews__rating'), review_count=Count('product_reviews'))

    search = request.GET.get('q', '').strip()
    subcategory = request.GET.get('subcategory', 'all')
    sort = request.GET.get('sort', 'featured')
    min_price = parse_query_float(request.GET.get('min_price'))
    max_price = parse_query_float(request.GET.get('max_price'))

    filtered = base_queryset
    if search:
        filtered = filtered.filter(name__icontains=search)
    if subcategory and subcategory != 'all':
        filtered = filtered.filter(subcategory=subcategory)

    products = list(filtered)
    for product in products:
        product.numeric_price = parse_catalog_price(product.price2 or product.price1 or product.price)

    if min_price is not None:
        products = [product for product in products if product.numeric_price >= min_price]
    if max_price is not None:
        products = [product for product in products if product.numeric_price <= max_price]

    if sort == 'price_asc':
        products.sort(key=lambda item: item.numeric_price)
    elif sort == 'price_desc':
        products.sort(key=lambda item: item.numeric_price, reverse=True)
    elif sort == 'name_asc':
        products.sort(key=lambda item: item.name.lower())
    elif sort == 'name_desc':
        products.sort(key=lambda item: item.name.lower(), reverse=True)
    elif sort == 'oldest':
        products.sort(key=lambda item: item.id)
    else:
        products.sort(key=lambda item: item.id, reverse=True)

    sections_map = {}
    for item in products:
        slug = item.subcategory if item.subcategory else 'styles'
        label = item.get_subcategory_display() if item.subcategory else 'Featured Styles'
        if slug not in sections_map:
            sections_map[slug] = {
                'slug': slug,
                'label': label,
                'items': [],
            }
        sections_map[slug]['items'].append(item)

    sections = list(sections_map.values())
    sections.sort(key=lambda entry: entry['label'].lower())

    subcategory_values = set(base_queryset.values_list('subcategory', flat=True))
    filter_subcategories = [
        option for option in Cloths.SUBCATEGORY_CHOICES
        if option[0] and option[0] in subcategory_values
    ]

    cart_count = 0
    try:
        cart_count = get_or_create_cart(request).get_item_count()
    except Exception:
        cart_count = 0

    # Pagination
    paginator = Paginator(products, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'mens_cloths.html', {
        'mens_cloths': page_obj,
        'sections': sections,
        'filter_subcategories': filter_subcategories,
        'selected_subcategory': subcategory,
        'selected_sort': sort,
        'selected_min_price': request.GET.get('min_price', ''),
        'selected_max_price': request.GET.get('max_price', ''),
        'search_query': search,
        'cart_count': cart_count,
        'is_paginated': paginator.num_pages > 1,
    })

def reviews(request):
    cart_count = 0
    try:
        cart_count = get_or_create_cart(request).get_item_count()
    except Exception:
        cart_count = 0

    if request.method == 'POST':
        is_ajax = _wants_json(request)
        if not request.user.is_authenticated:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Please log in to submit a review.',
                    'login_url': f'/login/?next={request.path}',
                }, status=401)
            messages.error(request, 'Please log in to submit a review.')
            return redirect(f'/login/?next={request.path}')
        form = ReviewForm(request.POST, request.FILES)
        if form.is_valid():
            review = form.save()
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'review': {
                        'name': review.name,
                        'rating': review.rating,
                        'rating_label': review.get_rating_display(),
                        'comment': review.comment,
                        'created_at': review.created_at.strftime('%b %d, %Y'),
                        'image_url': review.uploadImages.url if review.uploadImages else '',
                    }
                })
            messages.success(request, 'Review submitted successfully!')
            return redirect('/reviews/#reviewsList')
        if is_ajax:
            first_error = 'Please check your inputs and try again.'
            if form.errors:
                first_error = next(iter(form.errors.values()))[0]
            return JsonResponse({'success': False, 'message': str(first_error)})
    else:
        form = ReviewForm()
    
    # Get latest 20 reviews
    latest_reviews = Review.objects.all()[:20]
    
    return render(request, 'reviews.html', {'form': form, 'latest_reviews': latest_reviews, 'cart_count': cart_count})

def review_success(request):
    return render(request, 'review_success.html')


def service_reviews(request):
    cart_count = 0
    try:
        cart_count = get_or_create_cart(request).get_item_count()
    except Exception:
        cart_count = 0

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to submit a service review.')
            return redirect(f'/login/?next={request.path}')
        form = ServiceReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            email = (form.cleaned_data.get('email') or '').strip().lower()
            verified = False

            if request.user.is_authenticated and Order.objects.filter(user=request.user).exists():
                verified = True
            elif email and Order.objects.filter(email__iexact=email).exists():
                verified = True

            review.is_verified_customer = verified
            review.is_approved = verified
            review.save()

            if verified:
                messages.success(request, 'Thanks! Your verified service review is now live.')
            else:
                messages.info(request, 'Thanks! Your review was submitted and is waiting for admin approval.')

            return redirect('service_reviews')
    else:
        form = ServiceReviewForm()

    topic = request.GET.get('topic', 'all')
    sort = request.GET.get('sort', 'newest')
    only_verified = request.GET.get('verified', '0') == '1'
    min_rating_raw = request.GET.get('min_rating', '0')

    try:
        min_rating = float(min_rating_raw)
    except (TypeError, ValueError):
        min_rating = 0

    reviews_qs = ServiceReview.objects.filter(is_approved=True)

    if topic in {'overall', 'delivery', 'packaging', 'support', 'returns'}:
        reviews_qs = reviews_qs.filter(topic=topic)

    if only_verified:
        reviews_qs = reviews_qs.filter(is_verified_customer=True)

    if min_rating > 0:
        reviews_qs = reviews_qs.filter(overall_rating__gte=min_rating)

    if sort == 'helpful':
        reviews_qs = reviews_qs.order_by('-helpful_count', '-created_at')
    elif sort == 'highest':
        reviews_qs = reviews_qs.order_by('-overall_rating', '-created_at')
    else:
        reviews_qs = reviews_qs.order_by('-created_at')

    paginator = Paginator(reviews_qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    aggregate = ServiceReview.objects.filter(is_approved=True).aggregate(
        average_rating=Avg('overall_rating'),
        total=Count('id'),
    )

    avg_rating = round(float(aggregate.get('average_rating') or 0), 1)
    total_reviews = int(aggregate.get('total') or 0)

    return render(request, 'service_reviews.html', {
        'form': form,
        'service_reviews': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'selected_topic': topic,
        'selected_sort': sort,
        'selected_verified': only_verified,
        'selected_min_rating': min_rating,
        'avg_rating': avg_rating,
        'total_reviews': total_reviews,
        'cart_count': cart_count,
    })


@require_POST
def service_review_helpful(request, review_id):
    review = get_object_or_404(ServiceReview, id=review_id, is_approved=True)
    session_key = f'service_review_helpful_{review_id}'

    if request.session.get(session_key):
        return JsonResponse({'success': False, 'message': 'Already voted', 'helpful_count': review.helpful_count})

    review.helpful_count = (review.helpful_count or 0) + 1
    review.save(update_fields=['helpful_count'])
    request.session[session_key] = True

    return JsonResponse({'success': True, 'helpful_count': review.helpful_count})


def contact_us(request):
    cart_count = 0
    try:
        cart_count = get_or_create_cart(request).get_item_count()
    except Exception:
        cart_count = 0

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you! We received your message and will get back to you soon.')
            return redirect('contact_success')
    else:
        form = ContactForm()
    
    return render(request, 'contact.html', {
        'form': form,
        'cart_count': cart_count,
    })

def contact_success(request):
    cart_count = 0
    try:
        cart_count = get_or_create_cart(request).get_item_count()
    except Exception:
        cart_count = 0

    return render(request, 'contact_success.html', {
        'cart_count': cart_count,
    })


def toys_page(request):
    # Get filter parameters
    category = request.GET.get('category', 'all')
    age_range = request.GET.get('age', 'all')
    
    # Filter toys
    toys = Toy.objects.all().annotate(avg_rating=Avg('product_reviews__rating'), review_count=Count('product_reviews')).order_by('-id')
    
    if category != 'all':
        toys = toys.filter(category=category)
    
    if age_range != 'all':
        toys = toys.filter(age_range=age_range)
    
    # Get featured toys
    featured_toys = Toy.objects.filter(is_bestseller=True).annotate(avg_rating=Avg('product_reviews__rating'), review_count=Count('product_reviews'))[:4]
    new_toys = Toy.objects.filter(is_new=True).annotate(avg_rating=Avg('product_reviews__rating'), review_count=Count('product_reviews'))[:4]
    
    # Pagination
    paginator = Paginator(toys, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'toys': page_obj,
        'featured_toys': featured_toys,
        'new_toys': new_toys,
        'selected_category': category,
        'selected_age': age_range,
        'is_paginated': paginator.num_pages > 1,
    }
    
    return render(request, 'toys.html', context)


# Cart views
def cart_page(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    
    items_data = []
    for item in cart_items:
        product = item.get_item()
        items_data.append({
            'id': item.id,
            'name': product.name if hasattr(product, 'name') else product.title,
            'price': item.get_price(),
            'quantity': item.quantity,
            'subtotal': item.get_subtotal(),
            'image': product.imageUrl.url if product.imageUrl else '',
            'item_type': item.item_type,
        })
    
    context = {
        'cart_items': items_data,
        'cart_count': cart.get_item_count(),
        'subtotal': cart.get_total(),
        'tax': float(cart.get_total()) * 0.1,
        'total': float(cart.get_total()) * 1.1,
    }
    
    return render(request, 'cart.html', context)


def _wants_json(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')

def add_to_cart(request, item_type, item_id):
    try:
        cart = get_or_create_cart(request)
        
        # Get the product based on item_type
        item = None
        if item_type == 'cloth':
            item = get_object_or_404(Cloths, id=item_id)
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                item_type='cloth',
                cloth=item,
                defaults={'quantity': 1}
            )
        elif item_type == 'toy':
            item = get_object_or_404(Toy, id=item_id)
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                item_type='toy',
                toy=item,
                defaults={'quantity': 1}
            )
        elif item_type == 'offer':
            item = get_object_or_404(Offers, id=item_id)
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                item_type='offer',
                offer=item,
                defaults={'quantity': 1}
            )
        elif item_type == 'arrival':
            item = get_object_or_404(NewArrivals, id=item_id)
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                item_type='arrival',
                arrival=item,
                defaults={'quantity': 1}
            )
        else:
            if _wants_json(request):
                return JsonResponse({'success': False, 'error': 'Invalid item type'}, status=400)
            messages.error(request, 'Invalid item type')
            return redirect(request.META.get('HTTP_REFERER', 'index'))

        if not created:
            cart_item.quantity += 1
            cart_item.save()

        item_name = item.name if hasattr(item, 'name') else item.title
        success_msg = f'✓ Added {item_name} to cart!'

        if request.method == 'POST' or _wants_json(request):
            return JsonResponse({
                'success': True,
                'message': success_msg,
                'cart_count': cart.get_item_count(),
                'cart_total': float(cart.get_total())
            })

        messages.success(request, success_msg)
        return redirect(request.META.get('HTTP_REFERER', 'cart'))

    except Exception as e:
        if request.method == 'POST' or _wants_json(request):
            return JsonResponse({'success': False, 'error': 'Something went wrong. Please try again.'}, status=500)
        messages.error(request, 'Something went wrong. Please try again.')
        return redirect(request.META.get('HTTP_REFERER', 'index'))


@require_POST
def update_cart_item(request, cart_item_id):
    try:
        data = json.loads(request.body)
        quantity = int(data.get('quantity', 1))
        
        if quantity < 1:
            return JsonResponse({'success': False, 'error': 'Quantity must be at least 1'}, status=400)
        
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart=cart)
        
        cart_item.quantity = quantity
        cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Cart updated',
            'cart_count': cart.get_item_count(),
            'cart_total': float(cart.get_total()),
            'item_subtotal': float(cart_item.get_subtotal())
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
def remove_from_cart(request, cart_item_id):
    try:
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart=cart)
        
        item = cart_item.get_item()
        item_name = item.name if hasattr(item, 'name') else item.title
        
        cart_item.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Removed {item_name} from cart',
            'cart_count': cart.get_item_count(),
            'cart_total': float(cart.get_total())
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
def clear_cart(request):
    try:
        cart = get_or_create_cart(request)
        cart.items.all().delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Cart cleared',
            'cart_count': 0,
            'cart_total': 0
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def get_cart_data(request):
    """API endpoint to get cart data as JSON"""
    try:
        cart = get_or_create_cart(request)
        items_data = []

        for item in cart.items.all():
            try:
                product = item.get_item()
                if not product:
                    continue
                product_name = product.name if hasattr(product, 'name') else product.title
                product_url = f'/product/{item.item_type}/{product.id}/'
                items_data.append({
                    'id': item.id,
                    'name': product_name,
                    'price': float(item.get_price()),
                    'quantity': int(item.quantity),
                    'subtotal': float(item.get_subtotal()),
                    'image': product.imageUrl.url if getattr(product, 'imageUrl', None) else '',
                    'item_type': item.item_type,
                    'product_url': product_url,
                })
            except Exception:
                continue

        subtotal = float(cart.get_total())
        tax = round(subtotal * 0.1, 2)
        total = round(subtotal + tax, 2)

        return JsonResponse({
            'success': True,
            'items': items_data,
            'cart_count': cart.get_item_count(),
            'subtotal': round(subtotal, 2),
            'tax': tax,
            'total': total
        })

    except Exception as e:
        return JsonResponse({
            'success': True,  # keep frontend alive, show empty cart instead of breaking
            'items': [],
            'cart_count': 0,
            'subtotal': 0.0,
            'tax': 0.0,
            'total': 0.0,
            'error': str(e),
        })


def cart_details(request):
    cart = get_or_create_cart(request)
    return render(request, 'cart_details_page.html', {
        'cart': cart,
        'cart_count': cart.get_item_count(),
    })


# Wishlist views
@login_required(login_url='login')
def wishlist(request):
    wishlist_items = WishlistItem.objects.filter(user=request.user).select_related('cloth', 'toy')

    cloth_items = wishlist_items.filter(item_type='cloth').select_related('cloth')
    toy_items = wishlist_items.filter(item_type='toy').select_related('toy')
    
    total_count = wishlist_items.count()
    cloth_count = cloth_items.count()
    toy_count = toy_items.count()
    
    context = {
        'wishlist_items': wishlist_items,
        'cloth_items': cloth_items,
        'toy_items': toy_items,
        'total_count': total_count,
        'cloth_count': cloth_count,
        'toy_count': toy_count,
    }
    
    return render(request, 'wishlist.html', context)
    
    
@login_required(login_url='login')
def add_to_wishlist(request, item_type, item_id):
    try:
        
        if item_type == 'cloth':
            item = get_object_or_404(Cloths, id=item_id)
            
            
            wishlist_item, created = WishlistItem.objects.get_or_create(
                user=request.user,
                item_type='cloth',
                cloth=item
            )
        
        elif item_type == 'toy':
            item = get_object_or_404(Toy, id=item_id)
            
            
            wishlist_item, created = WishlistItem.objects.get_or_create(
                user=request.user,
                item_type='toy',
                toy=item
            )
        
        else:
            messages.error(request, 'Invalid item type')
            return redirect('wishlist')
        
        if created:
            messages.success(request, f'✓ Added {item.name} to wishlist!')
        else:
            messages.info(request, f'{item.name} is already in your wishlist')
            
            
        return redirect('wishlist')
    
    except Cloths.DoesNotExist:
        messages.error(request, 'Cloth product not found')
        return redirect('buy')
    except Toy.DoesNotExist:
        messages.error(request, 'Toy product not found')
        return redirect('toys')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('wishlist')


@login_required(login_url='login')
def remove_from_wishlist(request, wishlist_id):
    try:
        wishlist_item = get_object_or_404(
            WishlistItem,
            id=wishlist_id,
            user=request.user
        )
        
        product_name = wishlist_item.get_item().name
        
        wishlist_item.delete()
        
        messages.success(request, f'✓ Removed {product_name} from wishlist')
    
    except WishlistItem.DoesNotExist:
        messages.error(request, 'Item not found in your wishlist')
    except Exception as e:
        messages.error(request, f'Error removing item: {str(e)}')
    
    return redirect('wishlist')


@login_required(login_url='login')
def move_to_cart(request, wishlist_id):
    try:
        wishlist_item = get_object_or_404(
            WishlistItem,
            id=wishlist_id,
            user=request.user
        )
        
        item = wishlist_item.get_item()
        product_name = item.name
        
        # Add to cart
        cart = get_or_create_cart(request)
        
        if wishlist_item.item_type == 'cloth':
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                item_type='cloth',
                cloth=wishlist_item.cloth,
                defaults={'quantity': 1}
            )
        elif wishlist_item.item_type == 'toy':
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                item_type='toy',
                toy=wishlist_item.toy,
                defaults={'quantity': 1}
            )
        
        if not created:
            cart_item.quantity += 1
            cart_item.save()
        
        # Remove from wishlist
        wishlist_item.delete()
        
        messages.success(request, f'✓ Moved {product_name} to cart!')
    
    except WishlistItem.DoesNotExist:
        messages.error(request, 'Item not found')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    
    return redirect('wishlist')


# Checkout and Order views
@login_required(login_url='login')
def checkout(request):
    cart = get_or_create_cart(request)
    
    if cart.get_item_count() == 0:
        messages.warning(request, 'Your cart is empty')
        return redirect('cart_details')
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()
        country = request.POST.get('country', '').strip()
        payment_method = request.POST.get('payment_method', 'cash_on_delivery')
        coupon_code = request.POST.get('coupon_code', '').strip()
        
        if not all([full_name, email, phone, address, city, postal_code, country]):
            messages.error(request, 'Please fill in all required fields')
            subtotal = Decimal(str(cart.get_total()))
            tax = subtotal * Decimal('0.10')
            shipping = Decimal('10.00')
            return render(request, 'checkout.html', {
                'cart': cart,
                'cart_items': cart.items.all(),
                'subtotal': float(subtotal),
                'tax': float(tax),
                'shipping': float(shipping),
                'total': float(subtotal + tax + shipping),
                'coupons_available': Coupon.objects.filter(is_active=True).exists(),
            })
        
        try:
            # Inventory check
            for cart_item in cart.items.all():
                item = cart_item.get_item()
                if item and hasattr(item, 'inventory'):
                    inv = item.inventory
                    if inv.stock < cart_item.quantity:
                        item_name = getattr(item, 'name', None) or getattr(item, 'title', 'Item')
                        messages.error(request, f'"{item_name}" only has {inv.stock} in stock.')
                        return redirect('cart_details')

            order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
            subtotal = Decimal(str(cart.get_total()))
            
            # Apply coupon
            discount = Decimal('0')
            applied_coupon = ''
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(code__iexact=coupon_code)
                    if coupon.is_valid() and subtotal >= coupon.min_order_amount:
                        discount = Decimal(str(coupon.get_discount(subtotal)))
                        applied_coupon = coupon.code
                        coupon.used_count += 1
                        coupon.save()
                    else:
                        messages.warning(request, 'Coupon is invalid or does not meet minimum order.')
                except Coupon.DoesNotExist:
                    messages.warning(request, 'Invalid coupon code.')
            
            tax = (subtotal - discount) * Decimal('0.10')
            shipping = Decimal('10.00')
            total = subtotal - discount + tax + shipping
            
            order = Order.objects.create(
                user=request.user,
                order_number=order_number,
                full_name=full_name,
                email=email,
                phone=phone,
                address=address,
                city=city,
                postal_code=postal_code,
                country=country,
                subtotal=subtotal,
                tax=tax,
                shipping=shipping,
                discount=discount,
                coupon_code=applied_coupon,
                total=total,
                payment_method=payment_method
            )
            
            # Create order items and reduce inventory
            for cart_item in cart.items.all():
                item = cart_item.get_item()
                item_name = item.name if hasattr(item, 'name') else item.title
                OrderItem.objects.create(
                    order=order,
                    item_name=item_name,
                    item_type=cart_item.item_type,
                    quantity=cart_item.quantity,
                    price=Decimal(str(cart_item.get_price())),
                    subtotal=Decimal(str(cart_item.get_subtotal()))
                )
                # Reduce inventory
                if item and hasattr(item, 'inventory'):
                    inv = item.inventory
                    inv.stock = max(0, inv.stock - cart_item.quantity)
                    inv.save()
            
            # Create initial tracking entry
            OrderTracking.objects.create(order=order, status='pending', note='Order placed successfully.')
            
            # Send order confirmation email
            _send_order_confirmation_email(order)
            
            # Award Loyalty Points
            try:
                points_base = int((subtotal / 100) * 10)
                profile = get_loyalty_profile(request.user)
                
                multiplier = 1.0
                if profile.tier == 'silver':
                    multiplier = 1.5
                elif profile.tier == 'gold':
                    multiplier = 2.0
                
                final_points = int(points_base * multiplier)
                profile.total_points_earned += final_points
                profile.current_points += final_points
                profile.update_tier()
                
                LoyaltyHistory.objects.create(
                    profile=profile,
                    order=order,
                    points=final_points,
                    description=f"Earned from order {order_number}"
                )
            except Exception as e:
                # Fail silently for loyalty to ensure order success is prioritized
                pass
            
            cart.items.all().delete()
            
            messages.success(request, f'Order {order_number} placed successfully!')
            return redirect('order_success', order_number=order_number)
        
        except Exception as e:
            messages.error(request, 'Something went wrong placing your order. Please try again.')
            subtotal = Decimal(str(cart.get_total()))
            tax = subtotal * Decimal('0.10')
            shipping = Decimal('10.00')
            return render(request, 'checkout.html', {
                'cart': cart,
                'cart_items': cart.items.all(),
                'subtotal': float(subtotal),
                'tax': float(tax),
                'shipping': float(shipping),
                'total': float(subtotal + tax + shipping),
                'coupons_available': Coupon.objects.filter(is_active=True).exists(),
            })
    
    subtotal = Decimal(str(cart.get_total()))
    tax = subtotal * Decimal('0.10')
    shipping = Decimal('10.00')
    total = subtotal + tax + shipping
    
    context = {
        'cart': cart,
        'cart_items': cart.items.all(),
        'subtotal': float(subtotal),
        'tax': float(tax),
        'shipping': float(shipping),
        'total': float(total),
        'coupons_available': Coupon.objects.filter(is_active=True).exists(),
    }
    
    return render(request, 'checkout.html', context)


@login_required(login_url='login')
def order_success(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    context = {
        'order': order,
        'order_items': order.items.all()
    }
    
    return render(request, 'order_success.html', context)


# Profile Management Views
@login_required(login_url='login')
def update_profile(request):
    """AJAX endpoint to update user profile"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Update user fields
            user = request.user
            if 'first_name' in data:
                user.first_name = data['first_name']
            if 'last_name' in data:
                user.last_name = data['last_name']
            if 'email' in data:
                # Check if email is already taken by another user
                if User.objects.exclude(pk=user.pk).filter(email=data['email']).exists():
                    return JsonResponse({'success': False, 'error': 'Email already in use'}, status=400)
                user.email = data['email']
            user.save()
            
            return JsonResponse({'success': True, 'message': 'Profile updated successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required(login_url='login')
def change_password(request):
    """AJAX endpoint to change user password"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            current_password = data.get('current_password', '')
            new_password = data.get('new_password', '')
            confirm_password = data.get('confirm_password', '')
            
            user = request.user
            
            # Verify current password
            if not user.check_password(current_password):
                return JsonResponse({'success': False, 'error': 'Current password is incorrect'}, status=400)
            
            # Check password match
            if new_password != confirm_password:
                return JsonResponse({'success': False, 'error': 'New passwords do not match'}, status=400)
            
            # Check password length
            try:
                validate_password(new_password, user=user)
            except ValidationError as e:
                return JsonResponse({'success': False, 'error': ' '.join(e.messages)}, status=400)
            
            # Set new password
            user.set_password(new_password)
            user.save()
            
            # Re-authenticate user to keep them logged in
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            
            return JsonResponse({'success': True, 'message': 'Password changed successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@login_required(login_url='login')
def notification_preferences(request):
    """AJAX endpoint to update notification preferences"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Store notification preferences in session (or could use a UserProfile model)
            request.session['notify_orders'] = data.get('notify_orders', True)
            request.session['notify_promotions'] = data.get('notify_promotions', True)
            request.session['notify_new_arrivals'] = data.get('notify_new_arrivals', True)
            request.session['notify_reviews'] = data.get('notify_reviews', True)
            
            return JsonResponse({'success': True, 'message': 'Notification preferences updated!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    # GET request - return current preferences
    preferences = {
        'notify_orders': request.session.get('notify_orders', True),
        'notify_promotions': request.session.get('notify_promotions', True),
        'notify_new_arrivals': request.session.get('notify_new_arrivals', True),
        'notify_reviews': request.session.get('notify_reviews', True),
    }
    return JsonResponse({'success': True, 'preferences': preferences})


@login_required(login_url='login')
def update_email(request):
    """AJAX endpoint to update user email"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_email = data.get('email', '').strip()
            
            if not new_email:
                return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)
            
            # Validate email format
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, new_email):
                return JsonResponse({'success': False, 'error': 'Invalid email format'}, status=400)
            
            user = request.user
            
            # Check if email is already taken
            if User.objects.exclude(pk=user.pk).filter(email=new_email).exists():
                return JsonResponse({'success': False, 'error': 'Email already in use'}, status=400)
            
            user.email = new_email
            user.save()
            
            return JsonResponse({'success': True, 'message': 'Email updated successfully!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


# ══════════════════════════════════════════════════════
# SEARCH FUNCTIONALITY
# ══════════════════════════════════════════════════════

def search(request):
    query = request.GET.get('q', '').strip()
    results = []

    if query:
        cloths = Cloths.objects.filter(
            Q(name__icontains=query) | Q(desccription__icontains=query)
        )
        toys = Toy.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
        offers = Offers.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
        arrivals = NewArrivals.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

        for item in cloths:
            avg = item.product_reviews.aggregate(avg=Avg('rating'))['avg']
            results.append({
                'name': item.name,
                'price': item.price2 or item.price or item.price1,
                'image': item.imageUrl.url if item.imageUrl else '',
                'url': f'/product/cloth/{item.id}/',
                'type': 'Clothing',
                'rating': round(avg, 1) if avg else None,
            })
        for item in toys:
            avg = item.product_reviews.aggregate(avg=Avg('rating'))['avg']
            results.append({
                'name': item.name,
                'price': str(item.price),
                'image': item.imageUrl.url if item.imageUrl else '',
                'url': f'/product/toy/{item.id}/',
                'type': 'Toy',
                'rating': round(avg, 1) if avg else None,
            })
        for item in offers:
            avg = item.product_reviews.aggregate(avg=Avg('rating'))['avg']
            results.append({
                'name': item.title,
                'price': item.price1,
                'image': item.imageUrl.url if item.imageUrl else '',
                'url': f'/product/offer/{item.id}/',
                'type': 'Offer',
                'rating': round(avg, 1) if avg else None,
            })
        for item in arrivals:
            avg = item.product_reviews.aggregate(avg=Avg('rating'))['avg']
            results.append({
                'name': item.title,
                'price': item.price,
                'image': item.imageUrl.url if item.imageUrl else '',
                'url': f'/product/arrival/{item.id}/',
                'type': 'New Arrival',
                'rating': round(avg, 1) if avg else None,
            })

    paginator = Paginator(results, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = list(page_obj.object_list)
        return JsonResponse({'results': data, 'has_next': page_obj.has_next(), 'total': paginator.count})

    return render(request, 'search_results.html', {
        'query': query,
        'results': page_obj,
        'total': paginator.count,
    })


# ══════════════════════════════════════════════════════
# ORDER TRACKING
# ══════════════════════════════════════════════════════

@login_required(login_url='login')
def order_tracking(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    tracking_updates = order.tracking_updates.all()

    status_steps = ['pending', 'processing', 'shipped', 'delivered']
    current_index = status_steps.index(order.status) if order.status in status_steps else -1

    return render(request, 'order_tracking.html', {
        'order': order,
        'tracking_updates': tracking_updates,
        'status_steps': status_steps,
        'current_index': current_index,
    })


@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.filter(user=request.user)
    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'my_orders.html', {'orders': page_obj})


# ══════════════════════════════════════════════════════
# COUPON VALIDATION (AJAX)
# ══════════════════════════════════════════════════════

def validate_coupon(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '').strip()
            subtotal = Decimal(str(data.get('subtotal', 0)))

            coupon = Coupon.objects.get(code__iexact=code)
            if not coupon.is_valid():
                return JsonResponse({'valid': False, 'error': 'This coupon has expired or is no longer active.'})
            if subtotal < coupon.min_order_amount:
                return JsonResponse({'valid': False, 'error': f'Minimum order amount is Rs. {coupon.min_order_amount}.'})

            discount = coupon.get_discount(subtotal)
            return JsonResponse({
                'valid': True,
                'discount': float(discount),
                'type': coupon.discount_type,
                'value': float(coupon.discount_value),
            })
        except Coupon.DoesNotExist:
            return JsonResponse({'valid': False, 'error': 'Invalid coupon code.'})
        except Exception:
            return JsonResponse({'valid': False, 'error': 'Something went wrong.'})
    return JsonResponse({'valid': False, 'error': 'Invalid request.'})


# ══════════════════════════════════════════════════════
# PRODUCT VARIANTS (AJAX)
# ══════════════════════════════════════════════════════

def get_product_variants(request, product_id):
    variants = ProductVariant.objects.filter(cloth_id=product_id)
    data = [{
        'id': v.id,
        'size': v.size,
        'color': v.color,
        'color_code': v.color_code,
        'extra_price': float(v.extra_price),
        'stock': v.stock,
    } for v in variants]
    return JsonResponse({'variants': data})


# ══════════════════════════════════════════════════════
# ADMIN DASHBOARD (Charts)
# ══════════════════════════════════════════════════════

@staff_member_required(login_url='login')
def admin_dashboard(request):

    from django.db.models.functions import TruncMonth, TruncDate
    from datetime import timedelta
    from django.utils import timezone as tz

    six_months_ago = tz.now() - timedelta(days=180)
    monthly_revenue = list(
        Order.objects.filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=models_sum('total'), count=Count('id'))
        .order_by('month')
    )

    status_counts = {
        s['status']: s['count']
        for s in Order.objects.values('status').annotate(count=Count('id'))
    }

    top_products = list(
        OrderItem.objects.values('item_name')
        .annotate(total_qty=models_sum('quantity'), total_revenue=models_sum('subtotal'))
        .order_by('-total_qty')[:10]
    )
    for p in top_products:
        if p.get('total_revenue') is not None:
            p['total_revenue'] = float(p['total_revenue'])
        if p.get('total_qty') is not None:
            p['total_qty'] = int(p['total_qty'])

    thirty_days_ago = tz.now() - timedelta(days=30)
    daily_orders = list(
        Order.objects.filter(created_at__gte=thirty_days_ago)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('id'), total=models_sum('total'))
        .order_by('date')
    )

    low_stock = Inventory.objects.filter(stock__lte=F('low_stock_threshold'))

    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(total=models_sum('total'))['total'] or 0
    total_users = User.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()

    # Pass recent orders for management
    recent_orders = Order.objects.prefetch_related('user').order_by('-created_at')[:20]

    context = {
        'monthly_labels': json.dumps([m['month'].strftime('%b %Y') for m in monthly_revenue]),
        'monthly_revenue': json.dumps([float(m['total'] or 0) for m in monthly_revenue]),
        'monthly_counts': json.dumps([m['count'] for m in monthly_revenue]),
        'status_counts': json.dumps(status_counts),
        'top_products_json': json.dumps(top_products),
        'top_products': top_products,
        'daily_labels': json.dumps([d['date'].strftime('%d %b') for d in daily_orders]),
        'daily_totals': json.dumps([float(d['total'] or 0) for d in daily_orders]),
        'daily_counts': json.dumps([d['count'] for d in daily_orders]),
        'low_stock': low_stock,
        'total_orders': total_orders,
        'total_revenue': float(total_revenue),
        'total_users': total_users,
        'pending_orders': pending_orders,
        'recent_orders': recent_orders,
    }
    return render(request, 'admin_dashboard.html', context)


# ══════════════════════════════════════════════════════
# ADMIN ORDER UPDATE
# ══════════════════════════════════════════════════════

@login_required(login_url='login')
@require_POST
def admin_update_order_status(request, order_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
        
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        note = data.get('note', '')
        
        valid_statuses = [status[0] for status in Order.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': 'Invalid status provided.'}, status=400)
            
        order = get_object_or_404(Order, id=order_id)
        order.status = new_status
        order.save()
        
        # Create tracking update
        OrderTracking.objects.create(
            order=order,
            status=new_status,
            note=note
        )

        # Automated Email Notification
        if new_status in ['shipped', 'delivered']:
            from django.core.mail import send_mail
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags
            from django.conf import settings
            
            subject = f"KidZone Order Update: #{order.order_number} is now {new_status.title()}"
            html_message = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #6366f1;">Your Order is {new_status.title()}! 🎉</h2>
                <p>Hello {order.full_name},</p>
                <p>Great news! Your order <strong>#{order.order_number}</strong> has been marked as <strong>{new_status.title()}</strong>.</p>
                {f'<p><strong>Note:</strong> {note}</p>' if note else ''}
                {f'<p><strong>Tracking Number:</strong> {order.tracking_number}</p>' if order.tracking_number else ''}
                <p>Thank you for shopping with KidZone!</p>
            </div>
            """
            plain_message = strip_tags(html_message)
            try:
                send_mail(
                    subject,
                    plain_message,
                    getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@kidzone.com'),
                    [order.email],
                    html_message=html_message,
                    fail_silently=True
                )
            except Exception as mail_err:
                pass # Fail silently if email backend is not configured correctly

        return JsonResponse({'success': True, 'message': f'Order {order.order_number} status updated to {order.get_status_display()}'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════
# PAYMENT GATEWAY (Stripe)
# ══════════════════════════════════════════════════════

@login_required(login_url='login')
def payment_page(request):
    """Full-page payment UI with Stripe integration."""
    cart = get_or_create_cart(request)
    if cart.get_item_count() == 0:
        messages.warning(request, 'Your cart is empty')
        return redirect('cart_details')

    items_data = []
    for item in cart.items.all():
        product = item.get_item()
        if product:
            items_data.append({
                'name': getattr(product, 'name', '') or getattr(product, 'title', ''),
                'price': item.get_price(),
                'quantity': item.quantity,
                'subtotal': item.get_subtotal(),
                'image': product.imageUrl.url if getattr(product, 'imageUrl', None) else '',
            })

    subtotal = Decimal(str(cart.get_total()))
    tax = subtotal * Decimal('0.10')
    shipping = Decimal('10.00')
    total = subtotal + tax + shipping

    context = {
        'cart_items': items_data,
        'subtotal': float(subtotal),
        'tax': float(tax),
        'shipping': float(shipping),
        'total': float(total),
        'stripe_publishable_key': django_settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, 'payment.html', context)


@login_required(login_url='login')
@require_POST
def create_checkout_session(request):
    """Create a Stripe checkout session and return the session ID."""
    stripe.api_key = django_settings.STRIPE_SECRET_KEY

    cart = get_or_create_cart(request)
    if cart.get_item_count() == 0:
        return JsonResponse({'error': 'Cart is empty'}, status=400)

    line_items = []
    for item in cart.items.all():
        product = item.get_item()
        if not product:
            continue
        name = getattr(product, 'name', '') or getattr(product, 'title', '')
        price_cents = int(item.get_price() * 100)
        if price_cents <= 0:
            continue
        images = []
        if getattr(product, 'imageUrl', None):
            images = [request.build_absolute_uri(product.imageUrl.url)]
        line_items.append({
            'price_data': {
                'currency': 'lkr',
                'product_data': {'name': name, 'images': images},
                'unit_amount': price_cents,
            },
            'quantity': item.quantity,
        })

    # Add tax and shipping
    subtotal = cart.get_total()
    tax_cents = int(float(subtotal) * 0.10 * 100)
    if tax_cents > 0:
        line_items.append({
            'price_data': {
                'currency': 'lkr',
                'product_data': {'name': 'Tax (10%)'},
                'unit_amount': tax_cents,
            },
            'quantity': 1,
        })
    line_items.append({
        'price_data': {
            'currency': 'lkr',
            'product_data': {'name': 'Shipping'},
            'unit_amount': 1000,
        },
        'quantity': 1,
    })

    try:
        body = json.loads(request.body)
    except Exception:
        body = {}

    # Store shipping info in session for later use
    request.session['checkout_shipping'] = {
        'full_name': body.get('full_name', request.user.get_full_name() or request.user.username),
        'email': body.get('email', request.user.email),
        'phone': body.get('phone', ''),
        'address': body.get('address', ''),
        'city': body.get('city', ''),
        'postal_code': body.get('postal_code', ''),
        'country': body.get('country', ''),
        'coupon_code': body.get('coupon_code', ''),
    }

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri('/payment-success/') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri('/payment-cancel/'),
            customer_email=request.user.email,
            metadata={'user_id': str(request.user.id)},
        )
        return JsonResponse({'sessionId': session.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='login')
def payment_success(request):
    """Handle Stripe redirect after successful payment."""
    session_id = request.GET.get('session_id')
    if not session_id:
        return redirect('index')

    stripe.api_key = django_settings.STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id)
    except Exception:
        messages.error(request, 'Could not verify payment.')
        return redirect('index')

    if session.payment_status != 'paid':
        messages.error(request, 'Payment was not completed.')
        return redirect('payment_page')

    # Check if order already created for this session
    existing = Order.objects.filter(tracking_number=session_id).first()
    if existing:
        return redirect('order_success', order_number=existing.order_number)

    cart = get_or_create_cart(request)
    shipping_info = request.session.pop('checkout_shipping', {})

    order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    subtotal = Decimal(str(cart.get_total()))

    # Apply coupon
    discount = Decimal('0')
    coupon_code = shipping_info.get('coupon_code', '')
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code__iexact=coupon_code)
            if coupon.is_valid() and subtotal >= coupon.min_order_amount:
                discount = Decimal(str(coupon.get_discount(subtotal)))
                coupon.used_count += 1
                coupon.save()
        except Coupon.DoesNotExist:
            pass

    tax = (subtotal - discount) * Decimal('0.10')
    shipping = Decimal('10.00')
    total = subtotal - discount + tax + shipping

    order = Order.objects.create(
        user=request.user,
        order_number=order_number,
        full_name=shipping_info.get('full_name', request.user.username),
        email=shipping_info.get('email', request.user.email),
        phone=shipping_info.get('phone', ''),
        address=shipping_info.get('address', ''),
        city=shipping_info.get('city', ''),
        postal_code=shipping_info.get('postal_code', ''),
        country=shipping_info.get('country', ''),
        subtotal=subtotal,
        tax=tax,
        shipping=shipping,
        discount=discount,
        coupon_code=coupon_code,
        total=total,
        payment_method='stripe',
        tracking_number=session_id,
    )

    for cart_item in cart.items.all():
        item = cart_item.get_item()
        item_name = getattr(item, 'name', '') or getattr(item, 'title', 'Item')
        OrderItem.objects.create(
            order=order,
            item_name=item_name,
            item_type=cart_item.item_type,
            quantity=cart_item.quantity,
            price=Decimal(str(cart_item.get_price())),
            subtotal=Decimal(str(cart_item.get_subtotal())),
        )
        if item and hasattr(item, 'inventory'):
            inv = item.inventory
            inv.stock = max(0, inv.stock - cart_item.quantity)
            inv.save()

    OrderTracking.objects.create(order=order, status='pending', note='Order placed — payment confirmed via Stripe.')

    # Send order confirmation email
    _send_order_confirmation_email(order)

    cart.items.all().delete()
    messages.success(request, f'Payment successful! Order {order_number} placed.')
    return redirect('order_success', order_number=order_number)


@login_required(login_url='login')
def payment_cancel(request):
    messages.warning(request, 'Payment was cancelled. Your cart is still saved.')
    return redirect('cart_details')


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhooks for payment confirmation."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    stripe.api_key = django_settings.STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, django_settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Order is created on redirect; webhook is a safety net
        order = Order.objects.filter(tracking_number=session['id']).first()
        if order and order.status == 'pending':
            order.status = 'processing'
            order.save()
            OrderTracking.objects.create(order=order, status='processing', note='Payment confirmed via webhook.')

    return HttpResponse(status=200)


def _send_order_confirmation_email(order):
    """Send a rich order confirmation email."""
    try:
        subject = f'Order Confirmed — {order.order_number}'
        items = order.items.all()
        items_text = '\n'.join(f"  - {i.quantity}x {i.item_name} — Rs. {i.subtotal}" for i in items)
        message = (
            f"Hi {order.full_name},\n\n"
            f"Your order {order.order_number} has been placed successfully!\n\n"
            f"Items:\n{items_text}\n\n"
            f"Subtotal: Rs. {order.subtotal}\n"
            f"Tax: Rs. {order.tax}\n"
            f"Shipping: Rs. {order.shipping}\n"
        )
        if order.discount > 0:
            message += f"Discount: -Rs. {order.discount}\n"
        message += (
            f"Total: Rs. {order.total}\n\n"
            f"Payment: {order.payment_method}\n"
            f"Shipping to: {order.address}, {order.city}\n\n"
            f"Track your order at: /order-tracking/{order.order_number}/\n\n"
            f"Thank you for shopping with KidZone!"
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            fail_silently=True,
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════
# REORDER
# ══════════════════════════════════════════════════════

@login_required(login_url='login')
def reorder(request, order_number):
    """Re-add all items from a previous order to the cart."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    cart = get_or_create_cart(request)
    added = 0

    for oi in order.items.all():
        item = None
        if oi.item_type == 'cloth':
            item = Cloths.objects.filter(name=oi.item_name).first()
        elif oi.item_type == 'toy':
            item = Toy.objects.filter(name=oi.item_name).first()
        elif oi.item_type == 'offer':
            item = Offers.objects.filter(title=oi.item_name).first()
        elif oi.item_type == 'arrival':
            item = NewArrivals.objects.filter(title=oi.item_name).first()

        if not item:
            continue

        kwargs = {'cart': cart, 'item_type': oi.item_type, oi.item_type: item}
        # For cloth type the FK field is 'cloth'
        fk_field = oi.item_type
        if fk_field == 'arrival':
            kwargs = {'cart': cart, 'item_type': 'arrival', 'arrival': item}
        elif fk_field == 'offer':
            kwargs = {'cart': cart, 'item_type': 'offer', 'offer': item}

        ci, created = CartItem.objects.get_or_create(**kwargs, defaults={'quantity': oi.quantity})
        if not created:
            ci.quantity += oi.quantity
            ci.save()
        added += 1

    if added:
        messages.success(request, f'Added {added} item(s) from order {order_number} to your cart.')
    else:
        messages.warning(request, 'Could not find any of the original products to reorder.')
    return redirect('cart_details')


# ══════════════════════════════════════════════════════
# LIVE STOCK STATUS API
# ══════════════════════════════════════════════════════

def stock_status_api(request):
    """Return current stock levels for all products with inventory."""
    products = []
    for inv in Inventory.objects.select_related('cloth', 'toy', 'offer', 'arrival').all():
        product = inv.get_product()
        if product:
            products.append({
                'type': inv.product_type,
                'id': product.id,
                'stock': inv.stock,
                'threshold': inv.low_stock_threshold,
            })
    return JsonResponse({'products': products})


# ══════════════════════════════════════════════════════
# REST API — Product Listing
# ══════════════════════════════════════════════════════

def api_products(request):
    """Lightweight JSON API for products."""
    product_type = request.GET.get('type', 'all')
    q = request.GET.get('q', '').strip()
    page_num = request.GET.get('page', 1)

    results = []

    if product_type in ('all', 'cloth'):
        qs = Cloths.objects.all()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(desccription__icontains=q))
        for item in qs:
            inv = getattr(item, 'inventory', None)
            results.append({
                'id': item.id, 'type': 'cloth', 'name': item.name,
                'price': item.price2 or item.price or item.price1,
                'image': item.imageUrl.url if item.imageUrl else '',
                'category': item.category,
                'stock': inv.stock if inv else None,
                'url': f'/product/cloth/{item.id}/',
            })

    if product_type in ('all', 'toy'):
        qs = Toy.objects.all()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        for item in qs:
            inv = getattr(item, 'inventory', None)
            results.append({
                'id': item.id, 'type': 'toy', 'name': item.name,
                'price': str(item.price),
                'image': item.imageUrl.url if item.imageUrl else '',
                'category': item.category,
                'stock': inv.stock if inv else None,
                'url': f'/product/toy/{item.id}/',
            })

    if product_type in ('all', 'offer'):
        qs = Offers.objects.all()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        for item in qs:
            inv = getattr(item, 'inventory', None)
            results.append({
                'id': item.id, 'type': 'offer', 'name': item.title,
                'price': item.price2 or item.price1,
                'image': item.imageUrl.url if item.imageUrl else '',
                'category': item.category,
                'stock': inv.stock if inv else None,
                'url': f'/product/offer/{item.id}/',
            })

    paginator = Paginator(results, 12)
    page_obj = paginator.get_page(page_num)

    return JsonResponse({
        'products': list(page_obj.object_list),
        'total': paginator.count,
        'pages': paginator.num_pages,
        'current_page': page_obj.number,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    })


# ── Real-time site update polling endpoint ────────────
def check_updates(request):
    try:
        obj = SiteUpdate.objects.get(pk=1)
        ts = obj.updated_at.isoformat()
    except SiteUpdate.DoesNotExist:
        ts = ''
    return JsonResponse({'ts': ts})
