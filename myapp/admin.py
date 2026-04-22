
from django.contrib import admin
from django.utils.html import format_html
from .models import (Card, Cloths, Offers, NewArrivals, Review, ContactMessage, Toy,
                     WishlistItem, Cart, CartItem, Order, OrderItem, ProductReview,
                     ProductImage, Inventory, Coupon, ProductVariant, OrderTracking)

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
            'fields': ('long_description', 'features', 'material'),
            'description': 'These fields appear on the product detail page. '
                           'For "Features", enter one feature per line.',
            'classes': ('collapse',),
        }),
    )


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
            'fields': ('long_description', 'features', 'material'),
            'description': 'These fields appear on the product detail page. '
                           'For "Features", enter one feature per line.',
            'classes': ('collapse',),
        }),
    )


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
            'fields': ('long_description', 'features', 'material', 'care_instructions', 'sizes_available'),
            'description': 'These fields appear on the product detail page. '
                           'Enter "Features" one per line. '
                           'Enter "Sizes" comma-separated (e.g. S, M, L, XL).',
            'classes': ('collapse',),
        }),
    )

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
            'fields': ('long_description', 'features', 'material', 'safety_info', 'dimensions'),
            'description': 'These fields appear on the product detail page. '
                           'Enter "Features" one per line.',
            'classes': ('collapse',),
        }),
    )
    
    
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
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline, OrderTrackingInline]
    actions = ['mark_processing', 'mark_shipped', 'mark_delivered', 'mark_cancelled']
    
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
    list_display = ['get_product_name', 'product_type', 'sku', 'stock', 'low_stock_threshold', 'stock_status']
    list_filter = ['product_type']
    search_fields = ['sku']
    list_editable = ['stock', 'low_stock_threshold']

    def get_product_name(self, obj):
        product = obj.get_product()
        return getattr(product, 'name', None) or getattr(product, 'title', '?')
    get_product_name.short_description = 'Product'

    def stock_status(self, obj):
        if not obj.is_in_stock:
            return format_html('<span style="color:#ef4444;font-weight:600">Out of Stock</span>')
        if obj.is_low_stock:
            return format_html('<span style="color:#f59e0b;font-weight:600">Low Stock</span>')
        return format_html('<span style="color:#10b981;font-weight:600">In Stock</span>')
    stock_status.short_description = 'Status'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'min_order_amount', 'used_count', 'max_uses', 'is_active', 'valid_until', 'coupon_status']
    list_filter = ['discount_type', 'is_active']
    search_fields = ['code']
    list_editable = ['is_active']
    readonly_fields = ['used_count', 'created_at']

    def coupon_status(self, obj):
        if obj.is_valid():
            return format_html('<span style="color:#10b981;font-weight:600">Active</span>')
        return format_html('<span style="color:#ef4444;font-weight:600">Expired/Invalid</span>')
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

