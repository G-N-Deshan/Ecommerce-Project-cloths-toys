document.addEventListener('DOMContentLoaded', function() {
    animateOnScroll();
    initTimelineAnimation();
});

/**
 * Animate elements when scrolling into view
 */
function animateOnScroll() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.value-card, .stat-item, .team-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
}

/**
 * Timeline dot animation
 */
function initTimelineAnimation() {
    const dots = document.querySelectorAll('.timeline-dot');
    
    dots.forEach((dot, index) => {
        dot.style.animation = `pulse 2s infinite`;
        dot.style.animationDelay = `${index * 0.2}s`;
    });
}

// Add CSS for pulse animation if not already present
if (!document.querySelector('#about-animations')) {
    const style = document.createElement('style');
    style.id = 'about-animations';
    style.textContent = `
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.6; }
        }
    `;
    document.head.appendChild(style);
}
