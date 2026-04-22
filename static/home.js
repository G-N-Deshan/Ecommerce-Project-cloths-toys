/* ═══════════════════════════════════════════
   G11 HOME PAGE — HOME.JS
   All interactive features for the redesigned home page
   ═══════════════════════════════════════════ */

(function () {
    'use strict';

    /* ── 1. Canvas Particle System (Hero) ── */
    function initParticles() {
        const canvas = document.getElementById('heroParticles');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let W, H, particles = [], raf;

        function resize() {
            W = canvas.width = canvas.offsetWidth;
            H = canvas.height = canvas.offsetHeight;
        }
        resize();
        window.addEventListener('resize', resize);

        function Particle() {
            this.x = Math.random() * W;
            this.y = Math.random() * H;
            this.r = Math.random() * 2 + 0.5;
            this.dx = (Math.random() - 0.5) * 0.4;
            this.dy = (Math.random() - 0.5) * 0.4;
            this.alpha = Math.random() * 0.5 + 0.2;
        }

        for (let i = 0; i < 60; i++) particles.push(new Particle());

        function draw() {
            ctx.clearRect(0, 0, W, H);
            particles.forEach(p => {
                p.x += p.dx;
                p.y += p.dy;
                if (p.x < 0 || p.x > W) p.dx *= -1;
                if (p.y < 0 || p.y > H) p.dy *= -1;
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(165,180,252,' + p.alpha + ')';
                ctx.fill();
            });

            // Draw connecting lines between nearby particles
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < 120) {
                        ctx.beginPath();
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.strokeStyle = 'rgba(165,180,252,' + (0.15 * (1 - dist / 120)) + ')';
                        ctx.stroke();
                    }
                }
            }
            raf = requestAnimationFrame(draw);
        }

        // Only animate when hero is visible
        const heroObs = new IntersectionObserver(entries => {
            entries.forEach(e => {
                if (e.isIntersecting) { if (!raf) draw(); }
                else { cancelAnimationFrame(raf); raf = null; }
            });
        }, { threshold: 0.1 });
        heroObs.observe(canvas.parentElement);
    }

    /* ── 2. Hero Background Parallax ── */
    function initHeroParallax() {
        const bg = document.getElementById('heroBg');
        if (!bg) return;
        let ticking = false;
        window.addEventListener('scroll', () => {
            if (!ticking) {
                requestAnimationFrame(() => {
                    const y = window.scrollY;
                    if (y < window.innerHeight) {
                        bg.style.transform = 'scale(1.1) translateY(' + (y * 0.25) + 'px)';
                    }
                    ticking = false;
                });
                ticking = true;
            }
        });
    }

    /* ── 3. 3D Tilt Effect on Cards ── */
    function initTiltCards() {
        document.querySelectorAll('.tilt-card').forEach(card => {
            const inner = card.querySelector('.card-inner');
            if (!inner) return;

            card.addEventListener('mousemove', e => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                const cx = rect.width / 2;
                const cy = rect.height / 2;
                const rotateX = ((y - cy) / cy) * -6;
                const rotateY = ((x - cx) / cx) * 6;
                inner.style.transform = 'rotateX(' + rotateX + 'deg) rotateY(' + rotateY + 'deg)';
                inner.style.boxShadow = '0 20px 50px rgba(0,0,0,0.15)';
            });

            card.addEventListener('mouseleave', () => {
                inner.style.transform = 'rotateX(0) rotateY(0)';
                inner.style.boxShadow = '';
            });
        });
    }

    /* ── 4. Animated Number Counters ── */
    function initCounters() {
        const counters = document.querySelectorAll('.counter[data-target]');
        if (!counters.length) return;

        const obs = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                const el = entry.target;
                obs.unobserve(el);

                const target = parseFloat(el.dataset.target);
                const suffix = el.dataset.suffix || '';
                const decimals = parseInt(el.dataset.decimals) || 0;
                const duration = 2000;
                const start = performance.now();

                function step(now) {
                    const elapsed = now - start;
                    const progress = Math.min(elapsed / duration, 1);
                    // Ease-out cubic
                    const ease = 1 - Math.pow(1 - progress, 3);
                    const current = target * ease;
                    el.textContent = current.toFixed(decimals) + (progress >= 1 ? suffix : '');
                    if (progress < 1) requestAnimationFrame(step);
                }
                requestAnimationFrame(step);
            });
        }, { threshold: 0.5 });

        counters.forEach(c => obs.observe(c));
    }

    /* ── 5. Magnetic Button Effect ── */
    function initMagneticButtons() {
        document.querySelectorAll('.mag-btn').forEach(btn => {
            btn.addEventListener('mousemove', e => {
                const rect = btn.getBoundingClientRect();
                const x = e.clientX - rect.left - rect.width / 2;
                const y = e.clientY - rect.top - rect.height / 2;
                btn.style.transform = 'translate(' + (x * 0.15) + 'px,' + (y * 0.15) + 'px)';
            });
            btn.addEventListener('mouseleave', () => {
                btn.style.transform = '';
            });
        });
    }

    /* ── 6. Scroll Reveal (IntersectionObserver) ── */
    function initScrollReveal() {
        const revealEls = document.querySelectorAll('.reveal, .reveal-stagger');
        if (!revealEls.length) return;

        // Immediately reveal anything already in or near the viewport
        function revealIfVisible(el) {
            const rect = el.getBoundingClientRect();
            if (rect.top < window.innerHeight + 50 && rect.bottom > -50) {
                el.classList.add('visible');
                return true;
            }
            return false;
        }

        const pending = [];
        revealEls.forEach(el => {
            if (!revealIfVisible(el)) pending.push(el);
        });

        // Observe remaining elements
        if (pending.length) {
            const obs = new IntersectionObserver(entries => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');
                        obs.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.01, rootMargin: '0px 0px 150px 0px' });

            pending.forEach(el => obs.observe(el));
        }

        // Also re-check on scroll for any stragglers
        let scrollTimer;
        function onScroll() {
            clearTimeout(scrollTimer);
            scrollTimer = setTimeout(() => {
                document.querySelectorAll('.reveal:not(.visible), .reveal-stagger:not(.visible)').forEach(revealIfVisible);
            }, 100);
        }
        window.addEventListener('scroll', onScroll, { passive: true });

        // Final safety net: reveal everything after 3 seconds
        setTimeout(() => {
            document.querySelectorAll('.reveal:not(.visible), .reveal-stagger:not(.visible)').forEach(el => {
                el.classList.add('visible');
            });
            window.removeEventListener('scroll', onScroll);
        }, 3000);
    }

    /* ── 7. Feature Card Click Navigation ── */
    function initFeatureNav() {
        document.querySelectorAll('#features .tilt-card').forEach(card => {
            const inner = card.querySelector('.card-inner');
            if (!inner) return;
            const text = (inner.querySelector('h3')?.textContent || '').toLowerCase();
            inner.style.cursor = 'pointer';
            inner.addEventListener('click', e => {
                if (e.target.closest('a, button')) return;
                if (text.includes('cloth') || text.includes('fashion'))
                    window.location.href = '/cloths/';
                else if (text.includes('toy'))
                    window.location.href = '/toys/';
                else
                    window.location.href = '/buy/';
            });
        });
    }

    /* ── 8. Auto-dismiss messages ── */
    function initMessages() {
        const box = document.getElementById('msgBox');
        if (box) setTimeout(() => { box.style.display = 'none'; }, 5000);
    }

    /* ── Boot ── */
    document.addEventListener('DOMContentLoaded', () => {
        initParticles();
        initHeroParallax();
        initTiltCards();
        initCounters();
        initMagneticButtons();
        initScrollReveal();
        initFeatureNav();
        initMessages();
    });
})();
//             } catch (err) {
//                 showToast('Could not add to cart');
//             }
//         });
//     });
// }