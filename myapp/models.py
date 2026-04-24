
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import re

class Card(models.Model):
    imageUrl = models.ImageField(upload_to='cards/')
    name = models.CharField(max_length=150)
    details = models.TextField()
    
    def __str__(self):
        return self.name
    

class Offers(models.Model):
    
    CATEGORY_CHOICES = [
        ('kids', 'Kids'),
        ('men', 'Men'),
        ('women', 'Women'),
    ]
    
    imageUrl = models.ImageField(upload_to='offers/')
    offers_badge = models.CharField(max_length=50)
    title = models.CharField(max_length=150)
    description = models.TextField()
    price1 = models.CharField(max_length=50, blank=True)
    price2 = models.CharField(max_length=50, blank=True)
    stock_text = models.CharField(max_length=50, blank=True)

    button_text = models.CharField(max_length=50)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='kids')
    end_time = models.DateTimeField(blank=True, null=True)
    long_description = models.TextField(blank=True, default='', help_text='Detailed description shown on the product detail page')
    features = models.TextField(blank=True, default='', help_text='Key features, one per line')
    material = models.CharField(max_length=200, blank=True, default='', help_text='e.g. 100% Cotton, Polyester blend')
    
    def __str__(self):
        return self.title
    

class NewArrivals(models.Model):
    
    CATEGORY_CHOICES = [
        ('kids', 'Kids'),
        ('men', 'Men'),
        ('women','Women'),
    ]
    
    imageUrl = models.ImageField(upload_to='new_arrivals/')
    offers_badge = models.CharField(max_length=50)
    title = models.CharField(max_length=150)
    description = models.TextField()
    price = models.CharField(max_length=50, blank=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='kids')
    long_description = models.TextField(blank=True, default='', help_text='Detailed description shown on the product detail page')
    features = models.TextField(blank=True, default='', help_text='Key features, one per line')
    material = models.CharField(max_length=200, blank=True, default='', help_text='e.g. 100% Cotton, Polyester blend')
    
    def __str__(self):
        return self.title
    

class Cloths(models.Model):
    CATEGORY_CHOICES = [
        ('kids-men', 'Kids Boys'),
        ('men', 'Men'),
        ('women','Women'),
        ('kids-girl', 'Kids Girls')
    ]
    
    SUBCATEGORY_CHOICES = [
        ('', 'None'),
        ('dresses', 'Dresses'),
        ('tops', 'Tops'),
        ('pants', 'Pants'),
        ('skirts', 'Skirts'),
        ('shirts', 'Shirts'),
        ('shoes', 'Shoes'),
        ('accessories', 'Accessories'),
    ]
    
    imageUrl = models.ImageField(upload_to='cloths/')
    name = models.CharField(max_length=150)
    price = models.CharField(max_length=50, blank=True)
    desccription = models.TextField()
    price1 = models.CharField(max_length=50, blank=True)
    price2 = models.CharField(max_length=50, blank=True)
    discount_text = models.CharField(max_length=50, blank=True) 
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default='kids-men')
    subcategory = models.CharField(max_length=20, choices=SUBCATEGORY_CHOICES, blank=True, default='')
    long_description = models.TextField(blank=True, default='', help_text='Detailed description shown on the product detail page')
    features = models.TextField(blank=True, default='', help_text='Key features, one per line')
    material = models.CharField(max_length=200, blank=True, default='', help_text='e.g. 100% Cotton, Polyester blend')
    care_instructions = models.TextField(blank=True, default='', help_text='Washing and care instructions')
    sizes_available = models.CharField(max_length=200, blank=True, default='', help_text='e.g. S, M, L, XL or 2T, 3T, 4T')
    
    def __str__(self):
        return self.name
    

class Review(models.Model):
    RATING_CHOICES = [
        (1, 'Poor'),
        (2, 'Fair'),
        (3, 'Good'),
        (4, 'Very Good'),
        (5, 'Excellent'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    uploadImages = models.ImageField(upload_to='reviews/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.get_rating_display()}"

    class Meta:
        ordering = ['-created_at']


class ServiceReview(models.Model):
    TOPIC_CHOICES = [
        ('overall', 'Overall Experience'),
        ('delivery', 'Delivery Speed'),
        ('packaging', 'Packaging Quality'),
        ('support', 'Customer Support'),
        ('returns', 'Returns & Refunds'),
    ]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    topic = models.CharField(max_length=20, choices=TOPIC_CHOICES, default='overall')
    delivery_rating = models.IntegerField(default=5)
    packaging_rating = models.IntegerField(default=5)
    support_rating = models.IntegerField(default=5)
    returns_rating = models.IntegerField(default=5)
    overall_rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.0)
    comment = models.TextField()
    is_verified_customer = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    helpful_count = models.PositiveIntegerField(default=0)
    report_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        ratings = [
            self.delivery_rating,
            self.packaging_rating,
            self.support_rating,
            self.returns_rating,
        ]
        self.overall_rating = round(sum(ratings) / 4.0, 2)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.overall_rating}/5"

    class Meta:
        ordering = ['-created_at']
    

class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.subject}"

    class Meta:
        ordering = ['-created_at']


class Toy(models.Model):
    CATEGORY_CHOICES = [
        ('educational', 'Educational'),
        ('outdoor', 'Outdoor'),
        ('creative', 'Creative'),
        ('electronic', 'Electronic'),
        ('plush', 'Plush'),
        ('building', 'Building'),
    ]
    
    AGE_RANGE_CHOICES = [
        ('0-2', '0-2 years'),
        ('3-5', '3-5 years'),
        ('6-8', '6-8 years'),
        ('9-12', '9-12 years'),
        ('13+', '13+ years'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    age_range = models.CharField(max_length=10, choices=AGE_RANGE_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    imageUrl = models.ImageField(upload_to='toys/')
    is_bestseller = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=5.0)
    created_at = models.DateTimeField(auto_now_add=True)
    long_description = models.TextField(blank=True, default='', help_text='Detailed description shown on the product detail page')
    features = models.TextField(blank=True, default='', help_text='Key features, one per line')
    material = models.CharField(max_length=200, blank=True, default='', help_text='e.g. Wood, Plastic, Plush fabric')
    safety_info = models.TextField(blank=True, default='', help_text='Safety certifications and age warnings')
    dimensions = models.CharField(max_length=200, blank=True, default='', help_text='e.g. 30cm x 20cm x 15cm')

    def __str__(self):
        return self.name

    @property
    def discount_percentage(self):
        if self.original_price and self.original_price > self.price:
            return int(((self.original_price - self.price) / self.original_price) * 100)
        return 0

    class Meta:
        ordering = ['-created_at']
        

class WishlistItem(models.Model):

    ITEM_TYPE_CHOICES = [
        ('toy', 'Toy'),
        ('cloth', 'Cloth'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    
    item_type = models.CharField(max_length=10, choices=ITEM_TYPE_CHOICES)
    
    cloth = models.ForeignKey('Cloths', on_delete=models.CASCADE, blank=True, null=True, related_name='wishlisted_by')
    
    toy = models.ForeignKey('Toy', on_delete=models.CASCADE, blank=True, null=True, related_name='wishlisted_by')
    
    alert_threshold_percent = models.PositiveIntegerField(default=0)
    is_shared = models.BooleanField(default=False)
    last_alert_sent = models.DateTimeField(blank=True, null=True)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    price_alert_enabled = models.BooleanField(default=False)
    shared_at = models.DateTimeField(blank=True, null=True)
    
    added_at = models.DateTimeField(auto_now_add=True)
    
    
    class Meta:
        unique_together = [('user', 'cloth'), ('user', 'toy'),]
        
        ordering = ['-added_at']
        verbose_name = 'Wishlist Item'
        verbose_name_plural = 'Wishlist Items'
      
        
    
    def __str__(self):
        item = self.get_item()
        item_name = item.name if item else 'Unknown'
        return f"{self.user.username} - {item_name}"
    
    def get_item(self):
        return self.cloth if self.cloth else self.toy
    
    def get_price(self):
        if self.item_type == 'cloth':
            return self.cloth.price2 or self.cloth.price1 or self.cloth.price
        else:
            return str(self.toy.price)
    
    def get_category(self):
        item = self.get_item()
        return item.get_category_display() if hasattr(item, 'get_category_display') else item.category


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart', null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Cart for session {self.session_key}"
    
    def get_total(self):
        total = 0.0
        for item in self.items.all():
            try:
                total += float(item.get_subtotal())
            except Exception:
                continue
        return total
    
    def get_item_count(self):
        return sum(item.quantity for item in self.items.all())
    
    class Meta:
        verbose_name = 'Shopping Cart'
        verbose_name_plural = 'Shopping Carts'


class CartItem(models.Model):
    ITEM_TYPE_CHOICES = [
        ('toy', 'Toy'),
        ('cloth', 'Cloth'),
        ('offer', 'Offer'),
        ('arrival', 'New Arrival'),
    ]
    
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=10, choices=ITEM_TYPE_CHOICES)
    
    cloth = models.ForeignKey('Cloths', on_delete=models.CASCADE, null=True, blank=True)
    toy = models.ForeignKey('Toy', on_delete=models.CASCADE, null=True, blank=True)
    offer = models.ForeignKey('Offers', on_delete=models.CASCADE, null=True, blank=True)
    arrival = models.ForeignKey('NewArrivals', on_delete=models.CASCADE, null=True, blank=True)
    
    # Snapshot unit price at add-to-cart time so cart totals stay stable.
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        item = self.get_item()
        return f"{self.quantity}x {item.name if hasattr(item, 'name') else item.title}"
    
    def get_item(self):
        if self.cloth:
            return self.cloth
        elif self.toy:
            return self.toy
        elif self.offer:
            return self.offer
        elif self.arrival:
            return self.arrival
        return None
    
    @staticmethod
    def _to_float(value):
        """
        Convert values like 'Rs 1,299.00', '$45', '1200' safely to float.
        """
        if value is None:
            return 0.0
        if isinstance(value, (int, float, Decimal)):
            return float(value)

        s = str(value).strip()
        if not s:
            return 0.0

        # keep digits, dot, comma, minus
        s = re.sub(r'[^0-9,.\-]', '', s).replace(',', '')
        try:
            return float(s) if s else 0.0
        except ValueError:
            return 0.0

    def get_live_price(self):
        item = self.get_item()
        if not item:
            return 0.0

        if self.item_type == 'cloth':
            return self._to_float(item.price2 or item.price1 or item.price or 0)
        elif self.item_type == 'toy':
            return self._to_float(item.price)
        elif self.item_type == 'offer':
            return self._to_float(item.price1 or item.price2 or 0)
        elif self.item_type == 'arrival':
            return self._to_float(item.price or 0)
        return 0.0

    def get_price(self):
        if self.unit_price is not None:
            return float(self.unit_price)
        return self.get_live_price()
    
    def get_subtotal(self):
        return self.get_price() * self.quantity
    
    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    order_number = models.CharField(max_length=50, unique=True)
    
    # Shipping Information
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    
    # Order Details
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_code = models.CharField(max_length=30, blank=True, default='')
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, default='cash_on_delivery')
    tracking_number = models.CharField(max_length=100, blank=True, default='')
    estimated_delivery = models.DateField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Order {self.order_number} - {self.user.username}"
    
    class Meta:
        ordering = ['-created_at']


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=200)
    item_type = models.CharField(max_length=10)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.quantity}x {self.item_name}"


class ProductReview(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    PRODUCT_TYPE_CHOICES = [
        ('cloth', 'Cloth'),
        ('toy', 'Toy'),
        ('offer', 'Offer'),
        ('arrival', 'Arrival'),
    ]

    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPE_CHOICES)
    cloth = models.ForeignKey('Cloths', on_delete=models.CASCADE, blank=True, null=True, related_name='product_reviews')
    toy = models.ForeignKey('Toy', on_delete=models.CASCADE, blank=True, null=True, related_name='product_reviews')
    offer = models.ForeignKey('Offers', on_delete=models.CASCADE, blank=True, null=True, related_name='product_reviews')
    arrival = models.ForeignKey('NewArrivals', on_delete=models.CASCADE, blank=True, null=True, related_name='product_reviews')

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    rating = models.IntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.rating}/5"


# ══════════════════════════════════════════════════════
# PRODUCT IMAGE GALLERY
# ══════════════════════════════════════════════════════

class ProductImage(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('cloth', 'Cloth'),
        ('toy', 'Toy'),
        ('offer', 'Offer'),
        ('arrival', 'Arrival'),
    ]

    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPE_CHOICES)
    cloth = models.ForeignKey('Cloths', on_delete=models.CASCADE, blank=True, null=True, related_name='gallery_images')
    toy = models.ForeignKey('Toy', on_delete=models.CASCADE, blank=True, null=True, related_name='gallery_images')
    offer = models.ForeignKey('Offers', on_delete=models.CASCADE, blank=True, null=True, related_name='gallery_images')
    arrival = models.ForeignKey('NewArrivals', on_delete=models.CASCADE, blank=True, null=True, related_name='gallery_images')

    image = models.ImageField(upload_to='product_gallery/')
    alt_text = models.CharField(max_length=200, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order']
        verbose_name = 'Product Image'
        verbose_name_plural = 'Product Images'

    def __str__(self):
        return f"Image for {self.product_type} (order: {self.sort_order})"


# ══════════════════════════════════════════════════════
# INVENTORY MANAGEMENT
# ══════════════════════════════════════════════════════

class Inventory(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('cloth', 'Cloth'),
        ('toy', 'Toy'),
        ('offer', 'Offer'),
        ('arrival', 'Arrival'),
    ]

    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPE_CHOICES)
    cloth = models.OneToOneField('Cloths', on_delete=models.CASCADE, blank=True, null=True, related_name='inventory')
    toy = models.OneToOneField('Toy', on_delete=models.CASCADE, blank=True, null=True, related_name='inventory')
    offer = models.OneToOneField('Offers', on_delete=models.CASCADE, blank=True, null=True, related_name='inventory')
    arrival = models.OneToOneField('NewArrivals', on_delete=models.CASCADE, blank=True, null=True, related_name='inventory')

    stock = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)

    class Meta:
        verbose_name = 'Inventory'
        verbose_name_plural = 'Inventory'

    @property
    def is_in_stock(self):
        return self.stock > 0

    @property
    def is_low_stock(self):
        return 0 < self.stock <= self.low_stock_threshold

    def get_product(self):
        return self.cloth or self.toy or self.offer or self.arrival

    def __str__(self):
        product = self.get_product()
        name = getattr(product, 'name', None) or getattr(product, 'title', '?')
        return f"{name} — {self.stock} in stock"


# ══════════════════════════════════════════════════════
# COUPON / DISCOUNT SYSTEM
# ══════════════════════════════════════════════════════

class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    code = models.CharField(max_length=30, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_uses = models.PositiveIntegerField(default=0, help_text='0 = unlimited')
    used_count = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.max_uses > 0 and self.used_count >= self.max_uses:
            return False
        return True

    def get_discount(self, subtotal):
        if self.discount_type == 'percentage':
            return round(subtotal * self.discount_value / 100, 2)
        return min(self.discount_value, subtotal)

    def __str__(self):
        return f"{self.code} — {self.discount_value}{'%' if self.discount_type == 'percentage' else ' Rs'}"

    class Meta:
        ordering = ['-created_at']


# ══════════════════════════════════════════════════════
# SIZE / COLOR VARIANTS
# ══════════════════════════════════════════════════════

class ProductVariant(models.Model):
    cloth = models.ForeignKey('Cloths', on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=20, blank=True, help_text='e.g. S, M, L, XL')
    color = models.CharField(max_length=50, blank=True, help_text='e.g. Red, Blue')
    color_code = models.CharField(max_length=7, blank=True, help_text='e.g. #ff0000')
    extra_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['cloth', 'size', 'color']
        verbose_name = 'Product Variant'
        verbose_name_plural = 'Product Variants'

    def __str__(self):
        parts = []
        if self.size:
            parts.append(self.size)
        if self.color:
            parts.append(self.color)
        return f"{self.cloth.name} — {' / '.join(parts)}" if parts else self.cloth.name


# ══════════════════════════════════════════════════════
# ORDER TRACKING
# ══════════════════════════════════════════════════════

class OrderTracking(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='tracking_updates')
    status = models.CharField(max_length=20, choices=Order.STATUS_CHOICES)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order Tracking Update'
        verbose_name_plural = 'Order Tracking Updates'

    def __str__(self):
        return f"{self.order.order_number} → {self.get_status_display()} ({self.created_at:%Y-%m-%d %H:%M})"


# ══════════════════════════════════════════════════════
# SITE UPDATE TRACKER  (for real-time frontend refresh)
# ══════════════════════════════════════════════════════

class SiteUpdate(models.Model):
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site Update Tracker'

    @classmethod
    def touch(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        obj.save()
        return obj


class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.email

    class Meta:
        ordering = ['-subscribed_at']
        verbose_name = 'Newsletter Subscription'
        verbose_name_plural = 'Newsletter Subscriptions'


class LoyaltyProfile(models.Model):
    TIER_CHOICES = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='loyalty_profile')
    total_points_earned = models.PositiveIntegerField(default=0)
    current_points = models.PositiveIntegerField(default=0)
    tier = models.CharField(max_length=10, choices=TIER_CHOICES, default='bronze')
    
    def update_tier(self):
        if self.total_points_earned >= 5000:
            self.tier = 'gold'
        elif self.total_points_earned >= 1000:
            self.tier = 'silver'
        else:
            self.tier = 'bronze'
        self.save()

    def __str__(self):
        return f"{self.user.username} - {self.tier.title()} ({self.current_points} pts)"


class LoyaltyHistory(models.Model):
    profile = models.ForeignKey(LoyaltyProfile, on_delete=models.CASCADE, related_name='history')
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True)
    points = models.IntegerField()
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.user.username}: {self.points} pts - {self.description}"


# ══════════════════════════════════════════════════════
# SITE CONTENT MANAGEMENT
# ══════════════════════════════════════════════════════

class SiteBanner(models.Model):
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='banners/')
    link_url = models.CharField(max_length=200, default='/')
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = 'Site Banner'
        verbose_name_plural = 'Site Banners'

    def __str__(self):
        return self.title

class SiteSettings(models.Model):
    sale_text = models.CharField(max_length=200, default="Mega Summer Sale - Up to 50% Off!")
    is_sale_active = models.BooleanField(default=True)
    
    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'
