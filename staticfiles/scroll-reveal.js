/**
 * Scroll Reveal — Intersection Observer for all pages
 * Add data-reveal attribute to elements to animate on scroll.
 * 
 * Usage:
 *   <div data-reveal>             → slides up (default)
 *   <div data-reveal="left">      → slides from left
 *   <div data-reveal="right">     → slides from right
 *   <div data-reveal="scale">     → scales up
 *   <div data-reveal="fade">      → fades in
 *   <div data-reveal="flip">      → flips in
 *   <div data-reveal-stagger>     → staggers children
 */
(function () {
    'use strict';

    if (!('IntersectionObserver' in window)) return;

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    observer.unobserve(entry.target);
                }
            });
        },
        { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
    );

    function observeElements() {
        document.querySelectorAll('[data-reveal]:not(.revealed)').forEach((el) => {
            observer.observe(el);
        });
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', observeElements);
    } else {
        observeElements();
    }

    // Also observe dynamically added elements (for AJAX/spa)
    if ('MutationObserver' in window) {
        const mo = new MutationObserver((mutations) => {
            mutations.forEach((m) => {
                m.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) {
                        if (node.hasAttribute && node.hasAttribute('data-reveal')) {
                            observer.observe(node);
                        }
                        if (node.querySelectorAll) {
                            node.querySelectorAll('[data-reveal]:not(.revealed)').forEach((el) => {
                                observer.observe(el);
                            });
                        }
                    }
                });
            });
        });
        mo.observe(document.body || document.documentElement, { childList: true, subtree: true });
    }
})();
