/**
 * Cliente de API para la comunicación con el backend FastAPI.
 * Proporciona métodos para consultar fuentes, buscar libros,
 * obtener ofertas y filtrar autores independientes.
 */

const URL_BASE_API = (typeof window !== 'undefined' && window.location && window.location.hostname)
    ? `http://${window.location.hostname}:8000`
    : 'http://127.0.0.1:8000';

class ClienteApiLibros {
    constructor(urlBase = URL_BASE_API) {
        this.urlBase = urlBase;
    }

    /**
     * Realiza una petición HTTP con control de errores.
     * @private
     */
    async _peticion(ruta, opciones = {}) {
        const url = `${this.urlBase}${ruta}`;
        const cabecerasPorDefecto = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };

        const configuracion = {
            ...opciones,
            headers: {
                ...cabecerasPorDefecto,
                ...(opciones.headers || {})
            }
        };

        try {
            const respuesta = await fetch(url, configuracion);
            if (!respuesta.ok) {
                const errorDetalle = await respuesta.text();
                throw new Error(`Error HTTP ${respuesta.status}: ${errorDetalle || respuesta.statusText}`);
            }
            return await respuesta.json();
        } catch (error) {
            console.error(`Fallo en la petición a ${ruta}:`, error);
            throw error;
        }
    }

    /**
     * Obtiene las fuentes de scraping registradas.
     * @returns {Promise<Object>}
     */
    async obtenerFuentes() {
        return await this._peticion('/api/scraping/fuentes');
    }

    /**
     * Realiza una búsqueda general de libros con filtros.
     * @param {Object} filtro - Criterios de búsqueda.
     * @returns {Promise<Object>}
     */
    async buscarLibros(filtro) {
        return await this._peticion('/api/scraping/buscar', {
            method: 'POST',
            body: JSON.stringify(filtro)
        });
    }

    /**
     * Obtiene libros en oferta o con precios reducidos.
     * @param {number} precioMaximo - Precio tope para ofertas.
     * @param {number} limite - Límite de resultados.
     * @returns {Promise<Object>}
     */
    async obtenerOfertas(precioMaximo = 10.0, limite = 50) {
        const parametros = new URLSearchParams({
            precio_maximo: precioMaximo.toString(),
            limite: limite.toString()
        });
        return await this._peticion(`/api/scraping/ofertas?${parametros.toString()}`);
    }

    /**
     * Realiza una búsqueda priorizando autores independientes o emergentes.
     * @param {Object} filtro - Criterios de búsqueda.
     * @param {number} puntuacionMinima - Puntuación mínima de independencia.
     * @returns {Promise<Object>}
     */
    async buscarAutoresIndependientes(filtro, puntuacionMinima = 50.0) {
        const parametros = new URLSearchParams({
            puntuacion_minima: puntuacionMinima.toString()
        });
        return await this._peticion(`/api/scraping/autores-independientes?${parametros.toString()}`, {
            method: 'POST',
            body: JSON.stringify(filtro)
        });
    }
}

window.clienteApi = new ClienteApiLibros();
