# Integration Checklist - Phase 1 Features

## ✅ Completed Backend Implementation

### Models
- [x] ViewHistory model
- [x] Return model  
- [x] StockAlert model
- [x] CartAbandon model
- [x] OrderTracking enhancements (estimated_delivery, tracking_number, courier)

### Views
- [x] track_view_history() - Track product views
- [x] recently_viewed() - Display recently viewed products
- [x] order_tracking() - Display all user orders
- [x] order_details() - Display single order with tracking
- [x] initiate_return() - Create return request
- [x] return_status() - Track return progress
- [x] my_returns() - Display all user returns
- [x] stock_alert_settings() - Manage stock alerts
- [x] add_stock_alert() - Create stock alert

### URLs
- [x] All new routes added to urls.py
- [x] Proper name parameters for reverse()

### Templates
- [x] recently_viewed.html
- [x] order_details.html
- [x] initiate_return.html
- [x] return_status.html
- [x] my_returns.html
- [x] stock_alert_settings.html

### Admin
- [x] ViewHistoryAdmin
- [x] ReturnAdmin
- [x] StockAlertAdmin
- [x] CartAbandonAdmin

### Database
- [x] Migrations created and applied
- [x] All tables created successfully

---

## ⚠️ Frontend Integration Needed

### 1. Product Detail Page
**File:** `templates/product_detail.html`

**Changes Needed:**
```html
<!-- Add at the end of product_detail.html, before closing body -->

<!-- Track product view on page load -->
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Track this product view
    fetch('/track-view/{{ product_type }}/{{ product.id }}/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': '{{ csrf_token }}',
            'Content-Type': 'application/json'
        }
    }).catch(err => console.log('View tracked'));
});
</script>

<!-- Add stock alert button for out-of-stock items -->
{% if not inventory.stock %}
<div class="alert alert-warning mb-3">
    <button class="btn btn-primary" id="stock-alert-btn">
        <i class="bi bi-bell"></i> Notify Me When Available
    </button>
</div>

<script>
document.getElementById('stock-alert-btn').addEventListener('click', function(e) {
    e.preventDefault();
    this.disabled = true;
    this.innerHTML = '<span class="spinner-border spinner-border-sm mr-2"></span>Adding alert...';
    
    fetch('/stock-alert/{{ product_type }}/{{ product.id }}/add/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': '{{ csrf_token }}',
            'Content-Type': 'application/json'
        }
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert('✓ ' + data.message);
            this.innerHTML = '<i class="bi bi-check-circle"></i> You\'ll be notified';
        } else {
            alert('Error: ' + data.error);
            this.disabled = false;
            this.innerHTML = '<i class="bi bi-bell"></i> Notify Me When Available';
        }
    })
    .catch(err => {
        console.error(err);
        alert('Error adding alert');
        this.disabled = false;
        this.innerHTML = '<i class="bi bi-bell"></i> Notify Me When Available';
    });
});
</script>
{% endif %}
```

### 2. User Profile Menu (Navbar)
**File:** `templates/navbar.html`

**Changes Needed:**
```html
<!-- Find the user dropdown menu and add these links -->

<!-- In the user dropdown section, add: -->
<div class="dropdown-divider"></div>
<a class="dropdown-item" href="/orders/">
    <i class="bi bi-box-seam"></i> Track Orders
</a>
<a class="dropdown-item" href="/returns/">
    <i class="bi bi-arrow-counterclockwise"></i> My Returns
</a>
<a class="dropdown-item" href="/stock-alerts/">
    <i class="bi bi-bell"></i> Stock Alerts
</a>
<a class="dropdown-item" href="/recently-viewed/">
    <i class="bi bi-clock-history"></i> Recently Viewed
</a>
```

### 3. User Profile Dashboard
**File:** `templates/profile.html`

**Changes Needed:**
```html
<!-- Add these stat cards to the profile dashboard -->

<div class="row mt-4">
    <div class="col-md-3">
        <div class="card">
            <div class="card-body text-center">
                <h5 class="card-title">Active Returns</h5>
                <a href="/returns/" class="btn btn-sm btn-primary">
                    View Returns
                </a>
            </div>
        </div>
    </div>
    
    <div class="col-md-3">
        <div class="card">
            <div class="card-body text-center">
                <h5 class="card-title">Stock Alerts</h5>
                <a href="/stock-alerts/" class="btn btn-sm btn-primary">
                    Manage
                </a>
            </div>
        </div>
    </div>
    
    <div class="col-md-3">
        <div class="card">
            <div class="card-body text-center">
                <h5 class="card-title">Recently Viewed</h5>
                <a href="/recently-viewed/" class="btn btn-sm btn-primary">
                    View
                </a>
            </div>
        </div>
    </div>
</div>
```

### 4. Product Cards (All Pages)
**Files:** `templates/cloths.html`, `templates/toys.html`, etc.

**Changes Needed - Add stock alert button to out-of-stock cards:**
```html
<!-- Find the product card template and add this for out-of-stock items -->

{% if product.inventory.stock == 0 %}
<button class="btn btn-sm btn-outline-primary w-100 mt-2 add-stock-alert"
        data-product-type="{{ product_type }}"
        data-product-id="{{ product.id }}">
    <i class="bi bi-bell"></i> Notify Me
</button>

<script>
document.querySelectorAll('.add-stock-alert').forEach(btn => {
    btn.addEventListener('click', function(e) {
        e.preventDefault();
        const type = this.dataset.productType;
        const id = this.dataset.productId;
        
        fetch(`/stock-alert/${type}/${id}/add/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                'Content-Type': 'application/json'
            }
        })
        .then(r => r.json())
        .then(d => {
            if (d.success) {
                this.disabled = true;
                this.innerHTML = '<i class="bi bi-check-circle"></i> Alert Added';
            }
        });
    });
});
</script>
{% endif %}
```

---

## 📧 Email Integration Needed

### 1. Create Email Templates

**File:** `templates/emails/return_approved.html`
```html
<h2>Return Approved!</h2>
<p>Your return request #{{ return.id }} has been approved.</p>
<p>Item: {{ order_item.item_name }}</p>
<p>Refund Amount: Rs. {{ return.refund_amount }}</p>
<p>Please print the attached shipping label and ship the item back.</p>
```

**File:** `templates/emails/stock_available.html`
```html
<h2>Good News! Item Back in Stock</h2>
<p>{{ product.name }} is now available!</p>
<p>Price: Rs. {{ product.price }}</p>
<a href="{{ site_url }}/product/{{ product_type }}/{{ product.id }}/">View Product</a>
```

**File:** `templates/emails/return_processed.html`
```html
<h2>Return Processed</h2>
<p>Your return #{{ return.id }} has been processed.</p>
<p>Refund Amount: Rs. {{ return.refund_amount }}</p>
<p>Your refund will appear in your account within 5-7 business days.</p>
```

### 2. Add Email Sending to Views

**In `myapp/views.py`, add email sending functions:**

```python
def send_return_approved_email(return_obj):
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    
    html_message = render_to_string('emails/return_approved.html', {
        'return': return_obj,
        'order_item': return_obj.order_item
    })
    
    send_mail(
        subject=f'Return Approved - #{return_obj.id}',
        message='Return Approved',
        from_email='noreply@kidzone.com',
        recipient_list=[return_obj.order.user.email],
        html_message=html_message
    )

def send_stock_alert_email(alert):
    """Send email when item back in stock"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    
    # Get product
    product = alert.cloth or alert.toy or alert.offer or alert.arrival
    product_type = None
    if alert.cloth: product_type = 'cloth'
    elif alert.toy: product_type = 'toy'
    elif alert.offer: product_type = 'offer'
    elif alert.arrival: product_type = 'arrival'
    
    html_message = render_to_string('emails/stock_available.html', {
        'product': product,
        'product_type': product_type,
        'site_url': 'https://yoursite.com'
    })
    
    send_mail(
        subject=f'{product.name} is Back in Stock!',
        message='Item in stock',
        from_email='noreply@kidzone.com',
        recipient_list=[alert.user.email],
        html_message=html_message
    )
    
    alert.notified_at = timezone.now()
    alert.save()
```

---

## ⚙️ Admin Actions Needed

### In `myapp/admin.py`, add return approval actions:

```python
@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    # ... existing code ...
    actions = ['approve_return', 'reject_return', 'mark_shipped', 'mark_received', 'mark_processed']
    
    def approve_return(self, request, queryset):
        updated = queryset.update(status='approved')
        # Send emails
        for ret in queryset:
            send_return_approved_email(ret)
        self.message_user(request, f'{updated} returns approved and emails sent')
    approve_return.short_description = 'Approve selected returns'
    
    def mark_processed(self, request, queryset):
        updated = queryset.update(status='processed')
        # Send refund processed emails
        for ret in queryset:
            send_return_processed_email(ret)
        self.message_user(request, f'{updated} returns marked processed')
    mark_processed.short_description = 'Mark as processed & send refund email'
```

---

## 🔄 Celery Task Setup (Optional but Recommended)

**Create `myapp/tasks.py`:**
```python
from celery import shared_task
from django.utils import timezone
from .models import StockAlert, CartAbandon
from .views import send_stock_alert_email

@shared_task
def check_stock_alerts():
    """Check if alerted products are back in stock"""
    alerts = StockAlert.objects.filter(is_active=True, notified_at__isnull=True)
    
    for alert in alerts:
        product = alert.cloth or alert.toy or alert.offer or alert.arrival
        
        if hasattr(product, 'inventory') and product.inventory.stock > 0:
            send_stock_alert_email(alert)
```

---

## 🔍 Testing URLs (Development)

Test the new features with these URLs:

```
# View tracking
GET/POST /track-view/cloth/1/
GET/POST /track-view/toy/1/
GET/POST /track-view/offer/1/
GET/POST /track-view/arrival/1/

# Recently viewed
GET /recently-viewed/

# Orders
GET /orders/
GET /order/ORD-123456/
POST /order/ORD-123456/return/

# Returns
GET /returns/
GET /return/1/status/

# Stock alerts
POST /stock-alert/cloth/1/add/
GET /stock-alerts/
POST /stock-alerts/ (remove action)
```

---

## 📋 Priority Order for Integration

1. **High Priority:**
   - [ ] Add tracking script to product_detail.html
   - [ ] Add user dropdown menu items to navbar
   - [ ] Add stock alert button to product cards
   - [ ] Test order tracking (/orders/ page)

2. **Medium Priority:**
   - [ ] Add profile dashboard links
   - [ ] Create email templates
   - [ ] Add admin actions for returns
   - [ ] Test return workflow

3. **Low Priority:**
   - [ ] Setup Celery for stock alerts
   - [ ] Add abandoned cart recovery
   - [ ] Create analytics dashboard
   - [ ] Optimize database queries

---

## ✨ UI/UX Enhancement Recommendations

1. **Color Scheme:**
   - Pending: Yellow (#FFC107)
   - Processing: Blue (#007BFF)
   - Shipped: Purple (#6F42C1)
   - Delivered: Green (#28A745)

2. **Icons (Bootstrap Icons):**
   - Orders: `bi-box-seam`
   - Returns: `bi-arrow-counterclockwise`
   - Tracking: `bi-map`
   - Stock Alert: `bi-bell`
   - Recently Viewed: `bi-clock-history`

3. **Animations:**
   - Fade in on page load
   - Slide transitions between tabs
   - Smooth status updates
   - Loading spinners on buttons

---

**Last Updated:** Today
**Status:** Ready for Frontend Integration
