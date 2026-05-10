from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse, HttpResponse
import csv
import json
from .models import (
    Cloths, Toy, Offers, NewArrivals, Order, OrderItem, 
    Inventory, Review, ServiceReview, ProductReview, 
    ContactMessage, SiteBanner, SiteSettings, User, Coupon
)

@staff_member_required
def update_banner_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        order = data.get('order', [])
        for index, banner_id in enumerate(order):
            SiteBanner.objects.filter(id=banner_id).update(order=index)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
from .admin_forms import ClothsForm, ToyForm, OffersForm, NewArrivalsForm, CouponForm, SiteSettingsForm

@staff_member_required
def dashboard(request):
    """Admin Dashboard with statistics overview"""
    today = timezone.now().date()
    
    # Stats aggregation
    total_orders = Order.objects.count()
    recent_orders = Order.objects.all()[:10]
    total_sales = Order.objects.filter(status='delivered').aggregate(Sum('total'))['total__sum'] or 0
    total_users = User.objects.count()
    
    # Low stock alerts
    low_stock_items = Inventory.objects.filter(stock__lte=5)
    
    # Recent activity
    recent_reviews = ProductReview.objects.all()[:5]
    recent_messages = ContactMessage.objects.filter(is_read=False)[:5]
    
    # Sales Data for Chart (Last 30 days)
    sales_labels = []
    sales_data = []
    for i in range(29, -1, -1):
        date = today - timedelta(days=i)
        day_total = Order.objects.filter(created_at__date=date, status='delivered').aggregate(Sum('total'))['total__sum'] or 0
        sales_labels.append(date.strftime('%b %d'))
        sales_data.append(float(day_total))
    
    context = {
        'total_orders': total_orders,
        'total_sales': total_sales,
        'total_users': total_users,
        'recent_orders': recent_orders,
        'low_stock_items': low_stock_items,
        'recent_reviews': recent_reviews,
        'recent_messages': recent_messages,
        'sales_labels': sales_labels,
        'sales_data': sales_data,
        'active_tab': 'dashboard'
    }
    return render(request, 'admin/dashboard.html', context)

@staff_member_required
def product_list(request):
    """List all products across types"""
    cloths = Cloths.objects.all()
    toys = Toy.objects.all()
    offers = Offers.objects.all()
    arrivals = NewArrivals.objects.all()
    
    context = {
        'cloths': cloths,
        'toys': toys,
        'offers': offers,
        'arrivals': arrivals,
        'active_tab': 'products'
    }
    return render(request, 'admin/products/list.html', context)

@staff_member_required
def product_upsert(request, item_type, item_id=None):
    """Add or Edit a product across all types"""
    model_map = {
        'cloth': (Cloths, ClothsForm),
        'toy': (Toy, ToyForm),
        'offer': (Offers, OffersForm),
        'arrival': (NewArrivals, NewArrivalsForm),
    }
    
    if item_type not in model_map:
        messages.error(request, "Invalid product type")
        return redirect('custom_admin:product_list')
    
    model_class, form_class = model_map[item_type]
    instance = get_object_or_404(model_class, id=item_id) if item_id else None
    
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, f"{item_type.title()} product saved successfully!")
            return redirect('custom_admin:product_list')
    else:
        form = form_class(instance=instance)
    
    return render(request, 'admin/products/form.html', {
        'form': form,
        'item_type': item_type,
        'is_edit': bool(item_id),
        'active_tab': 'products'
    })

@staff_member_required
def product_delete(request, item_type, item_id):
    """Delete a product"""
    model_map = {'cloth': Cloths, 'toy': Toy, 'offer': Offers, 'arrival': NewArrivals}
    if item_type in model_map:
        instance = get_object_or_404(model_map[item_type], id=item_id)
        instance.delete()
        messages.success(request, f"Deleted {item_type.title()} product.")
    return redirect('custom_admin:product_list')

@staff_member_required
def coupon_list(request):
    coupons = Coupon.objects.all()
    return render(request, 'admin/coupons/list.html', {'coupons': coupons, 'active_tab': 'coupons'})

@staff_member_required
def coupon_upsert(request, coupon_id=None):
    instance = get_object_or_404(Coupon, id=coupon_id) if coupon_id else None
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon saved successfully!")
            return redirect('custom_admin:coupon_list')
    else:
        form = CouponForm(instance=instance)
    return render(request, 'admin/products/form.html', {
        'form': form,
        'item_type': 'Coupon',
        'is_edit': bool(coupon_id),
        'active_tab': 'coupons'
    })

@staff_member_required
def coupon_delete(request, coupon_id):
    coupon = get_object_or_404(Coupon, id=coupon_id)
    coupon.delete()
    messages.success(request, "Coupon deleted.")
    return redirect('custom_admin:coupon_list')

@staff_member_required
def order_list(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'admin/orders/list.html', {'orders': orders, 'active_tab': 'orders'})

@staff_member_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'admin/orders/detail.html', {'order': order, 'active_tab': 'orders'})

@staff_member_required
def order_invoice(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'admin/orders/invoice.html', {'order': order})

@staff_member_required
def order_status_update(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        status = request.POST.get('status')
        order.status = status
        order.save()
        messages.success(request, f"Order {order.order_number} status updated to {status}")
    return redirect('custom_admin:order_detail', order_id=order_id)

@staff_member_required
def inventory_manage(request):
    inventory = Inventory.objects.all()
    total_stock = sum(item.stock for item in inventory)
    out_of_stock_count = sum(1 for item in inventory if item.stock == 0)
    low_stock_count = sum(1 for item in inventory if item.is_low_stock)
    return render(request, 'admin/inventory.html', {
        'inventory': inventory,
        'total_stock': total_stock,
        'out_of_stock_count': out_of_stock_count,
        'low_stock_count': low_stock_count,
        'active_tab': 'inventory'
    })


@staff_member_required
def inventory_export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory_export.csv"'

    writer = csv.writer(response)
    writer.writerow(['Product', 'Type', 'SKU', 'Stock', 'Threshold', 'Status'])

    for item in Inventory.objects.select_related('cloth', 'toy', 'offer', 'arrival').all():
        product = item.get_product()
        product_name = getattr(product, 'name', None) or getattr(product, 'title', 'Inventory Item')
        status = 'Low Stock' if item.is_low_stock else ('Out of Stock' if item.stock == 0 else 'Healthy')
        writer.writerow([product_name, item.product_type, item.sku or '', item.stock, item.low_stock_threshold, status])

    return response

@staff_member_required
def feedback_manage(request):
    product_reviews = ProductReview.objects.all()
    service_reviews = ServiceReview.objects.all()
    messages_unread = ContactMessage.objects.filter(is_read=False)
    return render(request, 'admin/feedback.html', {
        'product_reviews': product_reviews,
        'service_reviews': service_reviews,
        'messages': messages_unread,
        'active_tab': 'feedback'
    })

@staff_member_required
def settings_manage(request):
    banners = SiteBanner.objects.all().order_by('order')
    settings = SiteSettings.get_settings()
    settings_form = SiteSettingsForm(request.POST or None, instance=settings)

    if request.method == 'POST' and settings_form.is_valid():
        settings_form.save()
        messages.success(request, 'Site settings updated successfully.')
        return redirect('custom_admin:settings_manage')

    return render(request, 'admin/settings.html', {
        'banners': banners,
        'settings': settings,
        'settings_form': settings_form,
        'active_tab': 'settings'
    })


@staff_member_required
def contact_message_toggle_read(request, message_id):
    message_obj = get_object_or_404(ContactMessage, id=message_id)
    if request.method == 'POST':
        message_obj.is_read = not message_obj.is_read
        message_obj.save(update_fields=['is_read'])
        messages.success(request, f"Message marked as {'read' if message_obj.is_read else 'unread'}.")
    return redirect('custom_admin:feedback_manage')


@staff_member_required
def product_review_delete(request, review_id):
    review = get_object_or_404(ProductReview, id=review_id)
    if request.method == 'POST':
        review.delete()
        messages.success(request, 'Product review deleted.')
    return redirect('custom_admin:feedback_manage')
