/**
 * SmartBids - Animaciones Interactivas, Deslizamiento y Scroll Suave
 * Controla:
 * 1. IntersectionObserver para el reveal de secciones y scrollspy del navbar.
 * 2. Botones condicionales (autenticado -> módulo, no autenticado -> registro).
 * 3. Animaciones sutiles interactivas activadas al hacer scroll (ejecutadas una sola vez por carga).
 */

document.addEventListener('DOMContentLoaded', () => {
    initSmoothAnchorScroll();
    initScrollSpy();
    initConditionalAuthButtons();

    // Las animaciones inician exactamente 3 segundos después de desaparecer la barra de carga
    ejecutarTrasCargaYTresSegundos(() => {
        initSlideReveal();
        initInteractiveMockupAnimations();
    });
});

/**
 * Aguarda a que la barra de carga (page-loader) desaparezca por completo y espera
 * exactamente 3 segundos adicionales antes de dar inicio a las animaciones de la landing page.
 */
function ejecutarTrasCargaYTresSegundos(callback) {
    let triggered = false;

    const iniciarConRetardo = () => {
        if (triggered) return;
        triggered = true;
        setTimeout(() => {
            callback();
        }, 3000); // 3 segundos exactos después de desaparecer la barra de carga
    };

    const loader = document.getElementById('page-loader');
    const estaCargando = document.documentElement.classList.contains('loading') || (loader && loader.style.display !== 'none');

    // Si ya desapareció el loader o nunca estuvo presente
    if (window.smartbidsLoaderHidden || (!loader && !estaCargando)) {
        iniciarConRetardo();
        return;
    }

    // Escuchar el evento disparado por hidePageLoader
    window.addEventListener('page-loader-hidden', iniciarConRetardo, { once: true });

    // Observador de mutaciones como salvaguarda ante remoción directa del DOM
    const observer = new MutationObserver(() => {
        const stillInDom = document.getElementById('page-loader');
        const hasLoading = document.documentElement.classList.contains('loading');
        if (!stillInDom && !hasLoading) {
            observer.disconnect();
            iniciarConRetardo();
        }
    });

    observer.observe(document.documentElement, { attributes: true, childList: true, subtree: true });

    // Salvaguarda final: si por alguna razón no se emite el evento en 2.5s, arrancar el contador
    setTimeout(() => {
        observer.disconnect();
        iniciarConRetardo();
    }, 2500);
}

/**
 * Gestiona los botones de la landing page para que dirijan a su módulo respectivo
 * si el usuario tiene sesión activa, o a la página de registro si no está autenticado.
 */
function initConditionalAuthButtons() {
    const buttons = document.querySelectorAll('[data-auth-href][data-guest-href]');
    if (!buttons.length) return;

    const checkIsAuth = () => {
        const hasUidStorage = Boolean(
            (window.localStorage && localStorage.getItem('smartbids_uid')) ||
            (window.sessionStorage && sessionStorage.getItem('smartbids_uid'))
        );
        const hasUidCookie = Boolean(
            document.cookie && (document.cookie.includes('sb_firebase_uid=') || document.cookie.includes('firebase_uid='))
        );
        const isLoginBtnHidden = document.getElementById('btn-login')?.style.display === 'none';
        const isProfileBtnVisible = document.getElementById('btn-profile')?.style.display === 'inline-flex';

        return hasUidStorage || hasUidCookie || isLoginBtnHidden || isProfileBtnVisible;
    };

    const syncButtons = () => {
        const isAuth = checkIsAuth();
        buttons.forEach(btn => {
            const targetHref = isAuth ? btn.getAttribute('data-auth-href') : btn.getAttribute('data-guest-href');
            if (targetHref) {
                btn.setAttribute('href', targetHref);
            }
        });
    };

    // Sincronizar inmediatamente al cargar el DOM
    syncButtons();

    // Sincronizar al hacer clic como salvaguarda
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            const isAuth = checkIsAuth();
            const targetHref = isAuth ? btn.getAttribute('data-auth-href') : btn.getAttribute('data-guest-href');
            if (targetHref) {
                btn.setAttribute('href', targetHref);
            }
        });
    });
}

/**
 * Inicializa las micro-animaciones interactivas sutiles que demuestran el funcionamiento
 * real de la plataforma (simulación de puntero, tipeo automático, contadores y barras).
 * Se activan por IntersectionObserver y se ejecutan SOLO UNA VEZ a menos que se recargue la página.
 */
function initInteractiveMockupAnimations() {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // 1. ANIMACIÓN DEL PUNTERO EN LA TARJETA DEL HERO
    const heroCard = document.querySelector('.home__hero-card');
    const heroBtn = document.getElementById('hero-follow-mock-btn');
    const heroCursor = document.getElementById('hero-simulated-cursor');
    const heroIcon = document.getElementById('hero-follow-icon');
    const heroText = document.getElementById('hero-follow-text');

    if (heroCard && heroBtn && heroCursor) {
        if (prefersReducedMotion) {
            heroBtn.classList.add('is-followed');
            if (heroIcon) heroIcon.className = 'fa-solid fa-bookmark';
            if (heroText) heroText.textContent = 'Siguiendo';
        } else {
            const heroObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting && !heroCard.dataset.animatedHero) {
                        heroCard.dataset.animatedHero = 'true';
                        observer.unobserve(heroCard);

                        // Inicia tras una pausa elegante para que el usuario aprecie el Hero
                        setTimeout(() => {
                            const cardRect = heroCard.getBoundingClientRect();
                            const btnRect = heroBtn.getBoundingClientRect();
                            if (!cardRect.width || !btnRect.width) return;

                            // Posición de inicio del cursor (esquina inferior derecha)
                            const startX = cardRect.width - 50;
                            const startY = cardRect.height - 45;
                            heroCursor.style.left = `${startX}px`;
                            heroCursor.style.top = `${startY}px`;
                            heroCursor.style.opacity = '1';

                            // Coordenadas de destino (centro del botón)
                            const targetX = (btnRect.left - cardRect.left) + (btnRect.width / 2) - 4;
                            const targetY = (btnRect.top - cardRect.top) + (btnRect.height / 2) - 4;

                            setTimeout(() => {
                                // Desplazamiento pausado y visible del puntero (1.6s)
                                heroCursor.style.left = `${targetX}px`;
                                heroCursor.style.top = `${targetY}px`;

                                // Simulación del micro-clic al completar el recorrido
                                setTimeout(() => {
                                    heroCursor.style.transform = 'scale(0.85)';
                                    heroBtn.classList.add('is-pressed');

                                    setTimeout(() => {
                                        heroCursor.style.transform = 'scale(1)';
                                        heroBtn.classList.remove('is-pressed');
                                        heroBtn.classList.add('is-followed');
                                        if (heroIcon) heroIcon.className = 'fa-solid fa-bookmark';
                                        if (heroText) heroText.textContent = 'Siguiendo';

                                        // Permite apreciar la bandera marcada antes de desvanecer el cursor
                                        setTimeout(() => {
                                            heroCursor.style.opacity = '0';
                                        }, 850);
                                    }, 260);
                                }, 1650);
                            }, 120);
                        }, 600);
                    }
                });
            }, { threshold: 0.25 });

            heroObserver.observe(heroCard);
        }
    }

    // 2. ANIMACIÓN DE TIPEO Y REVELADO EN EL EXPLORADOR TERRITORIAL
    const exploradorBar = document.querySelector('.home__explorador-bar');
    const typingTarget = document.getElementById('explorador-typing-target');
    const typingCursor = document.getElementById('explorador-typing-cursor');
    const searchBtn = document.getElementById('explorador-mock-search-btn');
    const resultCard = document.getElementById('explorador-mock-result-card');

    if (exploradorBar && typingTarget && resultCard) {
        const fullText = "Servicios de Mantención Cloud";

        if (prefersReducedMotion) {
            typingTarget.textContent = fullText;
            if (typingCursor) typingCursor.style.display = 'none';
            resultCard.classList.add('is-visible-card');
        } else {
            const expObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting && !exploradorBar.dataset.animatedTyping) {
                        exploradorBar.dataset.animatedTyping = 'true';
                        observer.unobserve(exploradorBar);

                        let charIndex = 0;
                        typingTarget.textContent = '';

                        // Efecto de tipeo cadencioso y natural (75ms por letra)
                        const typeInterval = setInterval(() => {
                            if (charIndex < fullText.length) {
                                typingTarget.textContent += fullText.charAt(charIndex);
                                charIndex++;
                            } else {
                                clearInterval(typeInterval);
                                if (typingCursor) typingCursor.style.display = 'none';

                                // Pausa para simular la decisión antes del clic
                                setTimeout(() => {
                                    if (searchBtn) searchBtn.classList.add('is-active');

                                    setTimeout(() => {
                                        if (searchBtn) searchBtn.classList.remove('is-active');

                                        // Revelación suave de 0 a 100 de la tarjeta de resultado
                                        resultCard.classList.add('is-visible-card');
                                    }, 320);
                                }, 450);
                            }
                        }, 75);
                    }
                });
            }, { threshold: 0.3 });

            expObserver.observe(exploradorBar);
        }
    }

    // 3. ANIMACIÓN DE CONTADORES EN RESUMEN DIARIO
    const resumenKpiGrid = document.getElementById('resumen-kpi-grid');
    const resumenMockList = document.getElementById('resumen-mock-list');
    const countElements = document.querySelectorAll('[data-count-target]');

    if (resumenKpiGrid && countElements.length) {
        if (prefersReducedMotion) {
            countElements.forEach(el => el.textContent = el.getAttribute('data-count-target'));
            if (resumenMockList) resumenMockList.classList.add('is-visible-items');
        } else {
            const kpiObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting && !resumenKpiGrid.dataset.animatedCounters) {
                        resumenKpiGrid.dataset.animatedCounters = 'true';
                        observer.unobserve(resumenKpiGrid);

                        // Animar contadores pausadamente de 0 a valor objetivo (1.8s)
                        countElements.forEach(el => {
                            const target = parseInt(el.getAttribute('data-count-target'), 10) || 0;
                            const duration = 1800;
                            const startTime = performance.now();

                            const updateCount = (now) => {
                                const elapsed = now - startTime;
                                const progress = Math.min(elapsed / duration, 1);
                                // Easing suave (easeOutCubic)
                                const easeProgress = 1 - Math.pow(1 - progress, 3);
                                const current = Math.floor(easeProgress * target);

                                el.textContent = current;

                                if (progress < 1) {
                                    requestAnimationFrame(updateCount);
                                } else {
                                    el.textContent = target;
                                }
                            };

                            requestAnimationFrame(updateCount);
                        });

                        // Revelado escalonado pausado de los ítems de licitación
                        if (resumenMockList) {
                            setTimeout(() => {
                                resumenMockList.classList.add('is-visible-items');
                            }, 400);
                        }
                    }
                });
            }, { threshold: 0.3 });

            kpiObserver.observe(resumenKpiGrid);
        }
    }

    // 4. ANIMACIÓN DE CRECIMIENTO DE BARRAS EN DATA WAREHOUSE
    const chartContainer = document.getElementById('dw-mock-chart');
    if (chartContainer) {
        const bars = chartContainer.querySelectorAll('.home__chart-bar[data-target-height]');
        if (prefersReducedMotion) {
            bars.forEach(b => b.style.height = b.getAttribute('data-target-height'));
        } else {
            const chartObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting && !chartContainer.dataset.animatedChart) {
                        chartContainer.dataset.animatedChart = 'true';
                        observer.unobserve(chartContainer);

                        chartContainer.classList.add('is-animated-chart');
                        bars.forEach(bar => {
                            const targetHeight = bar.getAttribute('data-target-height');
                            if (targetHeight) {
                                bar.style.height = targetHeight;
                            }
                        });
                    }
                });
            }, { threshold: 0.35 });

            chartObserver.observe(chartContainer);
        }
    }

    // 5. ANIMACIÓN DEL CRONOGRAMA DE PROCESO (FICHA TÉCNICA)
    const timelineList = document.getElementById('ficha-mock-timeline');
    const qaCard = document.getElementById('ficha-mock-qa');

    if (timelineList) {
        if (prefersReducedMotion) {
            timelineList.classList.add('is-animated-timeline');
            if (qaCard) qaCard.classList.add('is-visible-qa');
        } else {
            const timelineObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting && !timelineList.dataset.animatedTimeline) {
                        timelineList.dataset.animatedTimeline = 'true';
                        observer.unobserve(timelineList);

                        // Revelación de hitos del cronograma
                        timelineList.classList.add('is-animated-timeline');

                        if (qaCard) {
                            setTimeout(() => {
                                qaCard.classList.add('is-visible-qa');
                            }, 1600);
                        }
                    }
                });
            }, { threshold: 0.25 });

            timelineObserver.observe(timelineList);
        }
    }
}

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

    // Si la página se abre con un ancla hash (ej: /informacion/#terminos)
    if (window.location.hash) {
        try {
            const targetEl = document.querySelector(window.location.hash);
            if (targetEl) {
                targetEl.classList.add('is-visible');
                const parentSection = targetEl.closest('.home-slide-section');
                if (parentSection) parentSection.classList.add('is-visible');
            }
        } catch (_) {}
    }
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
    const navLinks = Array.from(document.querySelectorAll('header nav a[href^="#"]'));
    if (!navLinks.length) return;

    const sections = navLinks
        .map(link => {
            const rawHref = link.getAttribute('href') || '';
            const id = rawHref.replace('#', '').trim();
            return id ? document.getElementById(id) : null;
        })
        .filter(el => el !== null);

    if (!sections.length) return;

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

        // Si el usuario está al final de la página (ej. en contacto o garantías)
        if (window.innerHeight + window.pageYOffset >= document.documentElement.scrollHeight - 60) {
            const lastSection = sections[sections.length - 1];
            if (lastSection) {
                activeId = lastSection.getAttribute('id');
            }
        }

        navLinks.forEach(link => {
            const target = link.getAttribute('href')?.replace('#', '').trim();
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
