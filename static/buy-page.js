(function () {
    'use strict';

    var VIEWED_KEY = 'buyRecentlyViewed';
    var COMPARE_KEY = 'buyCompareItems';
    var AB_KEY = 'buy_ab_variant';
    var MAX_COMPARE = 3;

    function parseJson(raw, fallback) {
        try { return JSON.parse(raw); } catch (e) { return fallback; }
    }

    function toPrice(raw) {
        if (!raw) return 0;
        var s = String(raw).trim();
        // Remove leading non-digits (like "Rs. ") which cause parsing errors if they contain dots
        s = s.replace(/^[^0-9]+/, '');
        s = s.replace(/[^0-9,.-]/g, '').replace(/,/g, '');
        var n = parseFloat(s);
        return Number.isFinite(n) ? n : 0;
    }

    function text(v) {
        return String(v || '').trim();
    }

    function escapeHtml(s) {
        return text(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function getProducts() {
        return Array.prototype.slice.call(document.querySelectorAll('.js-buy-product'));
    }

    function getFilterState() {
        return {
            search: text(document.getElementById('buySearchInput')?.value).toLowerCase(),
            type: text(document.getElementById('buyTypeSelect')?.value || 'all'),
            category: text(document.getElementById('buyCategorySelect')?.value || 'all'),
            sort: text(document.getElementById('buySortSelect')?.value || 'featured')
        };
    }

    function matchProduct(product, state) {
        var name = text(product.dataset.name).toLowerCase();
        var desc = text(product.dataset.description).toLowerCase();
        var type = text(product.dataset.kind);
        var category = text(product.dataset.category);

        if (state.search && !(name.includes(state.search) || desc.includes(state.search))) return false;
        if (state.type !== 'all' && type !== state.type) return false;
        if (state.category !== 'all' && category !== state.category) return false;
        return true;
    }

    function applySortToGrid(gridEl, state) {
        if (!gridEl) return;
        var cards = Array.prototype.slice.call(gridEl.querySelectorAll('.js-buy-product'));
        var sorted = cards.slice();

        if (state.sort === 'price_low') {
            sorted.sort(function (a, b) { return toPrice(a.dataset.price) - toPrice(b.dataset.price); });
        } else if (state.sort === 'price_high') {
            sorted.sort(function (a, b) { return toPrice(b.dataset.price) - toPrice(a.dataset.price); });
        } else if (state.sort === 'rating_high') {
            sorted.sort(function (a, b) { return parseFloat(b.dataset.rating || '0') - parseFloat(a.dataset.rating || '0'); });
        } else {
            sorted.sort(function (a, b) {
                return parseInt(b.dataset.id || '0', 10) - parseInt(a.dataset.id || '0', 10);
            });
        }

        sorted.forEach(function (item) { gridEl.appendChild(item); });
    }

    function updateActiveChips(state) {
        var chips = [];
        if (state.search) chips.push('Search: ' + state.search);
        if (state.type !== 'all') chips.push('Type: ' + state.type);
        if (state.category !== 'all') chips.push('Category: ' + state.category);
        if (state.sort !== 'featured') chips.push('Sort: ' + state.sort.replace('_', ' '));

        var target = document.getElementById('buyActiveChips');
        if (!target) return;
        target.innerHTML = chips.map(function (c) { return '<span class="buy-chip">' + escapeHtml(c) + '</span>'; }).join('');
    }

    function applyFilters() {
        var state = getFilterState();
        var products = getProducts();
        var visible = 0;

        products.forEach(function (product) {
            var ok = matchProduct(product, state);
            product.style.display = ok ? '' : 'none';
            if (ok) visible += 1;
        });

        applySortToGrid(document.getElementById('offersGrid'), state);
        applySortToGrid(document.getElementById('arrivalsGrid'), state);

        var resultCount = document.getElementById('buyResultCount');
        if (resultCount) resultCount.textContent = 'Showing ' + visible + ' products';

        updateActiveChips(state);
    }

    function resetFilters() {
        var search = document.getElementById('buySearchInput');
        var type = document.getElementById('buyTypeSelect');
        var cat = document.getElementById('buyCategorySelect');
        var sort = document.getElementById('buySortSelect');
        if (search) search.value = '';
        if (type) type.value = 'all';
        if (cat) cat.value = 'all';
        if (sort) sort.value = 'featured';
        applyFilters();
    }

    function getViewed() {
        return parseJson(localStorage.getItem(VIEWED_KEY) || '[]', []);
    }

    function setViewed(items) {
        localStorage.setItem(VIEWED_KEY, JSON.stringify(items));
    }

    function trackViewedFromCard(card) {
        if (!card) return;
        var item = {
            id: card.dataset.id,
            kind: card.dataset.kind,
            category: card.dataset.category,
            name: card.dataset.name,
            price: card.dataset.price,
            image: card.dataset.image,
            url: card.dataset.url,
            rating: card.dataset.rating
        };

        var list = getViewed().filter(function (x) { return !(String(x.id) === String(item.id) && x.kind === item.kind); });
        list.unshift(item);
        if (list.length > 12) list = list.slice(0, 12);
        setViewed(list);
    }

    function renderRecentlyViewed() {
        var section = document.getElementById('buyRecentlyViewedSection');
        var grid = document.getElementById('buyRecentlyViewedGrid');
        if (!section || !grid) return;

        var items = getViewed().slice(0, 6);
        if (!items.length) {
            section.hidden = true;
            return;
        }

        section.hidden = false;
        grid.innerHTML = items.map(function (item) {
            return (
                '<a href="' + escapeHtml(item.url) + '" class="proof-mini-item">' +
                '<img src="' + escapeHtml(item.image) + '" alt="' + escapeHtml(item.name) + '" loading="lazy">' +
                '<div><strong>' + escapeHtml(item.name) + '</strong><span>' + escapeHtml(item.price) + '</span></div>' +
                '</a>'
            );
        }).join('');
    }

    function applyPersonalization() {
        var section = document.getElementById('buyPersonalizedSection');
        var grid = document.getElementById('buyPersonalizedGrid');
        var title = document.getElementById('buyRecoTitle');
        var subtitle = document.getElementById('buyRecoSubtitle');
        if (!section || !grid || !title || !subtitle) return;

        var variant = localStorage.getItem(AB_KEY);
        if (!variant) {
            variant = Math.random() > 0.5 ? 'A' : 'B';
            localStorage.setItem(AB_KEY, variant);
        }

        if (variant === 'A') {
            title.textContent = 'Recommended For You';
            subtitle.textContent = 'Personalized based on your recent interactions.';
        } else {
            title.textContent = 'Best Match Picks';
            subtitle.textContent = 'Curated from products customers like you explore most.';
        }

        var viewed = getViewed();
        if (!viewed.length) {
            section.hidden = true;
            return;
        }

        var catCount = {};
        viewed.forEach(function (x) {
            var c = x.category || 'all';
            catCount[c] = (catCount[c] || 0) + 1;
        });

        var prefCategory = Object.keys(catCount).sort(function (a, b) { return catCount[b] - catCount[a]; })[0];
        var products = getProducts().filter(function (card) {
            return card.dataset.category === prefCategory;
        }).slice(0, 4);

        if (!products.length) {
            section.hidden = true;
            return;
        }

        section.hidden = false;
        grid.innerHTML = products.map(function (card) {
            return (
                '<a href="' + escapeHtml(card.dataset.url) + '" class="proof-mini-item">' +
                '<img src="' + escapeHtml(card.dataset.image) + '" alt="' + escapeHtml(card.dataset.name) + '" loading="lazy">' +
                '<div><strong>' + escapeHtml(card.dataset.name) + '</strong><span>' + escapeHtml(card.dataset.price) + '</span></div>' +
                '</a>'
            );
        }).join('');
    }

    function openQuickView(card) {
        var modal = document.getElementById('buyQuickView');
        if (!modal || !card) return;

        document.getElementById('buyQvImage').src = card.dataset.image || '';
        document.getElementById('buyQvImage').alt = card.dataset.name || '';
        document.getElementById('buyQvKind').textContent = (card.dataset.kind || '').toUpperCase();
        document.getElementById('buyQvTitle').textContent = card.dataset.name || '';
        document.getElementById('buyQvDesc').textContent = card.dataset.description || '';
        document.getElementById('buyQvPrice').textContent = card.dataset.price || '';
        document.getElementById('buyQvRating').textContent = card.dataset.rating && parseFloat(card.dataset.rating) > 0 ? ('Rating: ' + parseFloat(card.dataset.rating).toFixed(1)) : 'No rating yet';
        document.getElementById('buyQvStock').textContent = card.dataset.stock || '';
        document.getElementById('buyQvLink').href = card.dataset.url || '#';

        modal.hidden = false;
    }

    function closeQuickView() {
        var modal = document.getElementById('buyQuickView');
        if (modal) modal.hidden = true;
    }

    function getCompare() {
        return parseJson(localStorage.getItem(COMPARE_KEY) || '[]', []);
    }

    function setCompare(items) {
        localStorage.setItem(COMPARE_KEY, JSON.stringify(items));
    }

    function updateCompareUI() {
        var items = getCompare();
        var bar = document.getElementById('buyCompareBar');
        var count = document.getElementById('buyCompareCount');
        if (bar) bar.hidden = items.length === 0;
        if (count) count.textContent = items.length + ' of 3 selected';

        document.querySelectorAll('.js-compare-toggle').forEach(function (btn) {
            var card = btn.closest('.js-buy-product');
            if (!card) return;
            var active = items.some(function (x) { return x.id === card.dataset.id && x.kind === card.dataset.kind; });
            btn.classList.toggle('buy-compare-btn--active', active);
            btn.textContent = active ? 'Selected' : 'Compare';
        });
    }

    function toggleCompare(card) {
        var items = getCompare();
        var id = card.dataset.id;
        var kind = card.dataset.kind;
        var idx = items.findIndex(function (x) { return x.id === id && x.kind === kind; });

        if (idx >= 0) {
            items.splice(idx, 1);
        } else {
            if (items.length >= MAX_COMPARE) {
                if (window.showToast) window.showToast('You can compare up to 3 products.', 'warning');
                return;
            }
            items.push({
                id: id,
                kind: kind,
                name: card.dataset.name,
                price: card.dataset.price,
                category: card.dataset.category,
                rating: card.dataset.rating,
                image: card.dataset.image,
                url: card.dataset.url
            });
        }

        setCompare(items);
        updateCompareUI();
    }

    function buildCompareTable() {
        var table = document.getElementById('buyCompareTable');
        if (!table) return;
        var items = getCompare();
        if (items.length < 2) {
            table.innerHTML = '<tr><td>Please select at least 2 products.</td></tr>';
            return;
        }

        function row(label, key) {
            return '<tr><th>' + label + '</th>' + items.map(function (x) { return '<td>' + escapeHtml(x[key] || 'N/A') + '</td>'; }).join('') + '</tr>';
        }

        table.innerHTML = [
            '<tr><th>Product</th>' + items.map(function (x) { return '<th><img src="' + escapeHtml(x.image) + '" alt="' + escapeHtml(x.name) + '"><div>' + escapeHtml(x.name) + '</div></th>'; }).join('') + '</tr>',
            row('Type', 'kind'),
            row('Price', 'price'),
            row('Category', 'category'),
            row('Rating', 'rating'),
            '<tr><th>Action</th>' + items.map(function (x) { return '<td><a href="' + escapeHtml(x.url) + '">View Product</a></td>'; }).join('') + '</tr>'
        ].join('');
    }

    function openCompareModal() {
        buildCompareTable();
        var modal = document.getElementById('buyCompareModal');
        if (modal) modal.hidden = false;
    }

    function closeCompareModal() {
        var modal = document.getElementById('buyCompareModal');
        if (modal) modal.hidden = true;
    }

    function attachEvents() {
        var search = document.getElementById('buySearchInput');
        var type = document.getElementById('buyTypeSelect');
        var category = document.getElementById('buyCategorySelect');
        var sort = document.getElementById('buySortSelect');
        var reset = document.getElementById('buyFilterReset');

        [search, type, category, sort].forEach(function (el) {
            if (!el) return;
            var eventName = el.tagName === 'INPUT' ? 'input' : 'change';
            el.addEventListener(eventName, applyFilters);
        });

        if (reset) reset.addEventListener('click', resetFilters);

        document.querySelectorAll('.js-quick-view').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var card = btn.closest('.js-buy-product');
                trackViewedFromCard(card);
                openQuickView(card);
                renderRecentlyViewed();
                applyPersonalization();
            });
        });

        document.querySelectorAll('.js-buy-product a[href]').forEach(function (link) {
            link.addEventListener('click', function () {
                trackViewedFromCard(link.closest('.js-buy-product'));
            });
        });

        document.querySelectorAll('[data-qv-close]').forEach(function (el) {
            el.addEventListener('click', closeQuickView);
        });

        document.querySelectorAll('.js-compare-toggle').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var card = btn.closest('.js-buy-product');
                if (card) toggleCompare(card);
            });
        });

        var cmpOpen = document.getElementById('buyCompareNow');
        var cmpClear = document.getElementById('buyCompareClear');
        if (cmpOpen) cmpOpen.addEventListener('click', openCompareModal);
        if (cmpClear) {
            cmpClear.addEventListener('click', function () {
                setCompare([]);
                updateCompareUI();
                closeCompareModal();
            });
        }

        document.querySelectorAll('[data-compare-close]').forEach(function (el) {
            el.addEventListener('click', closeCompareModal);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        attachEvents();
        applyFilters();
        updateCompareUI();
        renderRecentlyViewed();
        applyPersonalization();
    });
})();
