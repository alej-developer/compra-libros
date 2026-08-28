"""
Servicio orquestador del motor de scraping.

Coordina la ejecucion de multiples scrapers, aplica filtros de autores
independientes y consolida los resultados. Es el punto central de la
logica de negocio para las operaciones de scraping.

No se almacenan datos personales de los usuarios del sistema.
"""

import asyncio
import logging
import time
from typing import List, Optional

from app.modelos import Libro, FiltroScraping
from app.modelos.edicion import FormatoLibro
from app.modelos.resultado_busqueda import LibroConEdiciones, ResultadoBusqueda
from app.scraping.base import ScraperBase
from app.scraping.scraper_libreria_fisica import ScraperLibreriaFisica
from app.scraping.scraper_plataforma_digital import ScraperPlataformaDigital
from app.scraping.scraper_segunda_mano import ScraperSegundaMano
from app.scraping.filtro_autores import FiltroAutoresIndependientes


logger = logging.getLogger("servicios.scraping")


class ServicioScraping:
    """
    Servicio principal que orquesta las operaciones de scraping.

    Gestiona multiples scrapers (fisicos, digitales y de segunda mano),
    ejecuta busquedas en paralelo, aplica el algoritmo de filtrado de
    autores independientes y consolida los resultados en una respuesta
    unificada.

    Incluye filtrado silencioso: los libros sin URL de compra valida
    se descartan automaticamente de los resultados finales.

    Atributos:
        _scrapers: Lista de scrapers registrados.
        _filtro_autores: Instancia del algoritmo de filtrado.
    """

    def __init__(self) -> None:
        """Inicializa el servicio con los scrapers y filtros configurados."""
        self._scrapers: List[ScraperBase] = []
        self._filtro_autores = FiltroAutoresIndependientes()
        self._registrar_scrapers_por_defecto()

    def _registrar_scrapers_por_defecto(self) -> None:
        """
        Registra los scrapers predefinidos del sistema.

        Cada scraper se configura con los selectores CSS apropiados
        para su sitio web objetivo. Los selectores por defecto son
        genericos y se pueden personalizar.
        """
        # -- Librerias fisicas --
        self._scrapers.append(
            ScraperLibreriaFisica(
                nombre_fuente="Casa del Libro",
                url_base="https://www.casadellibro.com",
                pais="Espana",
                selectores={
                    "contenedor_libro": ".product-list-item, .book-card",
                    "titulo": ".product-title a, .book-title",
                    "autor": ".product-author, .author-name",
                    "precio": ".current-price, .product-price",
                    "precio_oferta": ".sale-price, .discount-price",
                    "editorial": ".product-publisher, .editorial",
                    "imagen": "img.product-image, img.book-cover",
                    "enlace": ".product-title a, a.book-link",
                    "categoria": ".product-category, .genre",
                    "isbn": ".isbn-value, [itemprop='isbn']",
                    "resenas": ".reviews-count, .num-reviews",
                    "formato": ".product-format, .format-type",
                    "disponibilidad": ".stock-status, .availability",
                    "url_busqueda": "{url_base}/buscar-libro?q={termino}&page={pagina}",
                    "url_ofertas": "{url_base}/ofertas",
                },
            )
        )

        self._scrapers.append(
            ScraperLibreriaFisica(
                nombre_fuente="Libreria Nacional",
                url_base="https://www.librerianacional.com",
                pais="Colombia",
                selectores={
                    "contenedor_libro": ".product-item, .book-result",
                    "titulo": ".product-name a, .book-title",
                    "autor": ".product-author, .author",
                    "precio": ".product-price, .price",
                    "precio_oferta": ".special-price, .discount",
                    "editorial": ".product-editorial, .publisher",
                    "imagen": "img.product-img, img.book-image",
                    "enlace": ".product-name a, a.product-link",
                    "categoria": ".product-category, .category",
                    "isbn": ".isbn, .product-isbn",
                    "resenas": ".reviews, .rating-count",
                    "formato": ".format, .product-format",
                    "disponibilidad": ".availability, .stock",
                    "url_busqueda": "{url_base}/busqueda?q={termino}&page={pagina}",
                    "url_ofertas": "{url_base}/promociones",
                },
            )
        )

        # -- Plataformas digitales --
        self._scrapers.append(
            ScraperPlataformaDigital(
                nombre_fuente="Amazon Kindle",
                url_base="https://www.amazon.es",
                pais="Espana",
                moneda="EUR",
            )
        )

        self._scrapers.append(
            ScraperPlataformaDigital(
                nombre_fuente="Google Play Books",
                url_base="https://play.google.com/store/books",
                pais="Internacional",
                moneda="EUR",
                selectores={
                    "contenedor_libro": ".ULeU3b, .ImZGtf, .book-item",
                    "titulo": ".Epkrse, .book-title, h2",
                    "autor": ".b8cIId, .author, .book-author",
                    "precio": ".VfPpfd, .price, .book-price",
                    "precio_oferta": ".SUZt4c, .sale-price",
                    "editorial": ".publisher",
                    "imagen": "img.T75of, img.book-cover",
                    "enlace": "a.JC71ub, a.book-link",
                    "categoria": ".KoLSre, .genre",
                    "isbn": ".isbn",
                    "resenas": ".EGFGHd, .reviews-count",
                    "calificacion": ".pf5lIe, .star-rating",
                    "formato": ".format-type",
                    "disponibilidad": ".availability",
                    "url_busqueda": (
                        "{url_base}?q={termino}&c=books&hl=es&gl=ES&page={pagina}"
                    ),
                    "url_ofertas": "{url_base}?q=ofertas&c=books&hl=es&price=1",
                },
            )
        )

        # -- Plataformas de segunda mano --
        self._scrapers.append(
            ScraperSegundaMano(
                nombre_fuente="Iberlibro",
                url_base="https://www.iberlibro.com",
                pais="Espana",
                moneda="EUR",
                selectores={
                    "contenedor_libro": ".result-item, .cf-result",
                    "titulo": ".result-title a, .title a",
                    "autor": ".result-author, .author",
                    "precio": ".result-price, .item-price",
                    "editorial": ".result-publisher, .publisher",
                    "imagen": "img.result-image, img.srp-item-image",
                    "enlace": ".result-title a, .title a",
                    "categoria": ".result-category, .genre",
                    "isbn": ".result-isbn, .isbn",
                    "condicion": ".result-binding, .condition",
                    "formato": ".result-binding, .format",
                    "url_busqueda": "{url_base}/servlet/SearchResults?kn={termino}&pn={pagina}",
                    "url_ofertas": "{url_base}/servlet/SearchResults?sortby=1&kn=ofertas",
                },
            )
        )

        self._scrapers.append(
            ScraperSegundaMano(
                nombre_fuente="Todocoleccion",
                url_base="https://www.todocoleccion.net",
                pais="Espana",
                moneda="EUR",
                selectores={
                    "contenedor_libro": ".product-card, .lot-item, .search-result-item",
                    "titulo": ".product-title a, .lot-title a, h3 a",
                    "autor": ".product-author, .lot-author",
                    "precio": ".product-price, .lot-price, .price-value",
                    "editorial": ".product-publisher, .editorial",
                    "imagen": "img.product-img, img.lot-image",
                    "enlace": ".product-title a, .lot-title a, h3 a",
                    "categoria": ".product-category, .lot-category",
                    "isbn": ".isbn",
                    "condicion": ".product-condition, .lot-condition",
                    "formato": ".product-format",
                    "url_busqueda": "{url_base}/libros-segunda-mano/{termino}?pag={pagina}",
                    "url_ofertas": "{url_base}/libros-segunda-mano/?sort=price_asc",
                },
            )
        )

        self._scrapers.append(
            ScraperSegundaMano(
                nombre_fuente="Uniliber",
                url_base="https://www.uniliber.com",
                pais="Espana",
                moneda="EUR",
                selectores={
                    "contenedor_libro": ".libro-item, .book-result, .ficha-libro",
                    "titulo": ".libro-titulo a, .book-title a, h2 a",
                    "autor": ".libro-autor, .book-author",
                    "precio": ".libro-precio, .book-price",
                    "editorial": ".libro-editorial, .book-publisher",
                    "imagen": "img.libro-imagen, img.book-cover",
                    "enlace": ".libro-titulo a, .book-title a, h2 a",
                    "categoria": ".libro-categoria, .book-genre",
                    "isbn": ".libro-isbn, .isbn",
                    "condicion": ".libro-estado, .book-condition",
                    "formato": ".libro-formato, .book-format",
                    "url_busqueda": "{url_base}/busqueda/?searchword={termino}&page={pagina}",
                    "url_ofertas": "{url_base}/busqueda/?searchword=ofertas&sort=price",
                },
            )
        )

        logger.info(
            "Registrados %d scrapers: %s",
            len(self._scrapers),
            ", ".join(s.nombre_fuente for s in self._scrapers),
        )

    def registrar_scraper(self, scraper: ScraperBase) -> None:
        """
        Registra un nuevo scraper en el servicio.

        Parametros:
            scraper: Instancia de un scraper a registrar.
        """
        self._scrapers.append(scraper)
        logger.info("Scraper registrado: %s", scraper.nombre_fuente)

    @property
    def scrapers_disponibles(self) -> List[dict]:
        """Retorna informacion sobre los scrapers registrados."""
        return [
            {
                "nombre": s.nombre_fuente,
                "tipo": s.tipo_fuente,
                "pais": s.pais,
                "url_base": s.url_base,
            }
            for s in self._scrapers
        ]

    async def buscar(self, filtro: FiltroScraping) -> ResultadoBusqueda:
        """
        Ejecuta una busqueda en todos los scrapers registrados.

        Lanza las busquedas en paralelo en todos los scrapers (o solo
        en los especificados en el filtro) y consolida los resultados.
        Los libros sin URL de compra valida se descartan silenciosamente.

        Parametros:
            filtro: Criterios de busqueda y filtraje.

        Retorna:
            ResultadoBusqueda con los libros encontrados y metadatos.
        """
        inicio = time.time()
        errores = []

        # Seleccionar scrapers segun el filtro
        scrapers_activos = self._seleccionar_scrapers(filtro)

        logger.info(
            "Iniciando busqueda '%s' en %d fuentes",
            filtro.termino_busqueda, len(scrapers_activos),
        )

        # Ejecutar busquedas en paralelo
        tareas = [
            self._buscar_con_manejo_errores(scraper, filtro, errores)
            for scraper in scrapers_activos
        ]
        resultados_por_fuente = await asyncio.gather(*tareas)

        # Consolidar resultados y filtrar libros sin URL de compra valida
        todos_los_libros = []
        for libros_fuente in resultados_por_fuente:
            for libro in libros_fuente:
                if self._tiene_url_compra_valida(libro):
                    libro_con_ediciones = LibroConEdiciones(libro=libro)
                    todos_los_libros.append(libro_con_ediciones)

        # Eliminar duplicados por titulo similar
        libros_unicos = self._eliminar_duplicados(todos_los_libros)

        tiempo_total = time.time() - inicio

        resultado = ResultadoBusqueda(
            libros=libros_unicos,
            total_encontrados=len(libros_unicos),
            pagina_actual=filtro.pagina,
            termino_busqueda=filtro.termino_busqueda,
            fuentes_consultadas=[s.nombre_fuente for s in scrapers_activos],
            tiempo_ejecucion_segundos=round(tiempo_total, 2),
            errores=errores,
        )

        logger.info(
            "Busqueda completada: %d libros en %.2f segundos",
            resultado.total_encontrados, tiempo_total,
        )

        return resultado

    async def buscar_ofertas(
        self,
        precio_maximo: float = 10.0,
        limite: int = 50,
    ) -> ResultadoBusqueda:
        """
        Busca libros con precios muy bajos en todas las fuentes.

        Parametros:
            precio_maximo: Precio maximo para considerar oferta.
            limite: Numero maximo de resultados totales.

        Retorna:
            ResultadoBusqueda con los libros en oferta.
        """
        inicio = time.time()
        errores = []

        logger.info(
            "Buscando ofertas (precio maximo: %.2f) en %d fuentes",
            precio_maximo, len(self._scrapers),
        )

        tareas = [
            self._obtener_ofertas_con_manejo_errores(
                scraper, precio_maximo, limite, errores
            )
            for scraper in self._scrapers
        ]
        resultados_por_fuente = await asyncio.gather(*tareas)

        # Consolidar resultados y filtrar libros sin URL de compra valida
        todos_los_libros = []
        for libros_fuente in resultados_por_fuente:
            for libro in libros_fuente:
                if self._tiene_url_compra_valida(libro):
                    libro_con_ediciones = LibroConEdiciones(libro=libro)
                    todos_los_libros.append(libro_con_ediciones)

        libros_unicos = self._eliminar_duplicados(todos_los_libros)
        tiempo_total = time.time() - inicio

        return ResultadoBusqueda(
            libros=libros_unicos[:limite],
            total_encontrados=len(libros_unicos),
            termino_busqueda=f"ofertas (max {precio_maximo})",
            fuentes_consultadas=[s.nombre_fuente for s in self._scrapers],
            tiempo_ejecucion_segundos=round(tiempo_total, 2),
            errores=errores,
        )

    async def buscar_autores_independientes(
        self,
        filtro: FiltroScraping,
        puntuacion_minima: float = 50.0,
    ) -> ResultadoBusqueda:
        """
        Busca libros priorizando autores poco conocidos o independientes.

        Primero realiza una busqueda normal, luego aplica el algoritmo
        de filtrado para identificar y priorizar autores independientes.

        Parametros:
            filtro: Criterios de busqueda.
            puntuacion_minima: Puntuacion minima de independencia (0-100).

        Retorna:
            ResultadoBusqueda con libros de autores independientes.
        """
        # Primero, buscar normalmente
        resultado_base = await self.buscar(filtro)

        # Aplicar filtro de autores independientes
        libros_independientes = self._filtro_autores.filtrar_y_puntuar(
            resultado_base.libros,
            puntuacion_minima=puntuacion_minima,
        )

        estadisticas = self._filtro_autores.obtener_estadisticas(resultado_base.libros)

        resultado_base.libros = libros_independientes
        resultado_base.total_encontrados = len(libros_independientes)

        logger.info(
            "Filtrado de autores independientes: %s",
            estadisticas,
        )

        return resultado_base

    # -- Metodos internos --

    def _tiene_url_compra_valida(self, libro: Libro) -> bool:
        """
        Verifica si un libro tiene una URL de compra valida.

        Este metodo implementa el filtrado silencioso: los libros cuyo
        campo url_compra no comience con http:// o https:// se descartan
        sin generar errores visibles al usuario.

        Parametros:
            libro: Libro a verificar.

        Retorna:
            True si el libro tiene una URL de compra valida.
        """
        if not libro.url_compra:
            return False
        return libro.url_compra.startswith(("http://", "https://"))

    def _seleccionar_scrapers(self, filtro: FiltroScraping) -> List[ScraperBase]:
        """
        Selecciona los scrapers segun las tiendas especificadas en el filtro.

        Parametros:
            filtro: Filtro con tiendas especificadas (opcional).

        Retorna:
            Lista de scrapers a utilizar.
        """
        if not filtro.tiendas:
            return list(self._scrapers)

        seleccionados = [
            s for s in self._scrapers
            if s.nombre_fuente.lower() in [t.lower() for t in filtro.tiendas]
        ]

        if not seleccionados:
            logger.warning(
                "Ninguna tienda del filtro coincide. Usando todas las fuentes."
            )
            return list(self._scrapers)

        return seleccionados

    async def _buscar_con_manejo_errores(
        self,
        scraper: ScraperBase,
        filtro: FiltroScraping,
        errores: List[str],
    ) -> List[Libro]:
        """
        Ejecuta una busqueda en un scraper con manejo de errores.

        Parametros:
            scraper: Scraper a utilizar.
            filtro: Criterios de busqueda.
            errores: Lista donde agregar errores ocurridos.

        Retorna:
            Lista de libros encontrados (vacia si hubo error).
        """
        try:
            return await scraper.buscar_libros(filtro)
        except Exception as error:
            mensaje = f"Error en {scraper.nombre_fuente}: {str(error)}"
            logger.error(mensaje)
            errores.append(mensaje)
            return []

    async def _obtener_ofertas_con_manejo_errores(
        self,
        scraper: ScraperBase,
        precio_maximo: float,
        limite: int,
        errores: List[str],
    ) -> List[Libro]:
        """
        Busca ofertas en un scraper con manejo de errores.

        Parametros:
            scraper: Scraper a utilizar.
            precio_maximo: Precio maximo para ofertas.
            limite: Numero maximo de resultados.
            errores: Lista donde agregar errores.

        Retorna:
            Lista de libros en oferta (vacia si hubo error).
        """
        try:
            return await scraper.obtener_ofertas(
                precio_maximo=precio_maximo,
                limite=limite,
            )
        except Exception as error:
            mensaje = f"Error en ofertas de {scraper.nombre_fuente}: {str(error)}"
            logger.error(mensaje)
            errores.append(mensaje)
            return []

    def _eliminar_duplicados(
        self,
        libros: List[LibroConEdiciones],
    ) -> List[LibroConEdiciones]:
        """
        Elimina libros duplicados basandose en el titulo normalizado.

        Cuando se encuentra un duplicado, se conserva el que tiene
        mas informacion (mas campos completos).

        Parametros:
            libros: Lista de libros potencialmente duplicados.

        Retorna:
            Lista de libros sin duplicados.
        """
        vistos = {}
        for libro_ed in libros:
            clave = libro_ed.libro.titulo.lower().strip()
            if clave not in vistos:
                vistos[clave] = libro_ed
            else:
                # Conservar el que tenga mas campos completos
                existente = vistos[clave]
                if self._contar_campos(libro_ed.libro) > self._contar_campos(existente.libro):
                    vistos[clave] = libro_ed

        return list(vistos.values())

    def _contar_campos(self, libro: Libro) -> int:
        """
        Cuenta el numero de campos no nulos de un libro.

        Parametros:
            libro: Libro a evaluar.

        Retorna:
            Numero de campos con valor.
        """
        campos = [
            libro.titulo, libro.isbn, libro.editorial,
            libro.descripcion, libro.imagen_url, libro.idioma,
            libro.calificacion, libro.url_fuente, libro.url_compra,
        ]
        return sum(1 for c in campos if c is not None) + len(libro.autores) + len(libro.categorias)
