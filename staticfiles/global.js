/* ══════════════════════════════════════════════════════
   GLOBAL JS — Toast, Loading, Quick-View, Live Stock, Recently Viewed
   ══════════════════════════════════════════════════════ */

/* ── Toast Notifications ── */
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const colors = {
        success: 'bg-emerald-500 text-white',
        error: 'bg-red-500 text-white',
        danger: 'bg-red-500 text-white',
        warning: 'bg-amber-500 text-white',
        info: 'bg-indigo-500 text-white',
    };

    const icons = {
        success: 'bi-check-circle-fill',
        error: 'bi-exclamation-triangle-fill',
        danger: 'bi-exclamation-triangle-fill',
        warning: 'bi-exclamation-circle-fill',
        info: 'bi-info-circle-fill',
    };

    const colorClass = colors[type] || colors.info;
    const iconClass = icons[type] || icons.info;

    const toast = document.createElement('div');
    toast.className = `pointer-events-auto flex items-center gap-3 px-5 py-3 rounded-xl font-semibold text-sm shadow-lg ${colorClass} transform translate-x-full transition-transform duration-300`;
    toast.innerHTML = `<i class="bi ${iconClass}"></i><span>${message}</span>`;
    container.appendChild(toast);

    requestAnimationFrame(() => {
        toast.classList.remove('translate-x-full');
        toast.classList.add('translate-x-0');
    });

    setTimeout(() => {
        toast.classList.remove('translate-x-0');
        toast.classList.add('translate-x-full');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}


/* ── Loading Overlay ── */
function showLoading() {
    const el = document.getElementById('loadingOverlay');
    if (el) el.classList.remove('hidden');
}

function hideLoading() {
    const el = document.getElementById('loadingOverlay');
    if (el) el.classList.add('hidden');
}


/* ── Quick-View Modal ── */
let _quickViewData = {};

function openQuickView(data) {
    _quickViewData = data;
    const modal = document.getElementById('quickViewModal');
    if (!modal) return;

    document.getElementById('qvImage').src = data.image || '';
    document.getElementById('qvImage').alt = data.name || '';
    document.getElementById('qvName').textContent = data.name || '';
    document.getElementById('qvDesc').textContent = data.description || '';
    document.getElementById('qvPrice').textContent = data.price || '';
    document.getElementById('qvOldPrice').textContent = data.oldPrice || '';
    document.getElementById('qvBadge').textContent = data.badge || data.type || '';
    document.getElementById('qvDetailLink').href = data.url || '#';

    // Stock badge
    const stockEl = document.getElementById('qvStock');
    if (data.stock !== undefined) {
        if (data.stock <= 0) {
            stockEl.innerHTML = '<span class="px-3 py-1 rounded-full bg-red-100 text-red-700 text-xs">Out of Stock</span>';
        } else if (data.stock <= 5) {
            stockEl.innerHTML = `<span class="px-3 py-1 rounded-full bg-amber-100 text-amber-700 text-xs">Low Stock — Only ${data.stock} left</span>`;
        } else {
            stockEl.innerHTML = '<span class="px-3 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs">In Stock</span>';
        }
    } else {
        stockEl.innerHTML = '';
    }

    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeQuickView() {
    const modal = document.getElementById('quickViewModal');
    if (modal) modal.classList.add('hidden');
    document.body.style.overflow = '';
}

function quickAddToCart() {
    if (!_quickViewData.cartUrl) return;
    fetch(_quickViewData.cartUrl, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest' },
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showToast(data.message || 'Added to cart!', 'success');
            updateCartBadge(data.cart_count);
            closeQuickView();
        } else {
            showToast(data.error || 'Failed to add', 'error');
        }
    })
    .catch(() => showToast('Something went wrong', 'error'));
}


/* ── Cart Badge Updater ── */
function updateCartBadge(count) {
    document.querySelectorAll('[data-cart-count]').forEach(el => {
        el.textContent = count;
        el.style.display = count > 0 ? '' : 'none';
    });
}

function getCsrfToken() {
    const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
}


/* ── Live Stock Status Polling ── */
function initLiveStockUpdates() {
    const stockElements = document.querySelectorAll('[data-stock-product]');
    if (stockElements.length === 0) return;

    function refreshStock() {
        fetch('/api/stock-status/', {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(r => r.json())
        .then(data => {
            if (!data.products) return;
            data.products.forEach(p => {
                const key = `${p.type}-${p.id}`;
                document.querySelectorAll(`[data-stock-product="${key}"]`).forEach(el => {
                    if (p.stock <= 0) {
                        el.className = 'stock-badge stock-badge--out';
                        el.textContent = 'Out of Stock';
                    } else if (p.stock <= p.threshold) {
                        el.className = 'stock-badge stock-badge--low';
                        el.textContent = `Low Stock — ${p.stock} left`;
                    } else {
                        el.className = 'stock-badge stock-badge--in';
                        el.textContent = 'In Stock';
                    }
                });
            });
        })
        .catch(() => {});
    }

    refreshStock();
    setInterval(refreshStock, 30000); // Refresh every 30 seconds
}


/* ── Recently Viewed Products ── */
function trackRecentlyViewed(product) {
    if (!product || !product.id) return;
    let items = JSON.parse(localStorage.getItem('recentlyViewed') || '[]');
    items = items.filter(i => !(i.id === product.id && i.type === product.type));
    items.unshift(product);
    if (items.length > 10) items = items.slice(0, 10);
    localStorage.setItem('recentlyViewed', JSON.stringify(items));
}

function getRecentlyViewed() {
    return JSON.parse(localStorage.getItem('recentlyViewed') || '[]');
}

function renderRecentlyViewed(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const items = getRecentlyViewed();
    if (items.length === 0) { container.style.display = 'none'; return; }

    container.style.display = '';
    const grid = container.querySelector('.rv-grid');
    if (!grid) return;

    grid.innerHTML = items.slice(0, 6).map(item => `
        <a href="${item.url}" class="group block bg-white rounded-xl overflow-hidden shadow-sm hover:shadow-lg transition border border-slate-100">
            <div class="aspect-square overflow-hidden">
                <img src="${item.image}" alt="${item.name}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy">
            </div>
            <div class="p-3">
                <h4 class="text-sm font-semibold text-slate-800 truncate">${item.name}</h4>
                <p class="text-sm font-bold text-indigo-600 mt-1">${item.price}</p>
            </div>
        </a>
    `).join('');
}


/* ── Lazy Loading Images ── */
function initLazyImages() {
    if ('loading' in HTMLImageElement.prototype) return; // Native support
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                }
                observer.unobserve(img);
            }
        });
    });
    document.querySelectorAll('img[data-src]').forEach(img => observer.observe(img));
}


/* ── Auto-init ── */
document.addEventListener('DOMContentLoaded', function() {
    initLiveStockUpdates();
    initLazyImages();
    renderRecentlyViewed('recentlyViewedSection');
});
