from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from .models import (Card, Offers, NewArrivals, Cloths, Review, ContactMessage, Toy,
                     WishlistItem, Cart, CartItem, Order, OrderItem, ProductReview,
                     ProductImage, Inventory, Coupon, ProductVariant, OrderTracking,
                     SiteUpdate, ServiceReview, NewsletterSubscription,
                     LoyaltyProfile, LoyaltyHistory, SiteBanner, SiteSettings,
                     ViewHistory, Return, StockAlert, CartAbandon, TrendingProduct)
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
from django.utils import timezone


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


def sort_items_by_stock(items, sort_key=None):
    """
    Separate items into in-stock and out-of-stock groups.
    In-stock items appear first, then out-of-stock items.
    Within each group, items are sorted by the provided sort_key function.
    """
    in_stock = []
    out_of_stock = []
    
    for item in items:
        # Check if item has inventory and if it's in stock
        has_inventory = hasattr(item, 'inventory') and item.inventory
        is_available = has_inventory and item.inventory.stock > 0 if has_inventory else True
        
        if is_available:
            in_stock.append(item)
        else:
            out_of_stock.append(item)
    
    # Sort each group if sort_key provided
    if sort_key:
        in_stock.sort(key=sort_key)
        out_of_stock.sort(key=sort_key)
    
    # Return in-stock items first, then out-of-stock
    return in_stock + out_of_stock


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
    """Smart Concierge AI Assistant Logic via Groq API (Free)"""
    try:
        data = json.loads(request.body)
        query = data.get('message', '').strip()
        
        if not query:
            return JsonResponse({'message': "I'm your G11 shopping assistant! How can I help you today?"})

        api_key = django_settings.GROQ_API_KEY.strip()
        if not api_key:
            return JsonResponse({'message': "I'm currently running in basic mode because my AI brain (Groq API key) isn't configured yet! Please check back soon.", 'products': []})
            
        import urllib.request
        
        # Groq uses an OpenAI-compatible endpoint
        api_url = "https://api.groq.com/openai/v1/chat/completions"
        
        prompt = f"""You are a helpful and friendly ecommerce assistant for G11 Fashion & Toys, a store selling kids clothes, men's clothes, women's clothes, and toys.
    The user says: "{query}"

Analyze the request and return ONLY a valid JSON object matching this exact structure:
{{
    "message": "Your friendly, conversational response to the user. Use emojis! Keep it short and helpful.",
    "search_params": {{
        "keywords": ["list", "of", "search", "keywords"],
        "category": "Identify if they want 'men', 'women', 'kids-men', 'kids-girl', 'toy', or null if unspecified",
        "age_mentions": ["list", "of", "numbers"]
    }}
}}"""
        
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {"role": "system", "content": "You are a helpful ecommerce assistant. Always respond in valid JSON format."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,
            "response_format": {"type": "json_object"},
            "stream": False
        }
        
        ai_data = None

        try:
            req = urllib.request.Request(
                api_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
            )

            import ssl
            context = ssl.create_default_context()
            
            with urllib.request.urlopen(req, timeout=10, context=context) as response:
                result = json.loads(response.read().decode('utf-8'))
                response_text = result['choices'][0]['message']['content'].strip()

            # Clean markdown if model ignores response_format
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            ai_data = json.loads(response_text.strip())
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Groq API Error ({type(e).__name__}): {str(e)}")
            # Log the full traceback for deeper debugging on server
            import traceback
            logger.error(traceback.format_exc())
            ai_data = None

        if not ai_data:
            # Fallback: lightweight local parsing so the assistant still returns products
            lowered = query.lower()
            age_mentions = [int(m) for m in re.findall(r'\b(\d{1,2})\b', lowered)]

            category = None
            if any(word in lowered for word in ['toy', 'toys', 'teddy', 'doll', 'lego', 'puzzle', 'game', 'car']):
                category = 'toy'
            elif any(word in lowered for word in ['men', "men's", 'mens', 'man', 'gents', 'male']):
                category = 'men'
            elif any(word in lowered for word in ['women', "women's", 'womens', 'woman', 'ladies', 'female']):
                category = 'women'
            elif any(word in lowered for word in ['boys', 'boy', 'kids boy', 'kid boy']):
                category = 'kids-men'
            elif any(word in lowered for word in ['girls', 'girl', 'kids girl', 'kid girl']):
                category = 'kids-girl'

            raw_words = re.findall(r'[a-z0-9]+', lowered)
            stop_words = {
                'show', 'me', 'the', 'a', 'an', 'for', 'to', 'of', 'and', 'or', 'with',
                'i', 'want', 'need', 'looking', 'find', 'buy', 'get', 'please', 'some',
                'any', 'my', 'your', 'in', 'on', 'at', 'from', 'is', 'are', 'you', 'today'
            }
            keywords = [w for w in raw_words if len(w) > 2 and w not in stop_words]

            if not keywords and category is None and not age_mentions:
                message = "I can help with toys or clothing. Tell me what you're looking for!"
            else:
                message = "I'm having trouble reaching the AI right now, but I can still show matching items."

            ai_data = {
                'message': message,
                'search_params': {
                    'keywords': keywords,
                    'category': category,
                    'age_mentions': age_mentions
                }
            }
            
        message = ai_data.get('message', "Here's what I found!")
        search_params = ai_data.get('search_params', {})
        keywords = search_params.get('keywords', [])
        category = search_params.get('category')
        age_mentions = search_params.get('age_mentions', [])
        
        products_out = []
        
        if keywords or category or age_mentions:
            toy_q = Q()
            cloth_q = Q()
            
            # Map category strictly
            if category == 'toy':
                cloth_q = Q(id__isnull=True) # Exclude cloths
            elif category in ['men', 'women', 'kids-men', 'kids-girl']:
                cloth_q &= Q(category=category)
                toy_q = Q(id__isnull=True) # Exclude toys
                
            # Keyword matching
            kw_toy_q = Q()
            kw_cloth_q = Q()
            if keywords:
                for kw in keywords:
                    if len(kw) > 2:
                        kw_toy_q |= Q(name__icontains=kw) | Q(description__icontains=kw) | Q(category__icontains=kw)
                        kw_cloth_q |= Q(name__icontains=kw) | Q(desccription__icontains=kw) | Q(category__icontains=kw)
                if kw_toy_q:
                    toy_q &= kw_toy_q
                if kw_cloth_q:
                    cloth_q &= kw_cloth_q
                        
            # Age matching
            age_toy_q = Q()
            age_cloth_q = Q()
            if age_mentions:
                for age in age_mentions:
                    age_toy_q |= Q(age_range__icontains=str(age))
                    age_cloth_q |= Q(name__icontains=str(age)) | Q(desccription__icontains=str(age))
                if age_toy_q:
                    toy_q &= age_toy_q
                if age_cloth_q:
                    cloth_q &= age_cloth_q
                    
            toys = Toy.objects.filter(toy_q).distinct()[:3] if category == 'toy' or not category else []
            cloths = Cloths.objects.filter(cloth_q).distinct()[:3] if category != 'toy' else []
            
            for t in toys:
                products_out.append({
                    'name': t.name,
                    'price': f"Rs. {t.price}",
                    'url': f"/product/toy/{t.id}/",
                    'image': t.imageUrl.url if t.imageUrl else ''
                })
            for c in cloths:
                products_out.append({
                    'name': c.name,
                    'price': f"Rs. {c.price2 or c.price1 or c.price}",
                    'url': f"/product/cloth/{c.id}/",
                    'image': c.imageUrl.url if c.imageUrl else ''
                })
                
        return JsonResponse({
            'message': message,
            'products': products_out
        })

    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"AI Chat Error: {error_msg}")
        return JsonResponse({
            'message': "I'm sorry, I ran into a snag. Please try again in a moment.",
            'products': []
        }, status=200) # Use 200 so the UI can show the error message instead of failing silently


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


def trending_page(request):
    """View to display all trending products with category filtering"""
    category = request.GET.get('category', '')
    trending_qs = TrendingProduct.objects.filter(is_active=True)
    
    if category:
        trending_qs = trending_qs.filter(category=category)
    
    # Pagination
    paginator = Paginator(trending_qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'trending_products': page_obj,
        'current_category': category,
        'cart_count': get_or_create_cart(request).get_item_count(),
    }
    return render(request, 'trending.html', context)


def index(request):
    offers = Offers.objects.annotate(avg_rating=Avg('product_reviews__rating')).all()
    arrivals = NewArrivals.objects.annotate(avg_rating=Avg('product_reviews__rating')).all()
    trending_products = TrendingProduct.objects.filter(is_active=True)[:4]
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
            wish_real_item = item.get_item()
            if wish_real_item:
                wishlist_items.append({
                    'id': item.id,
                    'name': wish_real_item.name if hasattr(wish_real_item, 'name') else wish_real_item.title,
                    'price': item.get_price(),
                    'image': wish_real_item.imageUrl.url if wish_real_item.imageUrl else '',
                    'category': item.get_category(),
                    'item_type': item.item_type,
                })

    try:
        active_banners = SiteBanner.objects.filter(is_active=True).order_by('order')
        site_settings_obj = SiteSettings.get_settings()
    except Exception:
        active_banners = []
        site_settings_obj = None

    context = {
        'cards': cards,
        'offers': offers,
        'arrivals': arrivals,
        'trending_products': trending_products,
        'wishlist_items': wishlist_items,
        'wishlist_count': wishlist_count,
        'cart_count': cart_count,
        'active_banners': active_banners,
        'site_settings': site_settings_obj,
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
        username = (request.POST.get('username') or '').strip()
        email = (request.POST.get('email') or '').strip().lower()
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        signup_data = {
            'username': username,
            'full_name': (request.POST.get('full_name') or '').strip(),
            'email': email,
            'address': (request.POST.get('address') or '').strip(),
            'phone': (request.POST.get('phone') or '').strip(),
        }

        # --- Validations ---
        if not email or '@' not in email or '.' not in email.split('@')[-1]:
            messages.error(request, 'Please enter a valid email address.')
            return render_signup_with_data(signup_data)

        if password != password2:
            messages.error(request, 'Passwords do not match')
            return render_signup_with_data(signup_data)

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render_signup_with_data(signup_data)

        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists')
            return render_signup_with_data(signup_data)

        # Validate password strength
        try:
            validate_password(password, user=User(username=username, email=email))
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, error)
            return render_signup_with_data(signup_data)

        user = User.objects.create_user(username=username, email=email, password=password)
        full_name = signup_data['full_name']
        if full_name:
            parts = full_name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
        user.save()

        auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, 'Account created successfully! Welcome to KidZone 🎉')
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
    colors_available = getattr(product, 'colors_available', '') or ''
    safety_info = getattr(product, 'safety_info', '') or ''
    dimensions = getattr(product, 'dimensions', '') or ''

    # Normalize price for UI and tracking (avoid price2 on arrivals)
    if product_type == 'cloth':
        product_display_price = getattr(product, 'price1', None) or getattr(product, 'price', '') or ''
    elif product_type == 'offer':
        product_display_price = getattr(product, 'price1', None) or getattr(product, 'price2', '') or ''
    else:
        product_display_price = getattr(product, 'price', '') or ''

    # ── Gallery images ──
    gallery_images = ProductImage.objects.filter(product_type=product_type, **{fk_field: product})

    def _parse_option_list(raw_value):
        if not raw_value:
            return []
        parts = re.split(r'[,/;\n]+', str(raw_value))
        return [p.strip() for p in parts if p.strip()]

    # ── Product variants (cloth only) + size/color options for all ──
    variants = []
    variant_data = []
    size_options = []
    color_options = []
    if product_type == 'cloth':
        variants = list(product.variants.all())
        if variants:
            variant_data = [
                {
                    'size': v.size or '',
                    'color': v.color or '',
                    'color_code': v.color_code or '',
                    'extra_price': float(v.extra_price or 0),
                    'stock': v.stock,
                } for v in variants
            ]
            size_options = sorted({v['size'] for v in variant_data if v['size']})
            seen_colors = set()
            for v in variant_data:
                name = v['color']
                if not name:
                    continue
                key = name.lower()
                if key in seen_colors:
                    continue
                seen_colors.add(key)
                color_options.append({'name': name, 'code': v['color_code'] or ''})
        else:
            size_options = _parse_option_list(sizes_available)
            color_options = [{'name': c, 'code': ''} for c in _parse_option_list(colors_available)]
    else:
        size_options = _parse_option_list(sizes_available)
        color_options = [{'name': c, 'code': ''} for c in _parse_option_list(colors_available)]

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
        'colors_available': colors_available,
        'safety_info': safety_info,
        'dimensions': dimensions,
        'gallery_images': gallery_images,
        'variants': variants,
        'variant_data': variant_data,
        'size_options': size_options,
        'color_options': color_options,
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

    # Sort by criteria first
    if sort == 'price_asc':
        sort_key = lambda item: item.numeric_price
    elif sort == 'price_desc':
        sort_key = lambda item: item.numeric_price
        items.sort(key=sort_key, reverse=True)
        sort_key = None  # Already sorted
    elif sort == 'name_asc':
        sort_key = lambda item: item.name.lower()
    elif sort == 'name_desc':
        sort_key = lambda item: item.name.lower()
        items.sort(key=sort_key, reverse=True)
        sort_key = None  # Already sorted
    elif sort == 'oldest':
        sort_key = lambda item: item.id
    else:
        sort_key = lambda item: item.id
        items.sort(key=sort_key, reverse=True)
        sort_key = None  # Already sorted
    
    # Now apply stock-based sorting with the sort criteria
    if sort in ['price_asc', 'name_asc', 'oldest']:
        items = sort_items_by_stock(items, sort_key)
    else:
        items = sort_items_by_stock(items)

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

    # Sort by criteria first
    if sort == 'price_asc':
        sort_key = lambda item: item.numeric_price
    elif sort == 'price_desc':
        sort_key = lambda item: item.numeric_price
        all_filtered_items.sort(key=sort_key, reverse=True)
        sort_key = None
    elif sort == 'name_asc':
        sort_key = lambda item: item.name.lower()
    elif sort == 'name_desc':
        sort_key = lambda item: item.name.lower()
        all_filtered_items.sort(key=sort_key, reverse=True)
        sort_key = None
    elif sort == 'newest':
        sort_key = lambda item: item.id
        all_filtered_items.sort(key=sort_key, reverse=True)
        sort_key = None
    elif sort == 'oldest':
        sort_key = lambda item: item.id
    else:
        sort_key = lambda item: item.id
        all_filtered_items.sort(key=sort_key, reverse=True)
        sort_key = None

    # Apply stock-based sorting
    if sort in ['price_asc', 'name_asc', 'oldest']:
        all_filtered_items = sort_items_by_stock(all_filtered_items, sort_key)
    else:
        all_filtered_items = sort_items_by_stock(all_filtered_items)

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

    # Sort by criteria first
    if sort == 'price_asc':
        sort_key = lambda item: item.numeric_price
    elif sort == 'price_desc':
        sort_key = lambda item: item.numeric_price
        products.sort(key=sort_key, reverse=True)
        sort_key = None
    elif sort == 'name_asc':
        sort_key = lambda item: item.name.lower()
    elif sort == 'name_desc':
        sort_key = lambda item: item.name.lower()
        products.sort(key=sort_key, reverse=True)
        sort_key = None
    elif sort == 'oldest':
        sort_key = lambda item: item.id
    else:
        sort_key = lambda item: item.id
        products.sort(key=sort_key, reverse=True)
        sort_key = None

    # Apply stock-based sorting
    if sort in ['price_asc', 'name_asc', 'oldest']:
        products = sort_items_by_stock(products, sort_key)
    else:
        products = sort_items_by_stock(products)

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
            contact_msg = form.save()
            
            # Send email notification to admin
            try:
                from django.core.mail import send_mail
                from django.conf import settings as django_settings
                
                admin_email = django_settings.EMAIL_HOST_USER
                subject = f"New Contact Message: {contact_msg.subject}"
                body = f"You received a new message from {contact_msg.name} ({contact_msg.email}):\n\n{contact_msg.message}\n\nPhone: {contact_msg.phone or 'N/A'}"
                
                send_mail(
                    subject,
                    body,
                    django_settings.DEFAULT_FROM_EMAIL,
                    [admin_email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Error sending contact email: {e}")

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
    toys = list(Toy.objects.all().annotate(avg_rating=Avg('product_reviews__rating'), review_count=Count('product_reviews')).order_by('-id'))
    
    if category != 'all':
        toys = [toy for toy in toys if toy.category == category]
    
    if age_range != 'all':
        toys = [toy for toy in toys if toy.age_range == age_range]
    
    # Apply stock-based sorting
    toys = sort_items_by_stock(toys)
    
    # Get featured toys
    featured_toys = list(Toy.objects.filter(is_bestseller=True).annotate(avg_rating=Avg('product_reviews__rating'), review_count=Count('product_reviews'))[:4])
    featured_toys = sort_items_by_stock(featured_toys)
    
    new_toys = list(Toy.objects.filter(is_new=True).annotate(avg_rating=Avg('product_reviews__rating'), review_count=Count('product_reviews'))[:4])
    new_toys = sort_items_by_stock(new_toys)
    
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

def _get_inventory(item):
    if item and hasattr(item, 'inventory') and item.inventory:
        return item.inventory
    return None

def _stock_error_response(request, message):
    if request.method == 'POST' or _wants_json(request):
        return JsonResponse({'success': False, 'error': message}, status=400)
    messages.error(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'index'))

def add_to_cart(request, item_type, item_id):
    try:
        cart = get_or_create_cart(request)
        requested_unit_price = None
        selected_size = None
        selected_color = None
        variant_extra_price = Decimal('0.00')
        requested_qty = 1

        # Optional unit price sent by frontend (price shown to user when clicking Add to Cart).
        if request.method == 'POST' and request.body:
            try:
                payload = json.loads(request.body)
                parsed_price = parse_catalog_price(payload.get('unit_price'))
                if parsed_price > 0:
                    requested_unit_price = Decimal(str(round(parsed_price, 2)))
                selected_size = (payload.get('size') or '').strip() or None
                selected_color = (payload.get('color') or '').strip() or None
                raw_qty = payload.get('quantity', 1)
                try:
                    requested_qty = max(1, int(raw_qty))
                except (TypeError, ValueError):
                    requested_qty = 1
                parsed_extra = parse_catalog_price(payload.get('variant_extra_price'))
                if parsed_extra:
                    variant_extra_price = Decimal(str(round(parsed_extra, 2)))
            except (TypeError, ValueError, json.JSONDecodeError):
                requested_unit_price = None
        
        # Get the product based on item_type
        item = None
        if item_type == 'cloth':
            item = get_object_or_404(Cloths, id=item_id)
            inv = _get_inventory(item)
            if inv and inv.stock <= 0:
                return _stock_error_response(request, 'This item is out of stock.')
            variant = None
            if selected_size or selected_color:
                variant = ProductVariant.objects.filter(
                    cloth=item,
                    size=selected_size or '',
                    color=selected_color or ''
                ).first()
                if variant and variant.stock <= 0:
                    return _stock_error_response(request, 'This variant is out of stock.')
                if variant:
                    variant_extra_price = variant.extra_price
            cart_item = CartItem.objects.filter(
                cart=cart,
                item_type='cloth',
                cloth=item,
                selected_size=selected_size,
                selected_color=selected_color
            ).first()
            created = cart_item is None
            if not cart_item:
                cart_item = CartItem(
                    cart=cart,
                    item_type='cloth',
                    cloth=item,
                    quantity=requested_qty
                )
            else:
                if variant and cart_item.quantity + requested_qty > variant.stock:
                    return _stock_error_response(request, f'Only {variant.stock} left in stock for this variant.')
                if inv and cart_item.quantity + requested_qty > inv.stock:
                    return _stock_error_response(request, f'Only {inv.stock} left in stock.')
                cart_item.quantity += requested_qty
        elif item_type == 'toy':
            item = get_object_or_404(Toy, id=item_id)
            inv = _get_inventory(item)
            if inv and inv.stock <= 0:
                return _stock_error_response(request, 'This item is out of stock.')
            cart_item = CartItem.objects.filter(
                cart=cart,
                item_type='toy',
                toy=item,
                selected_size=selected_size,
                selected_color=selected_color
            ).first()
            created = cart_item is None
            if not cart_item:
                cart_item = CartItem(cart=cart, item_type='toy', toy=item, quantity=requested_qty)
            else:
                if inv and cart_item.quantity + requested_qty > inv.stock:
                    return _stock_error_response(request, f'Only {inv.stock} left in stock.')
                cart_item.quantity += requested_qty
        elif item_type == 'offer':
            item = get_object_or_404(Offers, id=item_id)
            inv = _get_inventory(item)
            if inv and inv.stock <= 0:
                return _stock_error_response(request, 'This item is out of stock.')
            cart_item = CartItem.objects.filter(
                cart=cart,
                item_type='offer',
                offer=item,
                selected_size=selected_size,
                selected_color=selected_color
            ).first()
            created = cart_item is None
            if not cart_item:
                cart_item = CartItem(cart=cart, item_type='offer', offer=item, quantity=requested_qty)
            else:
                if inv and cart_item.quantity + requested_qty > inv.stock:
                    return _stock_error_response(request, f'Only {inv.stock} left in stock.')
                cart_item.quantity += requested_qty
        elif item_type == 'arrival':
            item = get_object_or_404(NewArrivals, id=item_id)
            inv = _get_inventory(item)
            if inv and inv.stock <= 0:
                return _stock_error_response(request, 'This item is out of stock.')
            cart_item = CartItem.objects.filter(
                cart=cart,
                item_type='arrival',
                arrival=item,
                selected_size=selected_size,
                selected_color=selected_color
            ).first()
            created = cart_item is None
            if not cart_item:
                cart_item = CartItem(cart=cart, item_type='arrival', arrival=item, quantity=requested_qty)
            else:
                if inv and cart_item.quantity + requested_qty > inv.stock:
                    return _stock_error_response(request, f'Only {inv.stock} left in stock.')
                cart_item.quantity += requested_qty
        else:
            if _wants_json(request):
                return JsonResponse({'success': False, 'error': 'Invalid item type'}, status=400)
            messages.error(request, 'Invalid item type')
            return redirect(request.META.get('HTTP_REFERER', 'index'))

        if cart_item.unit_price is None:
            if requested_unit_price is not None:
                cart_item.unit_price = requested_unit_price
            else:
                live_price = cart_item.get_live_price()
                cart_item.unit_price = Decimal(str(round(live_price, 2))) if live_price > 0 else Decimal('0.00')

        cart_item.selected_size = selected_size
        cart_item.selected_color = selected_color
        cart_item.variant_extra_price = variant_extra_price

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

def buy_now(request, item_type, item_id):
    """Adds item to cart and redirects to checkout immediately"""
    try:
        cart = get_or_create_cart(request)
        if item_type == 'cloth':
            item = get_object_or_404(Cloths, id=item_id)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, item_type='cloth', cloth=item)
        elif item_type == 'toy':
            item = get_object_or_404(Toy, id=item_id)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, item_type='toy', toy=item)
        elif item_type == 'offer':
            item = get_object_or_404(Offers, id=item_id)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, item_type='offer', offer=item)
        elif item_type == 'arrival':
            item = get_object_or_404(NewArrivals, id=item_id)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, item_type='arrival', arrival=item)
        else:
            messages.error(request, 'Invalid item type')
            return redirect('index')

        if not created:
            cart_item.quantity += 1
        if cart_item.unit_price is None:
            live_price = cart_item.get_live_price()
            cart_item.unit_price = Decimal(str(round(live_price, 2))) if live_price > 0 else Decimal('0.00')
        cart_item.save()
        return redirect('checkout')
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('index')


@require_POST
def update_cart_item(request, cart_item_id):
    try:
        data = json.loads(request.body)
        quantity = int(data.get('quantity', 1))
        
        if quantity < 1:
            return JsonResponse({'success': False, 'error': 'Quantity must be at least 1'}, status=400)
        
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart=cart)

        item = cart_item.get_item()
        inv = _get_inventory(item)
        if inv:
            if inv.stock <= 0:
                return JsonResponse({'success': False, 'error': 'This item is out of stock.'}, status=400)
            if quantity > inv.stock:
                return JsonResponse({'success': False, 'error': f'Only {inv.stock} left in stock.'}, status=400)

        if cart_item.unit_price is None:
            live_price = cart_item.get_live_price()
            cart_item.unit_price = Decimal(str(round(live_price, 2))) if live_price > 0 else Decimal('0.00')
        
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
    subtotal = Decimal(str(cart.get_total()))
    tax = subtotal * Decimal('0.10')
    total = subtotal + tax
    
    return render(request, 'cart_details_page.html', {
        'cart': cart,
        'cart_count': cart.get_item_count(),
        'cart_items': cart.items.all(),
        'subtotal': float(subtotal),
        'tax': float(tax),
        'total': float(total),
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

        inv = _get_inventory(item)
        if inv and inv.stock <= 0:
            messages.warning(request, f'"{product_name}" is out of stock and cannot be added to cart.')
            return redirect('wishlist')
        
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
            if inv and cart_item.quantity + 1 > inv.stock:
                messages.warning(request, f'Only {inv.stock} left for "{product_name}".')
                return redirect('wishlist')
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
        # Check if the user placed an order in the last 1 minute (to handle double-clicks)
        from django.utils import timezone
        from datetime import timedelta
        recent_order = Order.objects.filter(
            user=request.user, 
            created_at__gte=timezone.now() - timedelta(minutes=1)
        ).order_by('-created_at').first()
        
        if recent_order:
            return redirect('order_success', order_number=recent_order.order_number)
            
        messages.warning(request, 'Your cart is empty')
        return redirect('cart_details')
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        if not full_name and request.user.is_authenticated:
            full_name = request.user.get_full_name() or request.user.username
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
            last_order = Order.objects.filter(user=request.user).order_by('-created_at').first()
            return render(request, 'checkout.html', {
                'cart': cart,
                'cart_items': cart.items.all(),
                'subtotal': float(subtotal),
                'tax': float(tax),
                'shipping': float(shipping),
                'total': float(subtotal + tax + shipping),
                'coupons_available': Coupon.objects.filter(is_active=True).exists(),
                'post_data': request.POST,
                'last_order': last_order,
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
            
            if payment_method == 'card':
                # Store shipping info so the Stripe session can be created from the same checkout page.
                request.session['checkout_shipping'] = {
                    'full_name': full_name,
                    'email': email,
                    'phone': phone,
                    'address': address,
                    'city': city,
                    'postal_code': postal_code,
                    'country': country,
                    'coupon_code': coupon_code,
                }
                return render(request, 'checkout.html', {
                    'cart': cart,
                    'cart_items': cart.items.all(),
                    'subtotal': float(subtotal),
                    'tax': float(tax),
                    'shipping': float(shipping),
                    'total': float(total),
                    'coupons_available': Coupon.objects.filter(is_active=True).exists(),
                    'post_data': request.POST,
                    'last_order': Order.objects.filter(user=request.user).order_by('-created_at').first(),
                    'payment_method': 'card',
                })

            # --- CASH ON DELIVERY FLOW ---
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
                if item is None:
                    continue
                item_name = getattr(item, 'name', None) or getattr(item, 'title', 'Unknown Item')
                variant_label = cart_item.get_variant_display()
                if variant_label:
                    item_name = f"{item_name} ({variant_label})"
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
            except Exception:
                pass
            
            cart.items.all().delete()
            messages.success(request, f'Order {order_number} placed successfully!')
            return redirect('order_success', order_number=order_number)
        
        except Exception as e:
            messages.error(request, 'Something went wrong placing your order. Please try again.')
            subtotal = Decimal(str(cart.get_total()))
            tax = subtotal * Decimal('0.10')
            shipping = Decimal('10.00')
            last_order = Order.objects.filter(user=request.user).order_by('-created_at').first()
            return render(request, 'checkout.html', {
                'cart': cart,
                'cart_items': cart.items.all(),
                'subtotal': float(subtotal),
                'tax': float(tax),
                'shipping': float(shipping),
                'total': float(subtotal + tax + shipping),
                'coupons_available': Coupon.objects.filter(is_active=True).exists(),
                'post_data': request.POST,
                'last_order': last_order,
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
        'last_order': Order.objects.filter(user=request.user).order_by('-created_at').first() if request.user.is_authenticated else None,
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


@login_required(login_url='login')
def order_success_latest(request):
    """Render order success page for the latest order at /order-success/."""
    latest_order = Order.objects.filter(user=request.user).order_by('-created_at').first()
    if not latest_order:
        messages.warning(request, 'No recent order found. Please place an order first.')
        return redirect('checkout')
    context = {
        'order': latest_order,
        'order_items': latest_order.items.all(),
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
# ENHANCED FEATURES: Recently Viewed, Returns, Order Tracking
# ══════════════════════════════════════════════════════

@login_required(login_url='login')
def track_view_history(request, product_type, product_id):
    """Track when user views a product"""
    try:
        product_fk_field = None
        product = None
        
        if product_type == 'cloth':
            product = get_object_or_404(Cloths, id=product_id)
            product_fk_field = 'cloth'
        elif product_type == 'toy':
            product = get_object_or_404(Toy, id=product_id)
            product_fk_field = 'toy'
        elif product_type == 'offer':
            product = get_object_or_404(Offers, id=product_id)
            product_fk_field = 'offer'
        elif product_type == 'arrival':
            product = get_object_or_404(NewArrivals, id=product_id)
            product_fk_field = 'arrival'
        
        if product and product_fk_field:
            # Remove old view of same product (to update timestamp)
            ViewHistory.objects.filter(user=request.user, **{product_fk_field: product}).delete()
            
            # Create new view record
            ViewHistory.objects.create(user=request.user, **{product_fk_field: product})
        
        return JsonResponse({'success': True})
    except Exception:
        return JsonResponse({'success': False}, status=500)


@login_required(login_url='login')
def recently_viewed(request):
    """Display recently viewed products"""
    cart_count = 0
    try:
        cart_count = get_or_create_cart(request).get_item_count()
    except:
        cart_count = 0
    
    # Get last 20 viewed products
    viewed = ViewHistory.objects.filter(user=request.user)[:20]
    
    items = []
    for view in viewed:
        item = None
        url = '#'
        item_type = ''
        
        if view.cloth:
            item = view.cloth
            item_type = 'cloth'
            url = f"/product/cloth/{item.id}/"
        elif view.toy:
            item = view.toy
            item_type = 'toy'
            url = f"/product/toy/{item.id}/"
        elif view.offer:
            item = view.offer
            item_type = 'offer'
            url = f"/product/offer/{item.id}/"
        elif view.arrival:
            item = view.arrival
            item_type = 'arrival'
            url = f"/product/arrival/{item.id}/"
        
        if item:
            items.append({
                'name': getattr(item, 'name', None) or getattr(item, 'title', ''),
                'price': getattr(item, 'price', None) or getattr(item, 'price2', None) or getattr(item, 'price1', ''),
                'image': item.imageUrl.url if hasattr(item, 'imageUrl') and item.imageUrl else '',
                'url': url,
                'type': item_type,
                'viewed_at': view.viewed_at,
            })
    
    return render(request, 'recently_viewed.html', {
        'items': items,
        'cart_count': cart_count,
    })


@login_required(login_url='login')
def order_tracking(request):
    """Display order tracking with detailed status"""
    cart_count = get_or_create_cart(request).get_item_count()
    
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    orders_data = []
    for order in orders:
        tracking = order.tracking_updates.all().order_by('-created_at')
        current_status = tracking.first().status if tracking else 'pending'
        
        orders_data.append({
            'order': order,
            'current_status': current_status,
            'tracking_updates': tracking,
            'can_return': (timezone.now() - order.created_at).days <= 30,
            'has_return': Return.objects.filter(order=order).exists(),
        })
    
    return render(request, 'order_tracking.html', {
        'orders_data': orders_data,
        'cart_count': cart_count,
    })


@login_required(login_url='login')
def order_details(request, order_number):
    """View detailed order information"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    cart_count = get_or_create_cart(request).get_item_count()
    
    tracking_updates = order.tracking_updates.all().order_by('-created_at')
    returns = Return.objects.filter(order=order)
    
    context = {
        'order': order,
        'order_items': order.items.all(),
        'tracking_updates': tracking_updates,
        'returns': returns,
        'current_status': tracking_updates.first().status if tracking_updates else 'pending',
        'can_return': (timezone.now() - order.created_at).days <= 30,
        'cart_count': cart_count,
    }
    
    return render(request, 'order_details.html', context)


@login_required(login_url='login')
def initiate_return(request, order_number):
    """Initiate a product return/refund"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    cart_count = get_or_create_cart(request).get_item_count()
    
    # Check if return is allowed (within 30 days)
    days_passed = (timezone.now() - order.created_at).days
    if days_passed > 30:
        messages.error(request, 'Returns are only allowed within 30 days of purchase')
        return redirect('order_details', order_number=order_number)
    
    if request.method == 'POST':
        try:
            item_id = request.POST.get('item_id')
            reason = request.POST.get('reason')
            description = request.POST.get('description')
            
            if not all([item_id, reason, description]):
                messages.error(request, 'Please fill in all required fields')
                return redirect('initiate_return', order_number=order_number)
            
            order_item = get_object_or_404(OrderItem, id=item_id, order=order)
            
            # Create return record
            return_obj = Return.objects.create(
                order=order,
                order_item=order_item,
                reason=reason,
                description=description,
                refund_amount=order_item.subtotal,
                status='initiated'
            )
            
            messages.success(request, f'Return initiated for {order_item.item_name}. Your return ID is: #{return_obj.id}')
            return redirect('return_status', return_id=return_obj.id)
        except Exception as e:
            messages.error(request, f'Error creating return: {str(e)}')
    
    return render(request, 'initiate_return.html', {
        'order': order,
        'order_items': order.items.all(),
        'cart_count': cart_count,
        'return_reasons': Return.REASON_CHOICES,
    })


@login_required(login_url='login')
def return_status(request, return_id):
    """Check return/refund status"""
    return_obj = get_object_or_404(Return, id=return_id, order__user=request.user)
    cart_count = get_or_create_cart(request).get_item_count()
    
    context = {
        'return': return_obj,
        'order': return_obj.order,
        'order_item': return_obj.order_item,
        'cart_count': cart_count,
        'status_timeline': [
            {'status': 'initiated', 'label': 'Return Initiated', 'icon': 'bi-check-circle'},
            {'status': 'approved', 'label': 'Return Approved', 'icon': 'bi-check-circle'},
            {'status': 'shipped', 'label': 'Shipped to Warehouse', 'icon': 'bi-truck'},
            {'status': 'received', 'label': 'Received at Warehouse', 'icon': 'bi-bag-check'},
            {'status': 'processed', 'label': 'Refund Processed', 'icon': 'bi-cash'},
        ]
    }
    
    return render(request, 'return_status.html', context)


@login_required(login_url='login')
def my_returns(request):
    """View all returns/refunds for user"""
    cart_count = get_or_create_cart(request).get_item_count()
    
    returns = Return.objects.filter(order__user=request.user).order_by('-initiated_at')
    
    return render(request, 'my_returns.html', {
        'returns': returns,
        'cart_count': cart_count,
    })


@login_required(login_url='login')
def stock_alert_settings(request):
    """Manage stock alerts for products"""
    cart_count = get_or_create_cart(request).get_item_count()
    
    alerts = StockAlert.objects.filter(user=request.user, is_active=True)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            action = data.get('action')
            alert_id = data.get('alert_id')
            
            if action == 'remove':
                alert = get_object_or_404(StockAlert, id=alert_id, user=request.user)
                alert.is_active = False
                alert.save()
                return JsonResponse({'success': True, 'message': 'Alert removed'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return render(request, 'stock_alert_settings.html', {
        'alerts': alerts,
        'cart_count': cart_count,
    })


@require_POST
@login_required(login_url='login')
def add_stock_alert(request, product_type, product_id):
    """Add a stock alert for an out-of-stock product"""
    try:
        product_fk_field = None
        
        if product_type == 'cloth':
            product = get_object_or_404(Cloths, id=product_id)
            product_fk_field = 'cloth'
        elif product_type == 'toy':
            product = get_object_or_404(Toy, id=product_id)
            product_fk_field = 'toy'
        elif product_type == 'offer':
            product = get_object_or_404(Offers, id=product_id)
            product_fk_field = 'offer'
        elif product_type == 'arrival':
            product = get_object_or_404(NewArrivals, id=product_id)
            product_fk_field = 'arrival'
        else:
            return JsonResponse({'success': False, 'error': 'Invalid product type'}, status=400)
        
        # Check if already alerting for this product
        existing = StockAlert.objects.filter(
            user=request.user,
            is_active=True,
            **{product_fk_field: product}
        ).first()
        
        if existing:
            return JsonResponse({'success': True, 'message': 'Already monitoring this product'})
        
        # Create alert
        alert = StockAlert.objects.create(user=request.user, **{product_fk_field: product})
        
        return JsonResponse({
            'success': True,
            'message': f'We\'ll notify you when this item is back in stock!',
            'alert_id': alert.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════
# SEARCH FUNCTIONALITY
# ══════════════════════════════════════════════════════

def live_search(request):
    query = request.GET.get('q', '').strip()
    results = []
    if len(query) >= 2:
        cloths = Cloths.objects.filter(Q(name__icontains=query))[:3]
        toys = Toy.objects.filter(Q(name__icontains=query))[:3]
        offers = Offers.objects.filter(Q(title__icontains=query))[:3]
        arrivals = NewArrivals.objects.filter(Q(title__icontains=query))[:3]

        for item in cloths:
            results.append({
                'name': item.name,
                'price': f"Rs {item.price2 or item.price or item.price1}",
                'image': item.imageUrl.url if item.imageUrl else '',
                'url': f'/product/cloth/{item.id}/',
                'type': 'Clothing'
            })
        for item in toys:
            results.append({
                'name': item.name,
                'price': f"Rs {item.price}",
                'image': item.imageUrl.url if item.imageUrl else '',
                'url': f'/product/toy/{item.id}/',
                'type': 'Toy'
            })
        for item in offers:
            results.append({
                'name': item.title,
                'price': f"Rs {item.price2 or item.price1}",
                'image': item.imageUrl.url if item.imageUrl else '',
                'url': f'/product/offer/{item.id}/',
                'type': 'Offer'
            })
        for item in arrivals:
            results.append({
                'name': item.title,
                'price': f"Rs {item.price}",
                'image': item.imageUrl.url if item.imageUrl else '',
                'url': f'/product/arrival/{item.id}/',
                'type': 'New Arrival'
            })

    return JsonResponse({'results': results[:8]})


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
def order_tracking_legacy(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    tracking_updates = order.tracking_updates.all().order_by('-created_at')

    status_steps = ['pending', 'processing', 'shipped', 'delivered']
    current_index = status_steps.index(order.status) if order.status in status_steps else -1
    
    # Check if any items are in this order
    order_items = order.items.all()

    return render(request, 'order_tracking.html', {
        'order': order,
        'order_items': order_items,
        'tracking_updates': tracking_updates,
        'status_steps': status_steps,
        'current_index': current_index,
    })


@login_required(login_url='login')
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    status_filter = request.GET.get('status', '').strip()
    valid_statuses = {choice[0] for choice in Order.STATUS_CHOICES}
    if status_filter in valid_statuses:
        orders = orders.filter(status=status_filter)

    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'my_orders.html', {
        'orders': page_obj,
        'status_filter': status_filter,
    })


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


# ══════════════════════════════════════════════════════
# DASHBOARD UTILITIES (CSV Export, JSON Details)
# ══════════════════════════════════════════════════════

import csv
from django.http import HttpResponse

@login_required(login_url='login')
def export_orders_csv(request):
    if not request.user.is_staff:
        return HttpResponse("Unauthorized", status=403)
    from django.utils import timezone
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="orders_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Order #', 'Customer', 'Email', 'Date', 'Total', 'Status', 'Payment'])
    
    orders = Order.objects.all().order_by('-created_at')
    for o in orders:
        writer.writerow([o.order_number, o.full_name, o.email, o.created_at.strftime('%Y-%m-%d %H:%M'), o.total, o.status, o.payment_method])
        
    return response

@login_required(login_url='login')
def get_order_details(request, order_id):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    order = get_object_or_404(Order, id=order_id)
    items = []
    for item in order.items.all():
        items.append({
            'name': item.item_name,
            'quantity': item.quantity,
            'price': float(item.price),
            'subtotal': float(item.subtotal)
        })
        
    return JsonResponse({
        'order_number': order.order_number,
        'full_name': order.full_name,
        'email': order.email,
        'phone': order.phone,
        'address': order.address,
        'city': order.city,
        'status': order.status,
        'total': float(order.total),
        'subtotal': float(order.subtotal),
        'tax': float(order.tax),
        'shipping': float(order.shipping),
        'discount': float(order.discount),
        'items': items
    })

@login_required(login_url='login')
@require_POST
def manage_loyalty_points(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        points = int(data.get('points', 0))
        description = data.get('description', 'Admin adjustment')
        
        profile = get_object_or_404(LoyaltyProfile, user_id=user_id)
        profile.current_points += points
        if points > 0:
            profile.total_points_earned += points
        profile.save()
        profile.update_tier()
        
        LoyaltyHistory.objects.create(
            profile=profile,
            points=points,
            description=description
        )
        
        return JsonResponse({'success': True, 'new_points': profile.current_points, 'tier': profile.get_tier_display()})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'valid': False, 'error': 'Invalid request.'})


@login_required(login_url='login')
@require_POST
def admin_inventory_restock(request, inventory_id):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        quantity = int(data.get('quantity', 10))
    except Exception:
        quantity = 10

    if quantity <= 0:
        return JsonResponse({'success': False, 'error': 'Quantity must be greater than zero.'}, status=400)

    inv = get_object_or_404(Inventory, id=inventory_id)
    inv.stock = int(inv.stock) + quantity
    inv.save(update_fields=['stock'])

    return JsonResponse({
        'success': True,
        'stock': inv.stock,
        'is_low_stock': inv.is_low_stock,
        'message': f'Stock increased by {quantity}.',
    })


@login_required(login_url='login')
@require_POST
def admin_inventory_update_threshold(request, inventory_id):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)

    try:
        data = json.loads(request.body)
        threshold = int(data.get('threshold', 0))
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid threshold value.'}, status=400)

    if threshold < 0:
        return JsonResponse({'success': False, 'error': 'Threshold cannot be negative.'}, status=400)

    inv = get_object_or_404(Inventory, id=inventory_id)
    inv.low_stock_threshold = threshold
    inv.save(update_fields=['low_stock_threshold'])

    return JsonResponse({
        'success': True,
        'threshold': inv.low_stock_threshold,
        'is_low_stock': inv.is_low_stock,
        'message': 'Low-stock threshold updated.',
    })


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

def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('index')

    from django.db.models.functions import TruncMonth, TruncDate
    from datetime import timedelta
    from django.utils import timezone as tz
    from django.db.models import Sum as models_sum, Count, F, Q, Avg
    from django.contrib.sessions.models import Session

    # 1. REAL-TIME PULSE (Last 5 mins)
    five_mins_ago = tz.now() - timedelta(minutes=5)
    active_sessions = Session.objects.filter(expire_date__gte=tz.now()).count()
    # Simple estimation for "Live Now"
    live_now = max(1, active_sessions // 4) # Adjusting for session expiry buffer

    # 2. CORE STATS
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(total=models_sum('total'))['total'] or 0
    total_users = User.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()

    # 3. REVENUE CHARTS
    six_months_ago = tz.now() - timedelta(days=180)
    monthly_revenue = list(
        Order.objects.filter(created_at__gte=six_months_ago)
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total=models_sum('total'), count=Count('id'))
        .order_by('month')
    )

    thirty_days_ago = tz.now() - timedelta(days=30)
    daily_orders = list(
        Order.objects.filter(created_at__gte=thirty_days_ago)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('id'), total=models_sum('total'))
        .order_by('date')
    )

    # 4. STATUS & TOP PRODUCTS
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
        p['total_revenue'] = float(p.get('total_revenue') or 0)
        p['total_qty'] = int(p.get('total_qty') or 0)

    # 5. CUSTOMER BEHAVIOR (Top Spenders)
    top_spenders = User.objects.annotate(
        total_spent=models_sum('orders__total'),
        order_count=Count('orders')
    ).filter(total_spent__gt=0).order_by('-total_spent')[:10]

    # 6. ABANDONED CARTS (Carts with items > 2h old)
    two_hours_ago = tz.now() - timedelta(hours=2)
    abandoned_carts_count = Cart.objects.filter(
        items__isnull=False, 
        updated_at__lte=two_hours_ago
    ).distinct().count()

    # 7. INVENTORY FORECASTING
    low_stock = Inventory.objects.filter(stock__lte=F('low_stock_threshold'))
    
    # Calculate burn rate for forecasting (simple: units sold in last 30 days / 30)
    forecast_data = []
    all_inventory = Inventory.objects.all().select_related('cloth', 'toy', 'offer', 'arrival')
    for inv in all_inventory:
        product = inv.get_product()
        name = getattr(product, 'name', None) or getattr(product, 'title', 'Unknown')
        
        # Get units sold in last 30 days
        units_sold = OrderItem.objects.filter(
            item_name=name, 
            order__created_at__gte=thirty_days_ago
        ).aggregate(total=models_sum('quantity'))['total'] or 0
        
        daily_burn = units_sold / 30.0
        days_left = 999
        if daily_burn > 0:
            days_left = int(inv.stock / daily_burn)
            
        if days_left <= 7: # Only show forecast for items running out soon
            forecast_data.append({
                'name': name,
                'stock': inv.stock,
                'days_left': days_left,
                'burn_rate': round(daily_burn, 2)
            })
    
    forecast_data = sorted(forecast_data, key=lambda x: x['days_left'])[:5]

    # 8. LOYALTY STATS
    total_points_awarded = LoyaltyProfile.objects.aggregate(total=models_sum('total_points_earned'))['total'] or 0
    top_loyalty_users = LoyaltyProfile.objects.select_related('user').order_by('-current_points')[:5]

    # 9. SITE CONTENT
    try:
        active_banners = SiteBanner.objects.filter(is_active=True)
        site_settings = SiteSettings.get_settings()
    except Exception:
        active_banners = []
        site_settings = None

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
        'live_now': live_now,
        'abandoned_carts_count': abandoned_carts_count,
        'forecast_data': forecast_data,
        'top_spenders': top_spenders,
        'total_points_awarded': total_points_awarded,
        'top_loyalty_users': top_loyalty_users,
        'active_banners': active_banners,
        'site_settings': site_settings,
        'low_stock': low_stock,
    }
    return render(request, 'admin_dashboard.html', context)


# ══════════════════════════════════════════════════════
# ADMIN ORDER UPDATE
# ══════════════════════════════════════════════════════

@login_required(login_url='login')
@require_POST
def admin_update_order_status(request, order_id):
    if not request.user.is_staff:
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

    shipping_info = request.session.get('checkout_shipping', {})

    context = {
        'cart_items': items_data,
        'subtotal': float(subtotal),
        'tax': float(tax),
        'shipping': float(shipping),
        'total': float(total),
        'stripe_publishable_key': django_settings.STRIPE_PUBLISHABLE_KEY,
        'shipping_info': shipping_info,
    }
    return render(request, 'payment.html', context)


@login_required(login_url='login')
@require_POST
def create_checkout_session(request):
    """Create a Stripe checkout session and return the session ID."""
    stripe.api_key = django_settings.STRIPE_SECRET_KEY

    cart = get_or_create_cart(request)
    total = cart.get_total()
    if cart.get_item_count() == 0:
        return JsonResponse({'error': 'Cart is empty'}, status=400)
    
    # Stripe minimum amount check (approx $0.50)
    if float(total) < 150:
        return JsonResponse({'error': 'Order total must be at least Rs. 150 for card payments.'}, status=400)

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

    try:
        body = json.loads(request.body)
    except Exception:
        body = {}

    # [NEW] Handle Coupon logic for Stripe charging
    subtotal = float(cart.get_total())
    discount = 0.0
    coupon_code = body.get('coupon_code', '')
    
    if coupon_code:
        try:
            from .models import Coupon
            coupon = Coupon.objects.get(code__iexact=coupon_code)
            if coupon.is_valid() and subtotal >= float(coupon.min_order_amount):
                discount = float(coupon.get_discount(Decimal(str(subtotal))))
        except Exception:
            pass

    discounted_subtotal = max(0, subtotal - discount)
    tax = discounted_subtotal * 0.10
    shipping = 1000.0
    total_payable = discounted_subtotal + tax + shipping

    # Stripe does not allow negative line items. 
    # If a discount is applied, we'll send a single consolidated line item for the total.
    if discount > 0:
        line_items = [{
            'price_data': {
                'currency': 'lkr',
                'product_data': {
                    'name': f'Order Total (Discount {coupon_code} applied)',
                    'description': f'Original: Rs. {subtotal:.2f}, Discount: Rs. {discount:.2f}, Tax: Rs. {tax:.2f}',
                },
                'unit_amount': int(total_payable * 100),
            },
            'quantity': 1,
        }]
    else:
        # Standard flow with individual items
        if int(tax * 100) > 0:
            line_items.append({
                'price_data': {
                    'currency': 'lkr',
                    'product_data': {'name': 'Tax (10%)'},
                    'unit_amount': int(tax * 100),
                },
                'quantity': 1,
            })
        line_items.append({
            'price_data': {
                'currency': 'lkr',
                'product_data': {'name': 'Shipping'},
                'unit_amount': int(shipping * 100),
            },
            'quantity': 1,
        })

    # Store shipping info in session for later use
    shipping_data = {
        'full_name': body.get('full_name', request.user.get_full_name() or request.user.username),
        'email': body.get('email', request.user.email),
        'phone': body.get('phone', ''),
        'address': body.get('address', ''),
        'city': body.get('city', ''),
        'postal_code': body.get('postal_code', ''),
        'country': body.get('country', ''),
        'coupon_code': coupon_code,
        'discount_amount': str(discount),
    }
    request.session['checkout_shipping'] = shipping_data

    try:
        # Prepare metadata (ensure all values are strings)
        metadata = {
            'user_id': str(request.user.id),
        }
        for k, v in shipping_data.items():
            metadata[f'shipping_{k}'] = str(v)

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri('/payment-success/') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri('/payment-cancel/'),
            customer_email=request.user.email,
            metadata=metadata,
        )
        return JsonResponse({'sessionId': session.id, 'url': session.url})
    except Exception as e:
        print(f"STRIPE ERROR: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def _finalize_order_from_stripe_session(session, user, cart, request=None):
    """Helper to create order from Stripe session data."""
    # Double check if order already exists for this session
    existing = Order.objects.filter(tracking_number=session.id).first()
    if existing:
        return existing

    # Convert StripeObject to dict using .to_dict() to avoid AttributeError on .get()
    metadata = (session.metadata or {}).to_dict()
    shipping_info = {
        'full_name': metadata.get('shipping_full_name', user.get_full_name() or user.username),
        'email': metadata.get('shipping_email', user.email),
        'phone': metadata.get('shipping_phone', ''),
        'address': metadata.get('shipping_address', ''),
        'city': metadata.get('shipping_city', ''),
        'postal_code': metadata.get('shipping_postal_code', ''),
        'country': metadata.get('shipping_country', ''),
        'coupon_code': metadata.get('shipping_coupon_code', ''),
    }

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
        user=user,
        order_number=order_number,
        full_name=shipping_info.get('full_name'),
        email=shipping_info.get('email'),
        phone=shipping_info.get('phone'),
        address=shipping_info.get('address'),
        city=shipping_info.get('city'),
        postal_code=shipping_info.get('postal_code'),
        country=shipping_info.get('country'),
        subtotal=subtotal,
        tax=tax,
        shipping=shipping,
        discount=discount,
        coupon_code=coupon_code,
        total=total,
        payment_method='stripe',
        tracking_number=session.id,
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
    _send_order_confirmation_email(order, request)

    # Clear cart
    cart.items.all().delete()
    return order


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

    cart = get_or_create_cart(request)
    order = _finalize_order_from_stripe_session(session, request.user, cart, request)
    
    messages.success(request, f'Payment successful! Order {order.order_number} placed.')
    return redirect('order_success', order_number=order.order_number)


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
        metadata = (session.metadata or {}).to_dict()
        user_id = metadata.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                cart = Cart.objects.get(user=user)
                _finalize_order_from_stripe_session(session, user, cart)
            except Exception as e:
                print(f"Webhook order creation error: {e}")

    return HttpResponse(status=200)


def _send_order_confirmation_email(order, request=None):
    """Send a rich HTML order confirmation email."""
    try:
        from django.utils.html import strip_tags
        subject = f'KidZone Order Confirmed — {order.order_number}'
        
        tracking_url = f"/order-tracking/{order.order_number}/"
        if request:
            tracking_url = request.build_absolute_uri(tracking_url)
        
        # Context for the template
        context = {
            'order': order,
            'items': order.items.all(),
            'tracking_url': tracking_url,
        }
        
        # Render HTML template
        html_message = render_to_string('emails/order_confirmation.html', context)
        
        # Fallback plain text
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            fail_silently=True,
            html_message=html_message
        )
    except Exception as e:
        print(f"Failed to send order confirmation email: {e}")


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

        inv = _get_inventory(item)
        if inv and inv.stock <= 0:
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
            if inv and ci.quantity + oi.quantity > inv.stock:
                ci.quantity = inv.stock
            else:
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


def quick_view_api(request, item_type, item_id):
    """Return product data as JSON for the Quick View modal."""
    from .models import Cloths, Toy, Offers, NewArrivals

    try:
        if item_type == 'cloth':
            item = Cloths.objects.get(id=item_id)
            title = item.name
            price = item.price2 or item.price1 or item.price
            desc = item.desccription
        elif item_type == 'toy':
            item = Toy.objects.get(id=item_id)
            title = item.name
            price = item.price
            desc = item.description
        elif item_type == 'offer':
            item = Offers.objects.get(id=item_id)
            title = item.title
            price = item.price2 or item.price1
            desc = item.description
        elif item_type == 'arrival':
            item = NewArrivals.objects.get(id=item_id)
            title = item.title
            price = item.price
            desc = item.description
        else:
            return JsonResponse({'error': 'Invalid item type'}, status=400)

        data = {
            'id': item.id,
            'item_type': item_type,
            'title': title,
            'price': str(price),
            'description': desc,
            'image_url': item.imageUrl.url if item.imageUrl else '',
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=404)
