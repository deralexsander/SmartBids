// ==========================================================================
// CONTROLES VISUALES DE LICITACIONES
// ==========================================================================
export function toggleTextoLicitacion(idElemento, boton) {
    const contenedor = document.getElementById(idElemento);
    if (contenedor.classList.contains('licitacion-text-clamp')) {
        contenedor.classList.remove('licitacion-text-clamp');
        contenedor.classList.add('licitacion-text-expanded');
        boton.innerHTML = 'Ocultar <i class="fa-solid fa-chevron-up" style="font-size: 0.65rem;"></i>';
    } else {
        contenedor.classList.remove('licitacion-text-expanded');
        contenedor.classList.add('licitacion-text-clamp');
        boton.innerHTML = 'Ver <i class="fa-solid fa-chevron-down" style="font-size: 0.65rem;"></i>';
    }
}