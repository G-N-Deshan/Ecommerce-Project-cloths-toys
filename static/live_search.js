document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('navSearchInput');
    const resultsContainer = document.getElementById('liveSearchResults');
    let debounceTimer;

    if (searchInput && resultsContainer) {
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            const query = this.value.trim();

            if (query.length < 2) {
                resultsContainer.innerHTML = '';
                resultsContainer.classList.add('hidden');
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
                                    <a href="${item.url}" class="flex items-center gap-3 p-3 hover:bg-slate-50 transition-colors rounded-lg group">
                                        <div class="w-12 h-12 flex-shrink-0 rounded-lg overflow-hidden border border-slate-100">
                                            <img src="${item.image}" alt="${item.name}" class="w-full h-full object-cover">
                                        </div>
                                        <div class="flex-1 min-w-0">
                                            <div class="text-xs font-bold text-indigo-600 uppercase tracking-wider">${item.type}</div>
                                            <div class="text-sm font-semibold text-slate-800 truncate">${item.name}</div>
                                            <div class="text-sm font-bold text-slate-900">${item.price}</div>
                                        </div>
                                        <i class="bi bi-chevron-right text-slate-300 group-hover:text-indigo-500 transition-colors"></i>
                                    </a>
                                `;
                            });
                            html += '</div>';
                            resultsContainer.innerHTML = html;
                            resultsContainer.classList.remove('hidden');
                        } else {
                            resultsContainer.innerHTML = '<div class="p-4 text-center text-slate-400 text-sm">No products found</div>';
                            resultsContainer.classList.remove('hidden');
                        }
                    })
                    .catch(error => console.error('Live search error:', error));
            }, 300);
        });

        // Close results when clicking outside
        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !resultsContainer.contains(e.target)) {
                resultsContainer.classList.add('hidden');
            }
        });

        // Re-show results on focus if there's a query
        searchInput.addEventListener('focus', function() {
            if (this.value.trim().length >= 2 && resultsContainer.innerHTML !== '') {
                resultsContainer.classList.remove('hidden');
            }
        });
    }
});
