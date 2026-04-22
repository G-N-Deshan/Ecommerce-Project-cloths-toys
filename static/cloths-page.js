(function () {
    'use strict';

    var MAX_COMPARE = 3;
    var COMPARE_KEY = 'clothsCompareItems';
    var VIEWED_KEY = 'recentlyViewed';
    var AB_KEY = 'cloths_ab_variant';

    function safeJsonParse(raw, fallback) {
        try {
            return JSON.parse(raw);
        } catch (e) {
            return fallback;
        }
    }

    function getCompared() {
        return safeJsonParse(localStorage.getItem(COMPARE_KEY) || '[]', []);
    }

    function setCompared(items) {
        localStorage.setItem(COMPARE_KEY, JSON.stringify(items));
    }

    function upsertCompared(item) {
        var items = getCompared();
        var exists = items.some(function (x) { return String(x.id) === String(item.id); });
        if (exists) {
            items = items.filter(function (x) { return String(x.id) !== String(item.id); });
        } else {
            if (items.length >= MAX_COMPARE) return { ok: false, reason: 'limit' };
            items.push(item);
        }
        setCompared(items);
        return { ok: true, items: items };
    }

    function clearCompared() {
        setCompared([]);
    }

    function updateCompareUI() {
        var items = getCompared();
        var bar = document.getElementById('compareBar');
        var count = document.getElementById('compareCount');
        if (!bar || !count) return;

        count.textContent = items.length + ' of 3 selected';
        bar.hidden = items.length === 0;

        document.querySelectorAll('[data-compare-toggle]').forEach(function (btn) {
            var id = btn.getAttribute('data-product-id');
            var active = items.some(function (x) { return String(x.id) === String(id); });
            btn.classList.toggle('btn-compare--active', active);
            btn.textContent = active ? 'Selected' : 'Compare';
        });
    }

    function buildCompareTable() {
        var table = document.getElementById('compareTable');
        if (!table) return;
        var items = getCompared();
        if (items.length < 2) {
            table.innerHTML = '<tr><td>Please select at least 2 products.</td></tr>';
            return;
        }

        function row(label, key) {
            var tds = items.map(function (item) {
                return '<td>' + (item[key] || 'N/A') + '</td>';
            }).join('');
            return '<tr><th>' + label + '</th>' + tds + '</tr>';
        }

        var headerCells = items.map(function (item) {
            return '<th><img src="' + item.image + '" alt="' + item.name + '" /><div>' + item.name + '</div></th>';
        }).join('');

        table.innerHTML = [
            '<tr><th>Product</th>' + headerCells + '</tr>',
            row('Price', 'price'),
            row('Category', 'category'),
            row('Subcategory', 'subcategory'),
            row('Material', 'material'),
            row('Sizes', 'sizes'),
            '<tr><th>Action</th>' + items.map(function (item) {
                return '<td><a href="' + item.url + '">View Product</a></td>';
            }).join('') + '</tr>'
        ].join('');
    }

    function openCompareModal() {
        buildCompareTable();
        var modal = document.getElementById('compareModal');
        if (modal) modal.hidden = false;
    }

    function closeCompareModal() {
        var modal = document.getElementById('compareModal');
        if (modal) modal.hidden = true;
    }

    function trackViewed(item) {
        var viewed = safeJsonParse(localStorage.getItem(VIEWED_KEY) || '[]', []);
        viewed = viewed.filter(function (x) { return !(String(x.id) === String(item.id) && x.type === item.type); });
        viewed.unshift(item);
        if (viewed.length > 10) viewed = viewed.slice(0, 10);
        localStorage.setItem(VIEWED_KEY, JSON.stringify(viewed));
    }

    function renderRecentlyViewed() {
        var section = document.getElementById('recentlyViewedSection');
        if (!section) return;
        var grid = section.querySelector('.rv-grid');
        if (!grid) return;

        var viewed = safeJsonParse(localStorage.getItem(VIEWED_KEY) || '[]', []);
        var cloths = viewed.filter(function (x) { return x.type === 'cloth'; }).slice(0, 6);
        if (!cloths.length) {
            section.style.display = 'none';
            return;
        }

        section.style.display = '';
        grid.innerHTML = cloths.map(function (item) {
            return (
                '<a href="' + item.url + '" class="mini-product-card">' +
                '<img src="' + item.image + '" alt="' + item.name + '" loading="lazy">' +
                '<div><h3>' + item.name + '</h3><p>' + (item.category || '') + '</p><span>' + (item.price || '') + '</span></div>' +
                '</a>'
            );
        }).join('');
    }

    function applyPersonalizationAndAB() {
        var variant = localStorage.getItem(AB_KEY);
        if (!variant) {
            variant = Math.random() > 0.5 ? 'A' : 'B';
            localStorage.setItem(AB_KEY, variant);
        }

        var title = document.getElementById('recommendTitle');
        var subtitle = document.getElementById('recommendSubtitle');
        if (title && subtitle) {
            if (variant === 'A') {
                title.textContent = 'Recommended For You';
                subtitle.textContent = 'Smart picks based on what customers explore the most.';
            } else {
                title.textContent = 'Best Match Picks';
                subtitle.textContent = 'Personalized selection tuned by browsing behavior.';
            }
        }

        var viewed = safeJsonParse(localStorage.getItem(VIEWED_KEY) || '[]', []);
        var prefCategory = viewed.find(function (x) { return x.type === 'cloth' && x.categorySlug; });

        if (prefCategory) {
            var container = document.querySelector('.mini-grid--recommend');
            if (container) {
                var items = Array.prototype.slice.call(container.querySelectorAll('[data-recommend-item]'));
                items.sort(function (a, b) {
                    var aHit = a.getAttribute('data-category') === prefCategory.categorySlug ? 1 : 0;
                    var bHit = b.getAttribute('data-category') === prefCategory.categorySlug ? 1 : 0;
                    return bHit - aHit;
                });
                items.forEach(function (el) { container.appendChild(el); });
            }
        }
    }

    function attachHandlers() {
        document.querySelectorAll('[data-product-card]').forEach(function (card) {
            var link = card.querySelector('.product-card__image-wrap');
            if (!link) return;
            link.addEventListener('click', function () {
                var nameEl = card.querySelector('h3');
                var priceEl = card.querySelector('.price-current');
                var categoryEl = card.querySelector('.product-category');
                var imgEl = card.querySelector('img');
                var compareBtn = card.querySelector('[data-compare-toggle]');
                trackViewed({
                    id: compareBtn ? compareBtn.getAttribute('data-product-id') : '',
                    type: 'cloth',
                    name: nameEl ? nameEl.textContent : '',
                    price: priceEl ? priceEl.textContent : '',
                    category: categoryEl ? categoryEl.textContent : '',
                    categorySlug: compareBtn ? (compareBtn.getAttribute('data-product-category') || '').toLowerCase() : '',
                    image: imgEl ? imgEl.getAttribute('src') : '',
                    url: link.getAttribute('href')
                });
            });
        });

        document.querySelectorAll('[data-compare-toggle]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var payload = {
                    id: btn.getAttribute('data-product-id'),
                    name: btn.getAttribute('data-product-name'),
                    price: btn.getAttribute('data-product-price'),
                    category: btn.getAttribute('data-product-category'),
                    subcategory: btn.getAttribute('data-product-subcategory'),
                    material: btn.getAttribute('data-product-material'),
                    sizes: btn.getAttribute('data-product-sizes'),
                    image: btn.getAttribute('data-product-image'),
                    url: btn.getAttribute('data-product-url')
                };

                var result = upsertCompared(payload);
                if (!result.ok && result.reason === 'limit') {
                    if (window.showToast) window.showToast('Select up to 3 products only.', 'warning');
                }
                updateCompareUI();
            });
        });

        var openBtn = document.getElementById('compareOpenBtn');
        var closeBtn = document.getElementById('compareCloseBtn');
        var clearBtn = document.getElementById('compareClearBtn');
        var backdrop = document.getElementById('compareBackdrop');

        if (openBtn) openBtn.addEventListener('click', openCompareModal);
        if (closeBtn) closeBtn.addEventListener('click', closeCompareModal);
        if (backdrop) backdrop.addEventListener('click', closeCompareModal);
        if (clearBtn) {
            clearBtn.addEventListener('click', function () {
                clearCompared();
                updateCompareUI();
                closeCompareModal();
            });
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        attachHandlers();
        updateCompareUI();
        renderRecentlyViewed();
        applyPersonalizationAndAB();
    });
})();
