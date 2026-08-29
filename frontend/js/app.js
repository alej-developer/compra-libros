/**
 * Logica principal de la interfaz de usuario para Mi Rincon de Libros.
 * Controla eventos de navegacion, busquedas, filtros y renderizado
 * en cuadricula o lista. Muestra el estado del libro (Nuevo / De segunda
 * mano) y enlaza directamente a la pagina de compra sin rastreo alguno.
 */

document.addEventListener('DOMContentLoaded', () => {
    // -- Elementos del DOM --
    const campoBusqueda = document.getElementById('campo-busqueda');
    const botonBuscar = document.getElementById('boton-buscar');
    const toggleFiltros = document.getElementById('toggle-filtros');
    const panelFiltros = document.getElementById('panel-filtros');

    // Filtros
    const filtroCategoria = document.getElementById('filtro-categoria');
    const filtroPrecioMin = document.getElementById('filtro-precio-min');
    const filtroPrecioMax = document.getElementById('filtro-precio-max');
    const filtroIdioma = document.getElementById('filtro-idioma');
    const filtroOrden = document.getElementById('filtro-orden');

    // Secciones y contenedores
    const seccionBienvenida = document.getElementById('bienvenida');
    const contenedorResultados = document.getElementById('contenedor-resultados');
    const seccionSinResultados = document.getElementById('sin-resultados');
    const seccionError = document.getElementById('mensaje-error');
    const textoError = document.getElementById('texto-error');
    const botonReintentar = document.getElementById('boton-reintentar');
    const estadoCarga = document.getElementById('estado-carga');
    const controlesVista = document.getElementById('controles-vista');
    const infoResultados = document.getElementById('info-resultados');
    const infoFuentes = document.getElementById('info-fuentes');
    const pieFuentes = document.getElementById('pie-fuentes');

    // Botones de navegación
    const botonesNav = document.querySelectorAll('.boton-nav');
    const vistaCuadricula = document.getElementById('vista-cuadricula');
    const vistaLista = document.getElementById('vista-lista');
    const sugerencias = document.querySelectorAll('.etiqueta-sugerencia');

    // -- Estado de la aplicación --
    let seccionActual = 'buscar'; // 'buscar', 'ofertas', 'independientes'
    let vistaActual = 'cuadricula'; // 'cuadricula', 'lista'
    let ultimaAccion = null;

    // -- Inicialización --
    cargarFuentes();
    configurarEventos();

    /**
     * Configura todos los escuchadores de eventos.
     */
    function configurarEventos() {
        // Alternar panel de filtros
        toggleFiltros.addEventListener('click', () => {
            panelFiltros.classList.toggle('filtros__panel--visible');
        });

        // Búsqueda por botón o Enter
        botonBuscar.addEventListener('click', () => ejecutarBusquedaSegunSeccion());
        campoBusqueda.addEventListener('keydown', (evento) => {
            if (evento.key === 'Enter') {
                ejecutarBusquedaSegunSeccion();
            }
        });

        // Navegación superior
        botonesNav.forEach(boton => {
            boton.addEventListener('click', () => {
                botonesNav.forEach(b => b.classList.remove('boton-nav--activo'));
                boton.classList.add('boton-nav--activo');
                seccionActual = boton.dataset.seccion;
                ajustarInterfazPorSeccion();
            });
        });

        // Cambio de vista (cuadrícula / lista)
        vistaCuadricula.addEventListener('click', () => cambiarVista('cuadricula'));
        vistaLista.addEventListener('click', () => cambiarVista('lista'));

        // Sugerencias de búsqueda inicial
        sugerencias.forEach(sugerencia => {
            sugerencia.addEventListener('click', () => {
                campoBusqueda.value = sugerencia.dataset.busqueda;
                ejecutarBusquedaSegunSeccion();
            });
        });

        // Botón de reintentar
        botonReintentar.addEventListener('click', () => {
            if (ultimaAccion) {
                ultimaAccion();
            } else {
                ejecutarBusquedaSegunSeccion();
            }
        });
    }

    /**
     * Adapta la interfaz según la sección activa.
     */
    function ajustarInterfazPorSeccion() {
        if (seccionActual === 'ofertas') {
            campoBusqueda.placeholder = 'Buscar en ofertas (opcional)...';
            ejecutarCargaOfertas();
        } else if (seccionActual === 'independientes') {
            campoBusqueda.placeholder = 'Buscar autores independientes y emergentes...';
            if (campoBusqueda.value.trim()) {
                ejecutarBusquedaIndependientes();
            } else {
                campoBusqueda.focus();
            }
        } else {
            campoBusqueda.placeholder = 'Título, autor o tema...';
        }
    }

    /**
     * Ejecuta la búsqueda correspondiente según la sección actual.
     */
    function ejecutarBusquedaSegunSeccion() {
        if (seccionActual === 'ofertas') {
            ejecutarCargaOfertas();
        } else if (seccionActual === 'independientes') {
            ejecutarBusquedaIndependientes();
        } else {
            ejecutarBusquedaGeneral();
        }
    }

    /**
     * Construye el objeto de filtro a partir de los campos del formulario.
     */
    function construirFiltro() {
        const termino = campoBusqueda.value.trim() || 'literatura';
        const categoria = filtroCategoria.value || null;
        const precioMin = filtroPrecioMin.value ? parseFloat(filtroPrecioMin.value) : null;
        const precioMax = filtroPrecioMax.value ? parseFloat(filtroPrecioMax.value) : null;
        const idioma = filtroIdioma.value || null;
        const orden = filtroOrden.value || 'relevancia';

        return {
            termino_busqueda: termino,
            categoria: categoria,
            precio_minimo: precioMin,
            precio_maximo: precioMax,
            idioma: idioma,
            solo_disponibles: true,
            orden: orden,
            pagina: 1,
            resultados_por_pagina: 40
        };
    }

    /**
     * Carga las fuentes disponibles en el pie de página.
     */
    async function cargarFuentes() {
        try {
            const respuesta = await window.clienteApi.obtenerFuentes();
            if (respuesta && respuesta.fuentes) {
                renderizarFuentesPie(respuesta.fuentes);
            }
        } catch (error) {
            console.warn('No se pudieron obtener las fuentes del backend:', error);
        }
    }

    /**
     * Renderiza las etiquetas de fuentes en el pie de página.
     */
    function renderizarFuentesPie(fuentes) {
        pieFuentes.innerHTML = '';
        fuentes.forEach(fuente => {
            const etiqueta = document.createElement('span');
            etiqueta.className = `pie__fuente pie__fuente--${fuente.tipo}`;
            etiqueta.textContent = `${fuente.nombre} (${fuente.pais})`;
            pieFuentes.appendChild(etiqueta);
        });
    }

    /**
     * Ejecuta una búsqueda general.
     */
    async function ejecutarBusquedaGeneral() {
        const filtro = construirFiltro();
        mostrarCarga();
        ultimaAccion = () => ejecutarBusquedaGeneral();

        try {
            const resultado = await window.clienteApi.buscarLibros(filtro);
            procesarResultados(resultado);
        } catch (error) {
            mostrarError('No fue posible realizar la búsqueda en este momento.');
        }
    }

    /**
     * Ejecuta la carga de ofertas.
     */
    async function ejecutarCargaOfertas() {
        mostrarCarga();
        ultimaAccion = () => ejecutarCargaOfertas();

        const precioMaximo = filtroPrecioMax.value ? parseFloat(filtroPrecioMax.value) : 10.0;

        try {
            const resultado = await window.clienteApi.obtenerOfertas(precioMaximo, 50);
            procesarResultados(resultado, 'ofertas');
        } catch (error) {
            mostrarError('No fue posible cargar las ofertas actuales.');
        }
    }

    /**
     * Ejecuta la búsqueda priorizando autores independientes.
     */
    async function ejecutarBusquedaIndependientes() {
        const filtro = construirFiltro();
        mostrarCarga();
        ultimaAccion = () => ejecutarBusquedaIndependientes();

        try {
            const resultado = await window.clienteApi.buscarAutoresIndependientes(filtro, 45.0);
            procesarResultados(resultado, 'independientes');
        } catch (error) {
            mostrarError('No fue posible filtrar autores independientes.');
        }
    }

    /**
     * Procesa y muestra los resultados devueltos por el backend.
     */
    function procesarResultados(resultado, modo = 'general') {
        ocultarCarga();

        if (!resultado || !resultado.libros || resultado.libros.length === 0) {
            mostrarSinResultados();
            return;
        }

        mostrarResultados();
        actualizarInfoResultados(resultado, modo);
        renderizarLibros(resultado.libros);
    }

    /**
     * Actualiza la barra informativa de resultados y fuentes.
     */
    function actualizarInfoResultados(resultado, modo) {
        const cantidad = resultado.total_encontrados;
        let texto = `${cantidad} libro${cantidad === 1 ? '' : 's'} encontrado${cantidad === 1 ? '' : 's'}`;

        if (modo === 'ofertas') {
            texto += ' en sección de ofertas';
        } else if (modo === 'independientes') {
            texto += ' de sellos y autores independientes';
        }

        infoResultados.textContent = texto;

        if (resultado.fuentes_consultadas && resultado.fuentes_consultadas.length > 0) {
            infoFuentes.textContent = `Fuentes: ${resultado.fuentes_consultadas.join(', ')}`;
        } else {
            infoFuentes.textContent = '';
        }
    }

    /**
     * Renderiza las tarjetas de libros en el contenedor.
     */
    function renderizarLibros(libros) {
        contenedorResultados.innerHTML = '';

        libros.forEach(item => {
            const libro = item.libro;
            const ediciones = item.ediciones || [];
            const esIndependiente = item.es_autor_independiente || (item.puntuacion_independencia >= 50.0);
            const puntuacionIndie = item.puntuacion_independencia || 0;

            const tarjeta = document.createElement('article');
            tarjeta.className = 'tarjeta-libro';

            // Determinar formato predominante o tipo de edición
            const formatoTexto = formatearTipoEdicion(libro, ediciones);
            const esDigital = formatoTexto.toLowerCase().includes('kindle') ||
                              formatoTexto.toLowerCase().includes('ebook') ||
                              formatoTexto.toLowerCase().includes('digital');

            // Determinar precio visible
            const precioTexto = obtenerTextoPrecio(item);

            // Nombres de autores
            const autores = (libro.autores && libro.autores.length > 0)
                ? libro.autores.map(a => a.nombre).join(', ')
                : 'Autor no especificado';

            // Editorial
            const editorial = libro.editorial || 'Editorial independiente';

            // Estado del libro (Nuevo / De segunda mano)
            const estadoLibro = libro.estado || 'Nuevo';
            const esSegundaMano = estadoLibro === 'De segunda mano';

            // Enlace de compra real
            const urlCompra = libro.url_compra || libro.url_fuente || (ediciones[0] && ediciones[0].url_compra) || '#';
            const nombreTienda = (ediciones[0] && ediciones[0].tienda) || '';

            // Generar HTML de la tarjeta
            tarjeta.innerHTML = `
                <div class="tarjeta-libro__cabecera">
                    <span class="tarjeta-libro__formato ${esDigital ? 'tarjeta-libro__formato--digital' : 'tarjeta-libro__formato--fisico'}">
                        ${formatoTexto}
                    </span>
                    <span class="tarjeta-libro__estado ${esSegundaMano ? 'tarjeta-libro__estado--usado' : 'tarjeta-libro__estado--nuevo'}">
                        ${escaparHtml(estadoLibro)}
                    </span>
                    ${esIndependiente ? `
                        <span class="tarjeta-libro__independiente" title="Puntuacion de independencia: ${puntuacionIndie}/100">
                            Autor emergente
                        </span>
                    ` : ''}
                </div>
                <div class="tarjeta-libro__cuerpo">
                    <h3 class="tarjeta-libro__titulo" title="${escaparHtml(libro.titulo)}">
                        ${escaparHtml(libro.titulo)}
                    </h3>
                    <p class="tarjeta-libro__autor">${escaparHtml(autores)}</p>
                    <div class="tarjeta-libro__detalles">
                        <span class="tarjeta-libro__detalle">
                            <strong>Editorial:</strong> ${escaparHtml(editorial)}
                        </span>
                        ${libro.idioma ? `
                            <span class="tarjeta-libro__detalle">
                                <strong>Idioma:</strong> ${escaparHtml(libro.idioma)}
                            </span>
                        ` : ''}
                        ${libro.calificacion ? `
                            <span class="tarjeta-libro__detalle calificacion">
                                &#9733; ${libro.calificacion.toFixed(1)}
                            </span>
                        ` : ''}
                    </div>
                </div>
                <div class="tarjeta-libro__pie">
                    <div>
                        <div class="tarjeta-libro__precio ${precioTexto.esNumero ? '' : 'tarjeta-libro__precio--sin-dato'}">
                            ${precioTexto.texto}
                        </div>
                        ${nombreTienda ? `<span class="tarjeta-libro__nombre-tienda">${escaparHtml(nombreTienda)}</span>` : ''}
                    </div>
                    <div class="tarjeta-libro__tienda">
                        ${urlCompra !== '#' ? `
                            <a href="${urlCompra}" target="_blank" rel="noopener noreferrer" class="tarjeta-libro__enlace">
                                Ver ejemplar &rarr;
                            </a>
                        ` : `
                            <span class="tarjeta-libro__enlace tarjeta-libro__enlace--inactivo">Sin enlace</span>
                        `}
                    </div>
                </div>
            `;

            contenedorResultados.appendChild(tarjeta);
        });
    }

    /**
     * Formatea el tipo de formato para mostrar de forma limpia (Físico / Kindle / Digital).
     */
    function formatearTipoEdicion(libro, ediciones) {
        if (ediciones.length > 0 && ediciones[0].formato) {
            const f = ediciones[0].formato.toLowerCase();
            if (f === 'ebook' || f.includes('kindle')) return 'Edición Kindle / Digital';
            if (f === 'tapa_dura') return 'Tapa dura (Físico)';
            if (f === 'tapa_blanda') return 'Tapa blanda (Físico)';
            if (f === 'bolsillo') return 'Libro de bolsillo';
            if (f === 'audiolibro') return 'Audiolibro';
        }

        if (libro.categorias && libro.categorias.some(c => c.toLowerCase().includes('kindle'))) {
            return 'Edición Kindle';
        }

        return 'Edición impresa / física';
    }

    /**
     * Obtiene el texto formateado de precio de un libro o edición.
     */
    function obtenerTextoPrecio(item) {
        let precio = null;
        let moneda = 'EUR';

        if (item.ediciones && item.ediciones.length > 0) {
            const edicionValida = item.ediciones.find(e => e.precio !== null && e.precio !== undefined);
            if (edicionValida) {
                precio = edicionValida.precio;
                moneda = edicionValida.moneda || 'EUR';
            }
        }

        if (precio === null || precio === undefined) {
            return { texto: 'Consultar precio', esNumero: false };
        }

        if (precio === 0) {
            return { texto: 'Gratis', esNumero: true };
        }

        const simboloMoneda = moneda === 'EUR' ? 'EUR' : moneda;
        return {
            texto: `${precio.toFixed(2)} ${simboloMoneda}`,
            esNumero: true
        };
    }

    /**
     * Alterna la disposición visual entre cuadrícula y lista.
     */
    function cambiarVista(tipo) {
        vistaActual = tipo;

        if (tipo === 'cuadricula') {
            vistaCuadricula.classList.add('boton-vista--activo');
            vistaLista.classList.remove('boton-vista--activo');
            contenedorResultados.className = 'resultados resultados--cuadricula';
        } else {
            vistaLista.classList.add('boton-vista--activo');
            vistaCuadricula.classList.remove('boton-vista--activo');
            contenedorResultados.className = 'resultados resultados--lista';
        }
    }

    // -- Control de visibilidad de estados --

    function mostrarCarga() {
        seccionBienvenida.style.display = 'none';
        contenedorResultados.style.display = 'none';
        seccionSinResultados.style.display = 'none';
        seccionError.style.display = 'none';
        controlesVista.style.display = 'none';
        estadoCarga.style.display = 'flex';
    }

    function ocultarCarga() {
        estadoCarga.style.display = 'none';
    }

    function mostrarResultados() {
        seccionBienvenida.style.display = 'none';
        seccionSinResultados.style.display = 'none';
        seccionError.style.display = 'none';
        controlesVista.style.display = 'flex';
        contenedorResultados.style.display = vistaActual === 'cuadricula' ? 'grid' : 'flex';
    }

    function mostrarSinResultados() {
        seccionBienvenida.style.display = 'none';
        contenedorResultados.style.display = 'none';
        controlesVista.style.display = 'none';
        seccionError.style.display = 'none';
        seccionSinResultados.style.display = 'flex';
    }

    function mostrarError(mensaje) {
        ocultarCarga();
        seccionBienvenida.style.display = 'none';
        contenedorResultados.style.display = 'none';
        controlesVista.style.display = 'none';
        seccionSinResultados.style.display = 'none';
        textoError.textContent = mensaje || 'No se pudo conectar con el servidor.';
        seccionError.style.display = 'flex';
    }

    function escaparHtml(cadena) {
        if (!cadena) return '';
        const mapa = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(cadena).replace(/[&<>"']/g, m => mapa[m]);
    }
});
