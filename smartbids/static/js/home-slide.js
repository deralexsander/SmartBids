/**
 * SmartBids - Animación de Deslizamiento y Scroll Suave para la Página de Inicio
 * Controla el IntersectionObserver para el reveal de secciones y el scrollspy del navbar.
 */

document.addEventListener('DOMContentLoaded', () => {
    initSlideReveal();
    initSmoothAnchorScroll();
    initScrollSpy();
});

/**
 * Inicializa el IntersectionObserver para revelar y deslizar elementos
 * a medida que entran al área visible de la pantalla.
 */
function initSlideReveal() {
    const targets = document.querySelectorAll('.home-slide-section, .feature-row');
    if (!targets.length) return;

    if (!('IntersectionObserver' in window)) {
        // Fallback inmediato si el navegador no soporta IntersectionObserver
        targets.forEach(el => el.classList.add('is-visible'));
        return;
    }

    const observerOptions = {
        root: null,
        rootMargin: '0px 0px -40px 0px',
        threshold: 0.12
    };

    const revealObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                // Dejar de observar para mantener visible y optimizar el rendimiento
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    targets.forEach(el => revealObserver.observe(el));
}

/**
 * Maneja el desplazamiento suave (smooth scroll) compensando la altura
 * del header de navegación fijo para que los títulos no queden ocultos.
 */
function initSmoothAnchorScroll() {
    const header = document.querySelector('header');
    const getHeaderOffset = () => (header ? header.getBoundingClientRect().height + 15 : 85);

    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (!targetId || targetId === '#') return;

            const targetElement = document.querySelector(targetId);
            if (!targetElement) return;

            e.preventDefault();

            const headerOffset = getHeaderOffset();
            const elementPosition = targetElement.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

            window.scrollTo({
                top: Math.max(0, offsetPosition),
                behavior: 'smooth'
            });

            // Actualizar el historial/URL sin provocar un salto brusco
            if (window.history && window.history.pushState) {
                window.history.pushState(null, '', targetId);
            }
        });
    });
}

/**
 * ScrollSpy: Detecta la sección activa según la posición del scroll
 * y actualiza la clase activa en el menú de navegación superior.
 */
function initScrollSpy() {
    const sectionIds = ['propuesta', 'funcionalidades', 'inteligencia', 'beneficios', 'contacto'];
    const sections = sectionIds
        .map(id => document.getElementById(id))
        .filter(el => el !== null);

    const navLinks = Array.from(document.querySelectorAll('header nav a[href^="#"]'));

    if (!sections.length || !navLinks.length) return;

    const header = document.querySelector('header');
    const getHeaderHeight = () => (header ? header.getBoundingClientRect().height : 80);

    const updateActiveNav = () => {
        const scrollPosition = window.pageYOffset + getHeaderHeight() + 60;

        let activeId = '';

        for (const section of sections) {
            const top = section.offsetTop;
            const height = section.offsetHeight;
            if (scrollPosition >= top && scrollPosition < top + height) {
                activeId = section.getAttribute('id');
                break;
            }
        }

        // Si el usuario está al final de la página (ej. en contacto)
        if (window.innerHeight + window.pageYOffset >= document.documentElement.scrollHeight - 60) {
            const lastSection = sections[sections.length - 1];
            if (lastSection) {
                activeId = lastSection.getAttribute('id');
            }
        }

        navLinks.forEach(link => {
            const target = link.getAttribute('href')?.replace('#', '');
            const parentLi = link.closest('li');

            if (target && target === activeId) {
                link.classList.add('active');
                if (parentLi) parentLi.classList.add('active');
            } else {
                link.classList.remove('active');
                if (parentLi) parentLi.classList.remove('active');
            }
        });
    };

    let ticking = false;
    window.addEventListener('scroll', () => {
        if (!ticking) {
            window.requestAnimationFrame(() => {
                updateActiveNav();
                ticking = false;
            });
            ticking = true;
        }
    }, { passive: true });

    // Ejecutar inmediatamente
    updateActiveNav();
}
