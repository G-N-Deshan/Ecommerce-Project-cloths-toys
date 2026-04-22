/**
 * WHY: Tab switching without page reload
 * Makes UX smoother when filtering between All/Cloths/Toys
 */
(() => {
    const tabButtons = document.querySelectorAll('.wishlist-tab');
    const tabPanes = document.querySelectorAll('.wishlist-tab-pane');

    /**
     * Tab click handler
     * WHY: Switches between tabs without API calls or page reload
     */
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;

            // Remove active class from all tabs and panes
            tabButtons.forEach(btn => {
                btn.classList.remove('is-active');
                btn.setAttribute('aria-selected', 'false');
            });

            tabPanes.forEach(pane => {
                pane.classList.remove('is-active');
                pane.style.display = 'none';
            });

            // Add active class to clicked tab
            button.classList.add('is-active');
            button.setAttribute('aria-selected', 'true');

            // Show corresponding pane
            const activePane = document.getElementById(`tab-${tabName}`);
            if (activePane) {
                activePane.classList.add('is-active');
                activePane.style.display = 'block';
            }
        });
    });

    /**
     * Auto-dismiss alerts after 4 seconds
     * WHY: Clean up success/error messages automatically
     */
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.3s ease';
            setTimeout(() => {
                alert.remove();
            }, 300);
        }, 4000);
    });
})();