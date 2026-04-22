document.addEventListener('DOMContentLoaded', function() {
    initFAQ();
    setupFormValidation();
});

/**
 * FAQ accordion toggle
 */
function initFAQ() {
    const faqItems = document.querySelectorAll('.faq-item');
    
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        
        if (question) {
            question.addEventListener('click', () => {
                const isActive = item.classList.contains('active');
                
                // Close all other items
                faqItems.forEach(other => {
                    if (other !== item) {
                        other.classList.remove('active');
                    }
                });
                
                // Toggle current item
                item.classList.toggle('active');
            });
        }
    });
}

/**
 * Contact form validation
 */
function setupFormValidation() {
    const form = document.querySelector('.contact-form');
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        const email = form.querySelector('[name="email"]');
        const message = form.querySelector('[name="message"]');
        
        if (email && !isValidEmail(email.value)) {
            e.preventDefault();
            alert('Please enter a valid email address');
            return false;
        }
        
        if (message && message.value.trim().length < 10) {
            e.preventDefault();
            alert('Message must be at least 10 characters long');
            return false;
        }
    });
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}
