document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('navSearchInput');
    const resultsContainer = document.getElementById('liveSearchResults');
    const searchForm = document.getElementById('navSearchForm');
    let debounceTimer;

    const HISTORY_KEY = 'g11_search_history';
    const MAX_HISTORY = 5;

    function getHistory() {
        try {
            return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
        } catch (e) {
            return [];
        }
    }

    function saveToHistory(query) {
        if (!query || query.length < 2) return;
        let history = getHistory();
        history = [query, ...history.filter(h => h !== query)].slice(0, MAX_HISTORY);
        localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    }

    function clearHistory() {
        localStorage.removeItem(HISTORY_KEY);
        showDefaultResults();
    }

    function showDefaultResults() {
        fetch(`/live-search/?q=`)
            .then(response => response.json())
            .then(data => {
                const history = getHistory();
                let html = '<div class="p-4">';

                // Search History Section
                if (history.length > 0) {
                    html += `
                        <div class="mb-6">
                            <div class="flex items-center justify-between mb-3">
                                <h4 class="text-[11px] font-bold text-slate-400 uppercase tracking-widest">Recent Searches</h4>
                                <button id="clearSearchHistory" class="text-[10px] text-indigo-500 hover:text-indigo-600 font-semibold uppercase tracking-wider">Clear</button>
                            </div>
                            <div class="flex flex-wrap gap-2">
                                ${history.map(h => `
                                    <button class="history-item px-3 py-1.5 bg-slate-50 hover:bg-indigo-50 text-slate-600 hover:text-indigo-600 rounded-full text-xs font-medium transition-all border border-slate-100 hover:border-indigo-200">
                                        <i class="bi bi-clock-history mr-1 opacity-70"></i> ${h}
                                    </button>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }

                // Trending Section
                if (data.trending && data.trending.length > 0) {
                    html += `
                        <div class="mb-2">
                            <h4 class="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-3">Trending Now</h4>
                            <div class="grid grid-cols-1 gap-2">
                                ${data.trending.map(item => `
                                    <a href="${item.url}" class="flex items-center gap-3 p-2.5 hover:bg-slate-50 rounded-xl transition-all group border border-transparent hover:border-slate-100">
                                        <div class="w-8 h-8 flex items-center justify-center bg-indigo-50 text-indigo-500 rounded-lg group-hover:bg-indigo-500 group-hover:text-white transition-all">
                                            <i class="bi ${item.icon || 'bi-graph-up-arrow'}"></i>
                                        </div>
                                        <span class="text-sm font-medium text-slate-700">${item.name}</span>
                                    </a>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }

                html += '</div>';
                resultsContainer.innerHTML = html;
                resultsContainer.classList.remove('hidden');

                // Attach event listeners
                const clearBtn = document.getElementById('clearSearchHistory');
                if (clearBtn) clearBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    clearHistory();
                });

                document.querySelectorAll('.history-item').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.preventDefault();
                        searchInput.value = btn.textContent.trim();
                        searchInput.focus();
                        searchInput.dispatchEvent(new Event('input'));
                    });
                });
            });
    }

    if (searchInput && resultsContainer) {
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            const query = this.value.trim();

            if (query.length < 1) {
                showDefaultResults();
                return;
            }

            debounceTimer = setTimeout(() => {
                fetch(`/live-search/?q=${encodeURIComponent(query)}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.results && data.results.length > 0) {
                            let html = '<div class="p-2">';
                            
                            data.results.forEach(item => {
                                html += `
                                    <a href="${item.url}" class="flex items-center gap-4 p-3 hover:bg-slate-50 transition-all rounded-xl group border border-transparent hover:border-slate-100">
                                        <div class="w-14 h-14 flex-shrink-0 rounded-lg overflow-hidden border border-slate-100 shadow-sm">
                                            <img src="${item.image}" alt="${item.name}" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500">
                                        </div>
                                        <div class="flex-1 min-w-0">
                                            <div class="flex items-center gap-2 mb-0.5">
                                                <span class="text-[10px] font-bold text-indigo-600 uppercase tracking-widest bg-indigo-50 px-1.5 py-0.5 rounded">${item.type}</span>
                                                ${item.category ? `<span class="text-[10px] font-medium text-slate-400 uppercase tracking-widest">${item.category}</span>` : ''}
                                            </div>
                                            <div class="text-sm font-bold text-slate-800 truncate group-hover:text-indigo-600 transition-colors">${item.name}</div>
                                            <div class="text-sm font-black text-slate-900 mt-0.5">${item.price}</div>
                                        </div>
                                        <i class="bi bi-arrow-right text-slate-300 group-hover:text-indigo-500 transition-all transform group-hover:translate-x-1"></i>
                                    </a>
                                `;
                            });
                            html += '</div>';
                            resultsContainer.innerHTML = html;
                            resultsContainer.classList.remove('hidden');
                        } else {
                            resultsContainer.innerHTML = `
                                <div class="p-8 text-center">
                                    <div class="w-12 h-12 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-3">
                                        <i class="bi bi-search text-slate-300 text-xl"></i>
                                    </div>
                                    <p class="text-sm font-semibold text-slate-800">No products found</p>
                                    <p class="text-xs text-slate-400 mt-1">Try searching for something else</p>
                                </div>
                            `;
                            resultsContainer.classList.remove('hidden');
                        }
                    })
                    .catch(error => console.error('Live search error:', error));
            }, 300);
        });

        // Save history on form submit
        if (searchForm) {
            searchForm.addEventListener('submit', function() {
                saveToHistory(searchInput.value.trim());
            });
        }

        // Close results when clicking outside
        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !resultsContainer.contains(e.target)) {
                resultsContainer.classList.add('hidden');
            }
        });

        // Re-show results on focus
        searchInput.addEventListener('focus', function() {
            if (this.value.trim().length === 0) {
                showDefaultResults();
            } else {
                resultsContainer.classList.remove('hidden');
            }
        });
    }
});
