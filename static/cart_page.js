document.addEventListener('DOMContentLoaded', function () {
    loadCart();
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function getCsrfToken() {
    // 1) cookie (normal)
    const fromCookie = getCookie('csrftoken');
    if (fromCookie) return fromCookie;

    // 2) hidden input fallback (your checkout form already has csrf token)
    const hidden = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (hidden && hidden.value) return hidden.value;

    return '';
}

const csrftoken = getCsrfToken();

async function loadCart() {
    try {
        const response = await fetch('/cart/get/');
        const data = await response.json();

        if (data.success) {
            renderCart(data);
        } else {
            console.error('Error loading cart:', data.error);
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

function renderCart(data) {
    const cartItemsDiv = document.getElementById('cartItems');
    const emptyCartMsg = document.getElementById('emptyCartMessage');

    if (!cartItemsDiv) return;

    cartItemsDiv.innerHTML = '';

    if (data.items.length === 0) {
        if (emptyCartMsg) emptyCartMsg.style.display = 'block';
    } else {
        if (emptyCartMsg) emptyCartMsg.style.display = 'none';

        data.items.forEach((item) => {
            const cartItem = document.createElement('div');
            cartItem.className = 'cart-item';
            cartItem.dataset.itemId = item.id;
            const detailUrl = item.product_url || '#';
            cartItem.innerHTML = `
                <div class="cart-item-img-wrap">
                    <a href="${detailUrl}">
                        <img src="${item.image}" alt="${item.name}" onerror="this.src='/static/placeholder.jpg'">
                    </a>
                    <a href="${detailUrl}" class="cart-quick-view">Quick View</a>
                </div>
                <div class="item-details">
                    <h3><a href="${detailUrl}" class="cart-item-link">${item.name}</a></h3>
                    <p>${item.item_type.charAt(0).toUpperCase() + item.item_type.slice(1)}</p>
                    <div class="item-price">Rs ${item.price.toFixed(2)}</div>
                    <div class="quantity-control">
                        <button class="qty-btn" onclick="updateQuantity(${item.id}, ${item.quantity - 1})">-</button>
                        <input type="number" class="qty-input" value="${item.quantity}" min="1" 
                               onchange="updateQuantity(${item.id}, this.value)">
                        <button class="qty-btn" onclick="updateQuantity(${item.id}, ${item.quantity + 1})">+</button>
                    </div>
                </div>
                <button class="remove-btn" onclick="removeItem(${item.id})">Remove</button>
            `;
            cartItemsDiv.appendChild(cartItem);
        });
    }

    updateSummary(data);
    updateCartCount(data.cart_count);
}

async function updateQuantity(itemId, quantity) {
    quantity = parseInt(quantity);
    if (quantity < 1) return;

    try {
        const response = await fetch(`/cart/update/${itemId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ quantity: quantity })
        });

        const data = await response.json();
        if (data.success) {
            loadCart();
        } else {
            alert('Error updating cart: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error updating cart');
    }
}

async function removeItem(itemId) {
    if (!confirm('Remove this item from cart?')) return;

    try {
        const response = await fetch(`/cart/remove/${itemId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        const data = await response.json();
        if (data.success) {
            loadCart();
            showToast(data.message);
        } else {
            alert('Error removing item: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error removing item');
    }
}

// Optional clear cart support if you add a clear button
async function clearCart() {
    try {
        const response = await fetch('/cart/clear/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        const data = await response.json();
        if (data.success) loadCart();
    } catch (e) {
        console.error(e);
    }
}

function updateSummary(data) {
    const subtotalEl = document.getElementById('subtotal');
    const taxEl = document.getElementById('tax');
    const totalEl = document.getElementById('total');

    if (subtotalEl) subtotalEl.textContent = `Rs ${data.subtotal.toFixed(2)}`;
    if (taxEl) taxEl.textContent = `Rs ${data.tax.toFixed(2)}`;
    if (totalEl) totalEl.textContent = `Rs ${data.total.toFixed(2)}`;
}

function updateCartCount(count) {
    const cartCountElements = document.querySelectorAll('.cart-count');
    cartCountElements.forEach(el => {
        el.textContent = count;
    });
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        background: rgba(15, 23, 42, 0.95);
        color: #fff;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
        z-index: 9999;
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}