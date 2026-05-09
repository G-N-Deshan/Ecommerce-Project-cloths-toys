/**
 * Global cart utility functions
 * Used across all pages to manage cart state
 */

// Inject spinner keyframes
if (!document.getElementById('cartSpinStyle')) {
    const s = document.createElement('style');
    s.id = 'cartSpinStyle';
    s.textContent = '@keyframes cartSpin{to{transform:rotate(360deg)}}';
    document.head.appendChild(s);
}

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

if (window.__cartUtilsBootstrapped) {
    console.log('✓ Cart Utils already loaded, skipping initialization');
} else {
    window.__cartUtilsBootstrapped = true;

    async function addToCart(itemType, itemId, buttonElement = null, unitPrice = null, options = {}) {
        const fallbackUrl = `/cart/add/${itemType}/${itemId}/`;

        try {
            if (buttonElement?.dataset.loading === '1') return false;
            if (buttonElement) {
                buttonElement.dataset.loading = '1';
                buttonElement._origHTML = buttonElement.innerHTML;
                buttonElement.innerHTML = '<span class="cart-spinner" style="display:inline-block;width:14px;height:14px;border:2px solid rgba(255,255,255,.4);border-top-color:#fff;border-radius:50%;animation:cartSpin .5s linear infinite;vertical-align:middle;margin-right:6px;"></span> Adding...';
                buttonElement.disabled = true;
            }

            const csrftoken = getCookie('csrftoken');

            // If CSRF cookie missing, use safe GET fallback
            if (!csrftoken) {
                window.location.href = fallbackUrl;
                return false;
            }

            const payload = { unit_price: unitPrice };
            if (options && typeof options === 'object') {
                if (options.size) payload.size = options.size;
                if (options.color) payload.color = options.color;
                if (options.quantity) payload.quantity = options.quantity;
                if (options.variant_extra_price !== undefined) {
                    payload.variant_extra_price = options.variant_extra_price;
                }
            }

            const response = await fetch(fallbackUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrftoken,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                // e.g., 403/500 -> fallback
                window.location.href = fallbackUrl;
                return false;
            }

            const data = await response.json();

            if (data.success) {
                updateGlobalCartCount(data.cart_count);

                if (buttonElement) {
                    const origHTML = buttonElement._origHTML || buttonElement.textContent;
                    const originalBg = buttonElement.style.background;
                    buttonElement.innerHTML = '✓ Added!';
                    buttonElement.style.background = '#10b981';

                    setTimeout(() => {
                        buttonElement.innerHTML = origHTML;
                        buttonElement.style.background = originalBg;
                    }, 1200);
                }

                showGlobalToast(data.message);
                return true;
            }

            showGlobalToast('Error: ' + (data.error || 'Failed'), 'error');
            return false;
        } catch (error) {
            console.error('Error adding to cart:', error);
            // Final fallback path
            window.location.href = fallbackUrl;
            return false;
        } finally {
            if (buttonElement) {
                delete buttonElement.dataset.loading;
                buttonElement.disabled = false;
            }
        }
    }

    window.addToCart = addToCart;

    document.addEventListener('DOMContentLoaded', function () {
        console.log('🛒 Cart Utils: Initializing global cart functionality...');
        loadCartCount();

        document.body.addEventListener('click', function (e) {
            const btn = e.target.closest('[data-add-to-cart]');
            if (!btn || e.defaultPrevented) return;

            const itemType = btn.dataset.itemType;
            const itemId = btn.dataset.itemId;
            
            if (!itemType || !itemId) {
                console.error('Missing data-item-type or data-item-id:', btn);
                return;
            }

            e.preventDefault();
            e.stopPropagation();
            console.log(`Adding ${itemType} #${itemId} to cart...`);

            const card = btn.closest('[data-price], [data-product-price], .product-card, article, .card');
            const unitPrice =
                btn.dataset.productPrice ||
                (card && (card.dataset.productPrice || card.dataset.price)) ||
                null;

            addToCart(itemType, itemId, btn, unitPrice);
        });

        console.log('✅ Cart Utils: Ready!');
    });
}

function updateGlobalCartCount(count) {
    const cartElements = document.querySelectorAll('.cart-count, .cart-badge, [data-cart-count]');
    cartElements.forEach(el => {
        el.textContent = count;
        if (count > 0) {
            el.style.display = 'inline-block';
            el.classList.add('has-items');
        } else {
            el.classList.remove('has-items');
        }
    });
    
    // Cache cart count in localStorage for instant display on next page load
    try {
        localStorage.setItem('kids_cart_count', count);
    } catch(e) {
        // localStorage not available
    }
}

function showGlobalToast(message, type = 'success') {
    const existing = document.querySelector('.global-toast');
    if (existing) existing.remove();
    
    const toast = document.createElement('div');
    toast.className = 'global-toast';
    toast.textContent = message;
    
    const bgColor = type === 'success' ? 'rgba(16, 185, 129, 0.95)' : 'rgba(239, 68, 68, 0.95)';
    
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        background: ${bgColor};
        color: #fff;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
        z-index: 99999;
        animation: slideIn 0.3s ease;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

async function loadCartCount() {
    try {
        const response = await fetch('/cart/get/');
        const data = await response.json();
        
        if (data.success) {
            updateGlobalCartCount(data.cart_count);
        }
    } catch (error) {
        console.error('Error loading cart count:', error);
    }
}

// Add CSS animations if not already present
if (!document.querySelector('#cart-utils-styles')) {
    const style = document.createElement('style');
    style.id = 'cart-utils-styles';
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(400px); opacity: 0; }
        }
        .cart-badge.has-items {
            animation: pulse 0.3s ease;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.2); }
        }
        [data-add-to-cart] {
            cursor: pointer;
            transition: all 0.2s ease;
        }
        [data-add-to-cart]:hover {
            opacity: 0.9;
            transform: translateY(-1px);
        }
    `;
    document.head.appendChild(style);
}

console.log('✅ cart_utils.js loaded');
