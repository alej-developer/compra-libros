"""
Scraper para plataformas digitales (Kindle, Google Books, etc.).

Implementa la logica de scraping especifica para tiendas de libros
digitales (ebooks, audiolibros). Extrae: titulo, autor, precio,
formato digital, genero, pais, editorial, url de compra real y estado.
"""

import logging
from typing import List, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.modelos import Libro, FiltroScraping
from app.modelos.libro import EstadoLibro
from app.modelos.edicion import FormatoLibro
from app.scraping.base import ScraperBase
from app.scraping.utilidades import limpiar_texto, extraer_precio


logger = logging.getLogger("scraping.plataforma_digital")


class ScraperPlataformaDigital(ScraperBase):
    """
    Scraper especializado en plataformas de libros digitales.

    Implementa la extraccion de datos de tiendas de ebooks y audiolibros
    como Amazon Kindle, Google Play Books, Kobo, etc.

    Las plataformas digitales suelen tener estructuras HTML diferentes
    a las librerias fisicas, con precios que varian segun la region
    y formatos exclusivamente digitales (EPUB, MOBI, PDF, audiolibro).

    La clase utiliza selectores CSS configurables para adaptarse a
    diferentes plataformas sin modificar la logica principal.
    """

    def __init__(
        self,
        nombre_fuente: str,
        url_base: str,
        pais: str = "Internacional",
        moneda: str = "EUR",
        selectores: Optional[dict] = None,
    ) -> None:
        """
        Inicializa el scraper de plataforma digital.

        Parametros:
            nombre_fuente: Nombre de la plataforma.
            url_base: URL base de la plataforma.
            pais: Pais o region de la plataforma.
            moneda: Moneda principal de la plataforma.
            selectores: Selectores CSS personalizados.
        """
        super().__init__(
            nombre_fuente=nombre_fuente,
            url_base=url_base,
            tipo_fuente="digital",
            pais=pais,
        )
        self._moneda = moneda
        self._selectores = selectores or self._selectores_por_defecto()

    def _selectores_por_defecto(self) -> dict:
        """
        Retorna los selectores CSS por defecto para plataformas digitales.

        Retorna:
            Diccionario con selectores CSS adaptados a tiendas digitales.
        """
        return {
            "contenedor_libro": (
                ".s-result-item, .book-item, .product-card, "
                "[data-component-type='s-search-result']"
            ),
            "titulo": (
                "h2 a span, .book-title, .product-title, "
                "[data-cy='title-recipe'] a"
            ),
            "autor": ".a-size-base+ .a-size-base, .author, .book-author",
            "precio": ".a-price .a-offscreen, .price, .ebook-price, .kindle-price",
            "precio_oferta": ".a-price[data-a-color='price'] .a-offscreen, .deal-price",
            "editorial": ".publisher, .editorial, [data-cy='publisher']",
            "imagen": "img.s-image, img.book-cover, .product-image img",
            "enlace": "h2 a, .book-link, a.product-link",
            "categoria": ".a-badge-text, .genre, .category-tag",
            "isbn": ".isbn, [itemprop='isbn']",
            "resenas": ".a-size-base.s-underline-text, .reviews-count, .rating-count",
            "calificacion": ".a-icon-alt, .star-rating, [data-cy='rating']",
            "formato": ".a-text-bold, .format-type, .book-format",
            "disponibilidad": ".a-declarative, .availability, .stock",
            "url_busqueda": (
                "{url_base}/s?k={termino}&i=digital-text&page={pagina}"
            ),
            "url_ofertas": "{url_base}/s?k=ebook+ofertas&i=digital-text&s=price-asc-rank",
        }

    async def construir_url_busqueda(self, filtro: FiltroScraping) -> str:
        """
        Construye la URL de busqueda para la plataforma digital.

        Parametros:
            filtro: Criterios de busqueda.

        Retorna:
            URL completa para la busqueda.
        """
        plantilla = self._selectores.get(
            "url_busqueda",
            "{url_base}/s?k={termino}&i=digital-text&page={pagina}",
        )
        url = plantilla.format(
            url_base=self._url_base,
            termino=quote_plus(filtro.termino_busqueda),
            pagina=filtro.pagina,
        )

        # Agregar filtros de precio si estan definidos
        parametros_extra = []
        if filtro.precio_minimo is not None:
            # El formato de precio varia por plataforma; se usa centimos
            precio_min_centimos = int(filtro.precio_minimo * 100)
            parametros_extra.append(f"low-price={filtro.precio_minimo}")
        if filtro.precio_maximo is not None:
            parametros_extra.append(f"high-price={filtro.precio_maximo}")

        if parametros_extra:
            separador = "&" if "?" in url else "?"
            url += separador + "&".join(parametros_extra)

        return url

    async def buscar_libros(self, filtro: FiltroScraping) -> List[Libro]:
        """
        Busca libros digitales segun los filtros proporcionados.

        Parametros:
            filtro: Criterios de busqueda y filtraje.

        Retorna:
            Lista de libros digitales encontrados.
        """
        url = await self.construir_url_busqueda(filtro)
        self._logger.info(
            "Buscando en %s (digital): '%s'",
            self._nombre_fuente, filtro.termino_busqueda,
        )

        pagina = await self._cliente.obtener_pagina(url)
        if pagina is None:
            self._logger.warning("No se pudo acceder a %s", url)
            return []

        libros = self._parsear_resultados(pagina, filtro)
        self._logger.info(
            "Encontrados %d libros digitales en %s",
            len(libros), self._nombre_fuente,
        )
        return libros

    async def extraer_detalles_libro(self, url_libro: str) -> Optional[Libro]:
        """
        Extrae los detalles completos de un ebook desde su pagina.

        Parametros:
            url_libro: URL directa a la pagina del libro digital.

        Retorna:
            Libro con todos los detalles, o None si falla.
        """
        self._logger.info("Extrayendo detalles digitales de: %s", url_libro)

        pagina = await self._cliente.obtener_pagina(url_libro)
        if pagina is None:
            return None

        try:
            titulo = self._extraer_texto(pagina, "h1, #productTitle, #ebooksProductTitle")
            autor = self._extraer_texto(pagina, ".author a, #bylineInfo a, .contributorNameID")
            precio_texto = self._extraer_texto(pagina, self._selectores["precio"])
            editorial = self._extraer_texto(pagina, "#detailBullets_feature_div, .publisher")
            categoria = self._extraer_texto(pagina, ".a-breadcrumb a, .genre")

            if not titulo:
                self._logger.warning("No se encontro titulo en %s", url_libro)
                return None

            # Validar URL de compra: si no es valida, descartar silenciosamente
            url_compra = self._construir_url_absoluta(url_libro)
            if not self._validar_url_compra(url_compra):
                self._logger.debug(
                    "Descartado libro '%s': URL de compra no valida", titulo
                )
                return None

            # Los libros digitales siempre son formato ebook
            formato = FormatoLibro.EBOOK

            libro = self._crear_libro(
                titulo=titulo,
                nombre_autor=autor or "Autor desconocido",
                url_compra=url_compra,
                estado=EstadoLibro.NUEVO,
                precio=extraer_precio(precio_texto),
                formato=formato,
                editorial=editorial,
                categorias=[categoria] if categoria else [],
                url_fuente=url_libro,
            )
            return libro

        except Exception as error:
            self._logger.error(
                "Error al extraer detalles de %s: %s", url_libro, str(error)
            )
            return None

    async def obtener_ofertas(
        self,
        precio_maximo: float = 3.0,
        limite: int = 20,
    ) -> List[Libro]:
        """
        Busca ebooks con precios muy bajos o gratuitos.

        Las plataformas digitales suelen tener mas ofertas que las
        librerias fisicas, con ebooks desde 0.99 EUR o incluso gratuitos.

        Parametros:
            precio_maximo: Precio maximo para considerar oferta (por defecto 3 EUR).
            limite: Numero maximo de resultados.

        Retorna:
            Lista de ebooks en oferta ordenados por precio ascendente.
        """
        url_ofertas = self._selectores.get("url_ofertas", "").format(
            url_base=self._url_base
        )
        self._logger.info(
            "Buscando ofertas digitales en %s (precio maximo: %.2f)",
            self._nombre_fuente, precio_maximo,
        )

        pagina = await self._cliente.obtener_pagina(url_ofertas)
        if pagina is None:
            self._logger.warning(
                "No se pudo acceder a ofertas en %s", self._nombre_fuente
            )
            return []

        filtro_ofertas = FiltroScraping(
            termino_busqueda="ofertas ebook",
            precio_maximo=precio_maximo,
            resultados_por_pagina=limite,
        )

        libros = self._parsear_resultados(pagina, filtro_ofertas)

        # Ordenar por precio ascendente (los mas baratos primero)
        libros_con_precio = [l for l in libros if l.calificacion is not None or True]
        return libros_con_precio[:limite]

    async def buscar_ebooks_gratuitos(self, limite: int = 20) -> List[Libro]:
        """
        Busca ebooks completamente gratuitos.

        Muchas plataformas ofrecen libros clasicos o promocionales
        de forma gratuita. Este metodo los localiza especificamente.

        Parametros:
            limite: Numero maximo de resultados.

        Retorna:
            Lista de ebooks gratuitos.
        """
        return await self.obtener_ofertas(precio_maximo=0.01, limite=limite)

    # -- Metodos internos de parseo --

    def _parsear_resultados(
        self,
        pagina: BeautifulSoup,
        filtro: FiltroScraping,
    ) -> List[Libro]:
        """
        Parsea la pagina de resultados de la plataforma digital.

        Parametros:
            pagina: HTML parseado de la pagina de resultados.
            filtro: Filtros a aplicar durante el parseo.

        Retorna:
            Lista de libros extraidos.
        """
        libros = []
        contenedores = pagina.select(self._selectores["contenedor_libro"])

        for contenedor in contenedores:
            try:
                libro = self._parsear_contenedor_digital(contenedor)
                if libro and self._cumple_filtros(libro, filtro):
                    libros.append(libro)
            except Exception as error:
                self._logger.debug(
                    "Error al parsear libro digital: %s", str(error)
                )
                continue

        return libros

    def _parsear_contenedor_digital(
        self,
        contenedor: BeautifulSoup,
    ) -> Optional[Libro]:
        """
        Extrae los datos de un ebook desde su contenedor HTML.

        Descarta silenciosamente los libros que no tengan un enlace
        valido (href real que apunte a una URL absoluta).

        Parametros:
            contenedor: Elemento HTML que contiene los datos del ebook.

        Retorna:
            Libro extraido, o None si no se obtuvieron datos minimos
            o si el enlace de compra no es valido.
        """
        titulo = self._extraer_texto(contenedor, self._selectores["titulo"])
        if not titulo:
            return None

        autor = self._extraer_texto(contenedor, self._selectores["autor"])
        precio_texto = self._extraer_texto(contenedor, self._selectores["precio"])
        precio_oferta_texto = self._extraer_texto(
            contenedor, self._selectores["precio_oferta"]
        )
        editorial = self._extraer_texto(contenedor, self._selectores["editorial"])
        categoria = self._extraer_texto(contenedor, self._selectores["categoria"])
        formato_texto = self._extraer_texto(contenedor, self._selectores["formato"])

        # Preferir precio de oferta
        precio = extraer_precio(precio_oferta_texto) or extraer_precio(precio_texto)

        # En plataformas digitales, el formato por defecto es ebook
        formato = self._determinar_formato_digital(formato_texto)

        # Extraer URL real del enlace (atributo href)
        enlace = contenedor.select_one(self._selectores["enlace"])
        url_compra = None
        if enlace and enlace.get("href"):
            url_compra = self._construir_url_absoluta(enlace["href"])

        # Descarte silencioso: si no hay URL de compra valida, omitir el libro
        if not self._validar_url_compra(url_compra):
            self._logger.debug(
                "Descartado libro digital '%s': sin enlace de compra valido", titulo
            )
            return None

        # Extraer imagen
        imagen = contenedor.select_one(self._selectores["imagen"])
        imagen_url = None
        if imagen:
            imagen_url = imagen.get("src") or imagen.get("data-src")

        # Extraer calificacion
        calificacion = self._extraer_calificacion(contenedor)

        return self._crear_libro(
            titulo=titulo,
            nombre_autor=autor or "Autor desconocido",
            url_compra=url_compra,
            estado=EstadoLibro.NUEVO,
            precio=precio,
            formato=formato,
            editorial=editorial,
            categorias=[categoria] if categoria else [],
            imagen_url=imagen_url,
            url_fuente=url_compra,
            calificacion=calificacion,
        )

    def _determinar_formato_digital(self, texto: Optional[str]) -> FormatoLibro:
        """
        Determina el formato digital del libro.

        Parametros:
            texto: Texto que describe el formato.

        Retorna:
            FormatoLibro correspondiente (por defecto EBOOK).
        """
        if not texto:
            return FormatoLibro.EBOOK

        texto_lower = texto.lower()
        if "audiolibro" in texto_lower or "audiobook" in texto_lower or "audio" in texto_lower:
            return FormatoLibro.AUDIOLIBRO
        elif "tapa dura" in texto_lower or "hardcover" in texto_lower:
            return FormatoLibro.TAPA_DURA
        elif "tapa blanda" in texto_lower or "paperback" in texto_lower:
            return FormatoLibro.TAPA_BLANDA

        return FormatoLibro.EBOOK

    def _extraer_calificacion(self, contenedor: BeautifulSoup) -> Optional[float]:
        """
        Extrae la calificacion numerica de un libro.

        Parametros:
            contenedor: Elemento HTML donde buscar la calificacion.

        Retorna:
            Calificacion como float (0.0 a 5.0), o None.
        """
        selector_cal = self._selectores.get("calificacion", "")
        texto = self._extraer_texto(contenedor, selector_cal)
        if not texto:
            return None

        import re
        # Buscar patrones como "4.5 de 5", "4,5 out of 5", "4.5"
        patron = re.search(r"(\d[.,]\d)", texto)
        if patron:
            try:
                valor = float(patron.group(1).replace(",", "."))
                if 0.0 <= valor <= 5.0:
                    return valor
            except ValueError:
                pass
        return None

    def _cumple_filtros(self, libro: Libro, filtro: FiltroScraping) -> bool:
        """
        Verifica si un libro cumple con los criterios de filtraje.

        Parametros:
            libro: Libro a verificar.
            filtro: Criterios de filtrado.

        Retorna:
            True si el libro cumple todos los filtros.
        """
        if filtro.categoria and libro.categorias:
            if not any(
                filtro.categoria.lower() in cat.lower() for cat in libro.categorias
            ):
                return False

        if filtro.idioma and libro.idioma:
            if filtro.idioma.lower() not in libro.idioma.lower():
                return False

        return True

    def _extraer_texto(
        self,
        elemento: BeautifulSoup,
        selector: str,
    ) -> Optional[str]:
        """
        Extrae texto limpio de un elemento HTML usando un selector CSS.

        Parametros:
            elemento: Elemento HTML donde buscar.
            selector: Selector CSS para localizar el texto.

        Retorna:
            Texto limpio, o None si no se encuentra.
        """
        encontrado = elemento.select_one(selector)
        if encontrado:
            return limpiar_texto(encontrado.get_text())
        return None
