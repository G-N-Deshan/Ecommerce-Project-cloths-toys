from django.contrib import admin
from django.utils.html import format_html, mark_safe
from .models import (Card, Cloths, Offers, NewArrivals, Review, ContactMessage, Toy,
                     WishlistItem, Cart, CartItem, Order, OrderItem, ProductReview,
                     ProductImage, Inventory, Coupon, ProductVariant, OrderTracking,
                     SiteBanner, SiteSettings, ViewHistory, Return, StockAlert, CartAbandon,
                     NewsletterSubscription, TrendingProduct)
from .models import ServiceReview

# Admin site branding
admin.site.site_header = 'KidZone Admin Dashboard'
admin.site.site_title = 'KidZone Admin'
admin.site.index_title = 'Manage Your Store'


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ['name', 'image_preview']
    search_fields = ['name']
    
    def image_preview(self, obj):
        if obj.imageUrl:
            return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:6px" />', obj.imageUrl.url)
        return '-'
    image_preview.short_description = 'Image'


@admin.register(Offers)
class OffersAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'offers_badge', 'price1', 'price2', 'end_time']
    list_filter = ['category']
    search_fields = ['title', 'description']
    ordering = ['-id']
    fieldsets = (
        ('Basic Info', {
            'fields': ('imageUrl', 'title', 'offers_badge', 'description', 'button_text', 'category'),
        }),
        ('Pricing', {
            'fields': ('price1', 'price2', 'stock_text', 'end_time'),
        }),
        ('Product Detail Page Content', {
            'fields': ('long_description', 'features', 'material', 'sizes_available', 'colors_available'),
            'description': 'These fields appear on the product detail page. '
                           'For "Features", enter one feature per line.',
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        if is_new:
            from .views import _notify_users_of_new_product
            _notify_users_of_new_product(obj, product_type='offer', request=request)


@admin.register(NewArrivals)
class NewArrivalsAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'offers_badge', 'price']
    list_filter = ['category']
    search_fields = ['title', 'description']
    ordering = ['-id']
    fieldsets = (
        ('Basic Info', {
            'fields': ('imageUrl', 'title', 'offers_badge', 'description', 'price', 'category'),
        }),
        ('Product Detail Page Content', {
            'fields': ('long_description', 'features', 'material', 'sizes_available', 'colors_available'),
            'description': 'These fields appear on the product detail page. '
                           'For "Features", enter one feature per line.',
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        if is_new:
            from .views import _notify_users_of_new_product
            _notify_users_of_new_product(obj, product_type='arrival', request=request)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('size', 'color', 'color_code', 'extra_price', 'stock')


@admin.register(Cloths)
class ClothsAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'subcategory', 'price1', 'discount_text']
    list_filter = ['category', 'subcategory']
    search_fields = ['name', 'desccription']
    ordering = ['-id']
    fieldsets = (
        ('Basic Info', {
            'fields': ('imageUrl', 'name', 'desccription', 'category', 'subcategory'),
        }),
        ('Pricing', {
            'fields': ('price', 'price1', 'price2', 'discount_text'),
        }),
        ('Product Detail Page Content', {
            'fields': ('long_description', 'features', 'material', 'care_instructions', 'sizes_available', 'colors_available'),
            'description': 'These fields appear on the product detail page. '
                           'Enter "Features" one per line. '
                           'Enter "Sizes" comma-separated (e.g. S, M, L, XL).',
            'classes': ('collapse',),
        }),
    )
    inlines = [ProductVariantInline]

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        if is_new:
            from .views import _notify_users_of_new_product
            _notify_users_of_new_product(obj, product_type='cloth', request=request)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['name', 'email']

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'created_at', 'is_read']
    list_filter = ['created_at', 'is_read']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['created_at']
    actions = ['mark_as_read', 'mark_as_unread']
    
    @admin.action(description='Mark selected messages as read')
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    
    @admin.action(description='Mark selected messages as unread')
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)


@admin.register(ServiceReview)
class ServiceReviewAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'email',
        'topic',
        'overall_rating',
        'is_verified_customer',
        'is_approved',
        'helpful_count',
        'created_at',
    ]
    list_filter = ['topic', 'is_verified_customer', 'is_approved', 'created_at']
    search_fields = ['name', 'email', 'comment']
    readonly_fields = ['overall_rating', 'created_at', 'updated_at', 'helpful_count', 'report_count']
    actions = ['approve_reviews', 'mark_unapproved']

    @admin.action(description='Approve selected service reviews')
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description='Mark selected service reviews as unapproved')
    def mark_unapproved(self, request, queryset):
        queryset.update(is_approved=False)
    
    
@admin.register(Toy)
class ToyAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'age_range', 'price', 'is_bestseller', 'is_new']
    list_filter = ['category', 'age_range', 'is_bestseller', 'is_new']
    search_fields = ['name', 'description']
    fieldsets = (
        ('Basic Info', {
            'fields': ('imageUrl', 'name', 'description', 'category', 'age_range'),
        }),
        ('Pricing & Flags', {
            'fields': ('price', 'original_price', 'rating', 'is_bestseller', 'is_new'),
        }),
        ('Product Detail Page Content', {
            'fields': ('long_description', 'features', 'material', 'safety_info', 'dimensions', 'sizes_available', 'colors_available'),
            'description': 'These fields appear on the product detail page. '
                           'Enter "Features" one per line.',
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        if is_new:
            from .views import _notify_users_of_new_product
            _notify_users_of_new_product(obj, product_type='toy', request=request)


    
@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'item_type', 'get_item_name', 'added_at']
    list_filter = ['item_type', 'added_at', 'user']
    search_fields = ['user__username', 'cloth__name', 'toy__name']
    readonly_fields = ['added_at']
    
    def get_item_name(self, obj):
        return obj.get_item().name
    
    get_item_name.short_description = 'Item Name'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'get_item_count', 'get_total', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'session_key']
    
    class CartItemInline(admin.TabularInline):
        model = CartItem
        extra = 0
        readonly_fields = ['item_type', 'cloth', 'toy', 'offer', 'arrival', 'quantity', 'get_subtotal_display']
        
        def get_subtotal_display(self, obj):
            return f"Rs. {obj.get_subtotal():.2f}"
        get_subtotal_display.short_description = 'Subtotal'
    
    inlines = [CartItemInline]
    
    def get_item_count(self, obj):
        return obj.get_item_count()
    
    def get_total(self, obj):
        return f"Rs. {obj.get_total():.2f}"
    
    get_item_count.short_description = 'Items'
    get_total.short_description = 'Total'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'cart', 'item_type', 'get_item_name', 'quantity', 'get_subtotal']
    list_filter = ['item_type', 'added_at']
    
    def get_item_name(self, obj):
        item = obj.get_item()
        return item.name if hasattr(item, 'name') else item.title
    
    def get_subtotal(self, obj):
        return f"${obj.get_subtotal():.2f}"
    
    get_item_name.short_description = 'Item'
    get_subtotal.short_description = 'Subtotal'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['item_name', 'item_type', 'quantity', 'price', 'subtotal']
    can_delete = False


class OrderTrackingInline(admin.TabularInline):
    model = OrderTracking
    extra = 1
    readonly_fields = ['created_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'full_name', 'total', 'status_badge', 'payment_method', 'created_at']
    list_filter = ['status', 'created_at', 'payment_method']
    search_fields = ['order_number', 'user__username', 'email', 'full_name']
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'user', 'subtotal', 'tax', 'shipping', 'discount', 'total']
    list_editable = ['payment_method']
    list_select_related = ['user']
    list_per_page = 30
    date_hierarchy = 'created_at'
    save_on_top = True
    inlines = [OrderItemInline, OrderTrackingInline]
    actions = ['mark_processing', 'mark_shipped', 'mark_delivered', 'mark_cancelled', 'delete_cancelled_orders', 'delete_selected_orders']
    
    fieldsets = (
        ('Order Info', {
            'fields': ('order_number', 'user', 'status', 'payment_method', 'created_at', 'updated_at'),
        }),
        ('Customer Info', {
            'fields': ('full_name', 'email', 'phone'),
        }),
        ('Shipping Address', {
            'fields': ('address', 'city', 'postal_code', 'country'),
        }),
        ('Tracking', {
            'fields': ('tracking_number', 'estimated_delivery'),
        }),
        ('Pricing', {
            'fields': ('subtotal', 'discount', 'coupon_code', 'tax', 'shipping', 'total'),
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'processing': '#6366f1',
            'shipped': '#3b82f6',
            'delivered': '#10b981',
            'cancelled': '#ef4444',
        }
        color = colors.get(obj.status, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    @admin.action(description='Mark as Processing')
    def mark_processing(self, request, queryset):
        queryset.update(status='processing')
    
    @admin.action(description='Mark as Shipped')
    def mark_shipped(self, request, queryset):
        queryset.update(status='shipped')
    
    @admin.action(description='Mark as Delivered')
    def mark_delivered(self, request, queryset):
        queryset.update(status='delivered')
    
    @admin.action(description='Mark as Cancelled')
    def mark_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
    
    @admin.action(description='🗑️ Delete Selected Orders (Permanently)')
    def delete_selected_orders(self, request, queryset):
        """
        Custom delete action with proper confirmation and audit trail.
        """
        from django.contrib import messages
        count = queryset.count()
        
        # Delete order items first (cascade safety)
        OrderItem.objects.filter(order__in=queryset).delete()
        
        # Delete order tracking updates
        OrderTracking.objects.filter(order__in=queryset).delete()
        
        # Delete orders
        queryset.delete()
        
        messages.success(
            request,
            f'✅ Successfully deleted {count} order{"s" if count > 1 else ""} and their associated data.'
        )
    
    @admin.action(description='🗑️ Delete Only Cancelled Orders')
    def delete_cancelled_orders(self, request, queryset):
        """
        Delete only orders with 'cancelled' status as a safety measure.
        """
        from django.contrib import messages
        
        cancelled_orders = queryset.filter(status='cancelled')
        count = cancelled_orders.count()
        
        if count == 0:
            messages.warning(request, 'No cancelled orders selected to delete.')
            return
        
        # Delete order items first
        OrderItem.objects.filter(order__in=cancelled_orders).delete()
        
        # Delete order tracking updates
        OrderTracking.objects.filter(order__in=cancelled_orders).delete()
        
        # Delete orders
        cancelled_orders.delete()
        
        messages.success(
            request,
            f'✅ Successfully deleted {count} cancelled order{"s" if count > 1 else ""}.'
        )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'item_name', 'quantity', 'price', 'subtotal']
    list_filter = ['item_type']


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['name', 'product_type', 'rating', 'title', 'created_at']
    list_filter = ['product_type', 'rating', 'created_at']
    search_fields = ['name', 'title', 'comment']
    readonly_fields = ['created_at']


# ══════════════════════════════════════════════════════
# NEW MODEL REGISTRATIONS
# ══════════════════════════════════════════════════════

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'sort_order', 'image_preview']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:6px" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Preview'


class InventoryInline(admin.StackedInline):
    model = Inventory
    extra = 0
    max_num = 1
    fields = ['sku', 'stock', 'low_stock_threshold']


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['size', 'color', 'color_code', 'extra_price', 'stock']


# Add inlines to existing product admins
ClothsAdmin.inlines = [ProductImageInline, InventoryInline, ProductVariantInline]
ToyAdmin.inlines = [ProductImageInline, InventoryInline]
OffersAdmin.inlines = [ProductImageInline, InventoryInline]
NewArrivalsAdmin.inlines = [ProductImageInline, InventoryInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'product_type', 'alt_text', 'sort_order', 'image_preview']
    list_filter = ['product_type']
    search_fields = ['alt_text']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:6px" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Preview'


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['get_product_name', 'product_type', 'sku', 'stock', 'low_stock_threshold', 'stock_badge']
    list_filter = ['product_type']
    search_fields = ['sku', 'cloth__name', 'toy__name', 'offer__title', 'arrival__title']
    list_editable = ['stock']
    ordering = ['stock', 'sku']
    list_per_page = 50

    def get_product_name(self, obj):
        product = obj.get_product()
        return getattr(product, 'name', None) or getattr(product, 'title', '?')
    get_product_name.short_description = 'Product'

    def stock_badge(self, obj):
        if not obj.is_in_stock:
            return format_html('<span style="color:{};font-weight:600">{}</span>', '#ef4444', 'Out of Stock')
        if obj.is_low_stock:
            return format_html('<span style="color:{};font-weight:600">{}</span>', '#f59e0b', 'Low Stock')
        return format_html('<span style="color:{};font-weight:600">{}</span>', '#10b981', 'In Stock')
    stock_badge.short_description = 'Status'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'min_order_amount', 'used_count', 'max_uses', 'is_active', 'valid_until', 'coupon_status']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['code']
    list_editable = ['is_active']
    readonly_fields = ['used_count', 'created_at']

    def coupon_status(self, obj):
        if obj.is_valid():
            return format_html('<span style="color:{};font-weight:600">{}</span>', '#10b981', 'Active')
        return format_html('<span style="color:{};font-weight:600">{}</span>', '#ef4444', 'Expired/Invalid')
    coupon_status.short_description = 'Status'


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ['cloth', 'size', 'color', 'color_swatch', 'extra_price', 'stock']
    list_filter = ['size', 'color']
    search_fields = ['cloth__name', 'size', 'color']

    def color_swatch(self, obj):
        if obj.color_code:
            return format_html(
                '<span style="display:inline-block;width:20px;height:20px;background:{};border-radius:50%;border:1px solid #ccc"></span>',
                obj.color_code
            )
        return '-'
    color_swatch.short_description = 'Color'


@admin.register(OrderTracking)
class OrderTrackingAdmin(admin.ModelAdmin):
    list_display = ['order', 'status', 'note', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order__order_number']
    readonly_fields = ['created_at']


@admin.register(SiteBanner)
class SiteBannerAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_active', 'order', 'created_at']
    list_filter = ['is_active']
    search_fields = ['title', 'subtitle']
    list_editable = ['is_active', 'order']
    ordering = ['order', 'id']


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ['sale_text', 'is_sale_active']


# ════════════════════════════════════════════════════
# New Models Admin (Phase 1 Features)
# ════════════════════════════════════════════════════

@admin.register(ViewHistory)
class ViewHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_product_name', 'viewed_at']
    list_filter = ['viewed_at', 'user']
    search_fields = ['user__username']
    readonly_fields = ['user', 'cloth', 'toy', 'offer', 'arrival', 'viewed_at']
    
    def get_product_name(self, obj):
        if obj.cloth:
            return f"Cloth: {obj.cloth.name}"
        elif obj.toy:
            return f"Toy: {obj.toy.name}"
        elif obj.offer:
            return f"Offer: {obj.offer.title}"
        elif obj.arrival:
            return f"Arrival: {obj.arrival.title}"
        return "Unknown"
    get_product_name.short_description = 'Product'


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'order_item', 'status', 'initiated_at', 'refund_amount']
    list_filter = ['status', 'initiated_at', 'reason']
    search_fields = ['order__order_number', 'order__user__username', 'order_item__item_name']
    fieldsets = (
        ('Order Information', {
            'fields': ('order', 'order_item'),
        }),
        ('Return Details', {
            'fields': ('reason', 'description', 'status', 'refund_amount'),
        }),
        ('Timestamps', {
            'fields': ('initiated_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['initiated_at', 'updated_at']
    
    def get_order_number(self, obj):
        return obj.order.order_number
    get_order_number.short_description = 'Order Number'


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_product_name', 'is_active', 'created_at', 'notified_at']
    list_filter = ['is_active', 'created_at', 'notified_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'notified_at']
    fieldsets = (
        ('User', {
            'fields': ('user',),
        }),
        ('Product', {
            'fields': ('cloth', 'toy', 'offer', 'arrival'),
        }),
        ('Status', {
            'fields': ('is_active', 'notified_at'),
        }),
    )
    
    def get_product_name(self, obj):
        if obj.cloth:
            return f"Cloth: {obj.cloth.name}"
        elif obj.toy:
            return f"Toy: {obj.toy.name}"
        elif obj.offer:
            return f"Offer: {obj.offer.title}"
        elif obj.arrival:
            return f"Arrival: {obj.arrival.title}"
        return "Unknown"
    get_product_name.short_description = 'Product'


@admin.register(CartAbandon)
class CartAbandonAdmin(admin.ModelAdmin):
    list_display = ['get_user_info', 'cart_total', 'abandoned_at', 'recovered', 'email_sent']
    list_filter = ['recovered', 'email_sent', 'abandoned_at']
    search_fields = ['user__username', 'user__email', 'session_key']
    readonly_fields = ['abandoned_at']
    fieldsets = (
        ('Cart Information', {
            'fields': ('user', 'session_key', 'cart_total'),
        }),
        ('Recovery Status', {
            'fields': ('recovered', 'email_sent', 'abandoned_at'),
        }),
    )
    
    def get_user_info(self, obj):
        if obj.user:
            return f"{obj.user.username} ({obj.user.email})"
        return f"Anonymous ({obj.session_key[:8]}...)"
    get_user_info.short_description = 'User/Session'

@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['email', 'subscribed_at']
    list_filter = ['subscribed_at']
    search_fields = ['email']
    readonly_fields = ['subscribed_at']
    ordering = ['-subscribed_at']


@admin.register(TrendingProduct)
class TrendingProductAdmin(admin.ModelAdmin):
    list_display = ['get_image', 'name', 'get_linked_product_label', 'category', 'price', 'order', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'category']
    list_editable = ['order', 'is_active', 'price']
    ordering = ['order', '-created_at']
    actions = ['auto_promote_top_cloths', 'auto_promote_top_toys', 'auto_promote_top_offers', 'auto_promote_top_arrivals']

    fieldsets = (
        ('Display Info', {
            'fields': ('name', 'image', 'price', 'original_price', 'badge', 'category'),
        }),
        ('Link to Real Product (Preferred)', {
            'fields': ('cloth', 'toy', 'offer', 'arrival'),
            'description': (
                '⚡ Pick ONE product from below. This enables Add to Cart, Buy Now, '
                'live stock, and ratings automatically. Leave all blank to use the local detail page.'
            ),
        }),
        ('Product Detail Page Content (Local Only)', {
            'fields': ('long_description', 'features', 'material', 'care_instructions', 'sizes_available', 'colors_available', 'safety_info', 'dimensions'),
            'description': 'These fields appear on the product detail page if no real product is linked above.',
            'classes': ('collapse',),
        }),
        ('Legacy Fallback URL', {
            'fields': ('link_url',),
            'description': 'Only used if no product is linked above.',
            'classes': ('collapse',),
        }),
        ('Status & Order', {
            'fields': ('is_active', 'order'),
        }),
    )

    def get_image(self, obj):
        img = obj.resolved_image
        if img and hasattr(img, 'url'):
            try:
                return format_html('<img src="{}" style="width:50px;height:50px;border-radius:8px;object-fit:cover;" />', img.url)
            except Exception:
                pass
        return '-'
    get_image.short_description = 'Image'

    def get_linked_product_label(self, obj):
        t = obj.resolved_item_type
        if t:
            p = obj.get_linked_product()
            label = getattr(p, 'name', None) or getattr(p, 'title', '?')
            colors = {'cloth': '#6366f1', 'toy': '#f59e0b', 'offer': '#ef4444', 'arrival': '#10b981', 'trending': '#64748b'}
            return format_html(
                '<span style="background:{};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700">{}</span> {}',
                colors.get(t, '#64748b'), t.upper(), label
            )
        return mark_safe('<span style="color:#94a3b8;font-size:11px">Local Only</span>')
    get_linked_product_label.short_description = 'Linked Product'

    # ── Admin actions to auto-promote top-viewed products ──────────────────

    @admin.action(description='🔥 Auto-promote Top 5 Most-Viewed Cloths to Trending')
    def auto_promote_top_cloths(self, request, queryset):
        from .models import Cloths
        self._promote_top(request, Cloths, 'cloth', 'men', 5)

    @admin.action(description='🧸 Auto-promote Top 5 Most-Viewed Toys to Trending')
    def auto_promote_top_toys(self, request, queryset):
        from .models import Toy
        self._promote_top(request, Toy, 'toys', 'toys', 5)

    @admin.action(description='🏷️ Auto-promote Top 5 Most-Viewed Offers to Trending')
    def auto_promote_top_offers(self, request, queryset):
        from .models import Offers
        self._promote_top(request, Offers, 'offer', 'men', 5)

    @admin.action(description='✨ Auto-promote Top 5 Most-Viewed New Arrivals to Trending')
    def auto_promote_top_arrivals(self, request, queryset):
        from .models import NewArrivals
        self._promote_top(request, NewArrivals, 'arrival', 'men', 5)

    def _promote_top(self, request, model_class, src_type, default_category, count):
        from django.contrib import messages
        top_items = model_class.objects.order_by('-view_count')[:count]
        created = 0
        skipped = 0

        for item in top_items:
            name = getattr(item, 'name', None) or getattr(item, 'title', '')
            # Avoid duplicates by name
            if TrendingProduct.objects.filter(name=name).exists():
                skipped += 1
                continue

            price = (getattr(item, 'price2', None) or getattr(item, 'price1', None)
                     or getattr(item, 'price', None) or '0')
            price = str(price)
            image = item.imageUrl
            item_cat = getattr(item, 'category', default_category)
            trending_cat = item_cat if item_cat in ['kids', 'men', 'women', 'toys'] else default_category

            kwargs = dict(
                name=name,
                image=image,
                price=price,
                category=trending_cat,
                badge='Trending',
                is_active=True,
                order=0,
            )
            # Set the correct FK
            if src_type == 'cloth':     kwargs['cloth'] = item
            elif src_type == 'toy':     kwargs['toy'] = item
            elif src_type == 'offer':   kwargs['offer'] = item
            elif src_type == 'arrival': kwargs['arrival'] = item

            TrendingProduct.objects.create(**kwargs)
            created += 1

        messages.success(
            request,
            f'✅ Promoted {created} product(s) to Trending. Skipped {skipped} already existing.'
        )

    # ── Change-list: show view rankings panel ──────────────────────────────

    def changelist_view(self, request, extra_context=None):
        from .models import Cloths, Toy, Offers, NewArrivals
        extra_context = extra_context or {}

        top_cloths   = list(Cloths.objects.order_by('-view_count').values('id', 'name', 'view_count', 'category')[:10])
        top_toys     = list(Toy.objects.order_by('-view_count').values('id', 'name', 'view_count', 'category')[:10])
        top_offers   = list(Offers.objects.order_by('-view_count').values('id', 'title', 'view_count', 'category')[:10])
        top_arrivals = list(NewArrivals.objects.order_by('-view_count').values('id', 'title', 'view_count', 'category')[:10])

        for item in top_offers:   item['name'] = item.pop('title'); item['type'] = 'Offer'
        for item in top_arrivals: item['name'] = item.pop('title'); item['type'] = 'New Arrival'
        for item in top_cloths:   item['type'] = 'Cloth'
        for item in top_toys:     item['type'] = 'Toy'

        all_products = top_cloths + top_toys + top_offers + top_arrivals
        all_products.sort(key=lambda x: x['view_count'], reverse=True)

        extra_context['view_rankings'] = all_products[:15]
        return super().changelist_view(request, extra_context=extra_context)
