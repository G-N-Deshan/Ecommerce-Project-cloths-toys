# How to Use Cart Utils and Add to Cart Buttons

## Step 1: Include cart_utils.js in your base template

Add this line in your base template's `<head>` or before `</body>`:

```html
<script src="{% static 'cart_utils.js' %}"></script>
```

Make sure it loads BEFORE your page-specific scripts.

## Step 2: Add data attributes to ALL "Add to Cart" buttons

Every button that should add items to cart needs these THREE attributes:

1. `data-add-to-cart` - Identifies this as an add-to-cart button
2. `data-item-type` - The type of item: "toy", "cloth", "offer", or "arrival"
3. `data-item-id` - The database ID of the item

### Example:

```html
<button 
    class="add-to-cart-btn" 
    data-add-to-cart
    data-item-type="toy" 
    data-item-id="{{ toy.id }}">
    Add to Cart
</button>
```

## Step 3: Add cart count display to your navigation

```html
<a href="{% url 'cart' %}" class="cart-link">
    🛒 Cart
    <span class="cart-count" data-cart-count>{{ cart_count|default:0 }}</span>
</a>
```

## Step 4: Button Types Supported

The system works with ANY button/link that has the required data attributes:

- `<button data-add-to-cart data-item-type="toy" data-item-id="1">Add to Cart</button>`
- `<a data-add-to-cart data-item-type="cloth" data-item-id="5">Buy Now</a>`
- `<div data-add-to-cart data-item-type="offer" data-item-id="3">Shop Now</div>`

## Step 5: Item Types Reference

| Item Type | Description | Database Model |
|-----------|-------------|----------------|
| `toy` | Toys | Toy model |
| `cloth` | Clothing items | Cloths model |
| `offer` | Special offers | Offers model |
| `arrival` | New arrivals | NewArrivals model |

## Complete Working Example:

```html
<!-- In your offers loop -->
{% for offer in offers %}
<div class="offer-card">
    <img src="{{ offer.imageUrl.url }}" alt="{{ offer.title }}">
    <h3>{{ offer.title }}</h3>
    <p>${{ offer.price2 }}</p>
    
    <button 
        class="btn-primary" 
        data-add-to-cart
        data-item-type="offer" 
        data-item-id="{{ offer.id }}">
        🛒 Add to Cart
    </button>
</div>
{% endfor %}
```

## No JavaScript Required in Your Templates!

The cart_utils.js file handles everything automatically. Just add the data attributes and it works!

## Testing Checklist:

- [ ] cart_utils.js is loaded in base template
- [ ] All buttons have `data-add-to-cart` attribute
- [ ] All buttons have `data-item-type` attribute (toy/cloth/offer/arrival)
- [ ] All buttons have `data-item-id` attribute with correct ID
- [ ] Cart count badge is in navigation with `data-cart-count` or class `cart-count`
- [ ] CSRF token is properly configured in Django settings
