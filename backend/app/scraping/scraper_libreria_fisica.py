"""
Scraper para librerias fisicas (tiendas en linea de librerias tradicionales).

Implementa la logica de scraping especifica para sitios web de librerias
fisicas como Casa del Libro, Libreria Nacional, etc.
Extrae: titulo, autor, precio, formato, genero, pais, editorial,
url de compra real y estado del libro.
"""

import logging
from typing import List, Optional
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from app.modelos import Libro, FiltroScraping
from app.modelos.libro import EstadoLibro
from app.modelos.edicion import FormatoLibro, EstadoDisponibilidad, Edicion
from app.scraping.base import ScraperBase
from app.scraping.utilidades import limpiar_texto, extraer_precio


logger = logging.getLogger("scraping.libreria_fisica")


class ScraperLibreriaFisica(ScraperBase):
    """
    Scraper especializado en librerias fisicas con presencia en linea.

    Implementa la extraccion de datos de sitios web de librerias tradicionales.
    Cada instancia se configura con los selectores CSS especificos del sitio
    objetivo, lo que permite reutilizar la logica para multiples librerias.

    La clase utiliza un diccionario de selectores CSS para localizar los
    elementos en el HTML, lo que facilita la adaptacion a diferentes sitios
    sin modificar la logica principal.
    """

    def __init__(
        self,
        nombre_fuente: str,
        url_base: str,
        pais: str = "Espana",
        selectores: Optional[dict] = None,
    ) -> None:
        """
        Inicializa el scraper de libreria fisica.

        Parametros:
            nombre_fuente: Nombre de la libreria.
            url_base: URL base del sitio web.
            pais: Pais de la libreria.
            selectores: Diccionario con selectores CSS para cada campo.
                Claves esperadas:
                - 'contenedor_libro': Selector del contenedor de cada libro.
                - 'titulo': Selector del titulo.
                - 'autor': Selector del autor.
                - 'precio': Selector del precio.
                - 'precio_oferta': Selector del precio en oferta.
                - 'editorial': Selector de la editorial.
                - 'imagen': Selector de la imagen de portada.
                - 'enlace': Selector del enlace al detalle.
                - 'categoria': Selector de la categoria/genero.
                - 'isbn': Selector del ISBN.
                - 'resenas': Selector del numero de resenas.
                - 'formato': Selector del formato.
                - 'disponibilidad': Selector de disponibilidad.
                - 'url_busqueda': Plantilla de URL de busqueda.
                - 'url_ofertas': URL de la seccion de ofertas.
        """
        super().__init__(
            nombre_fuente=nombre_fuente,
            url_base=url_base,
            tipo_fuente="fisica",
            pais=pais,
        )
        self._selectores = selectores or self._selectores_por_defecto()

    def _selectores_por_defecto(self) -> dict:
        """
        Retorna los selectores CSS por defecto.

        Estos selectores son genericos y deben ser personalizados para
        cada sitio web objetivo.

        Retorna:
            Diccionario con los selectores CSS por defecto.
        """
        return {
            "contenedor_libro": ".libro, .book-item, .product-item, article.product",
            "titulo": "h2 a, h3 a, .titulo, .book-title, .product-title",
            "autor": ".autor, .author, .book-author",
            "precio": ".precio, .price, .book-price, .current-price",
            "precio_oferta": ".precio-oferta, .sale-price, .discount-price",
            "editorial": ".editorial, .publisher",
            "imagen": "img.portada, img.book-cover, img.product-image",
            "enlace": "a.detalle, a.book-link, h2 a, h3 a",
            "categoria": ".categoria, .genre, .book-genre",
            "isbn": ".isbn, [itemprop='isbn']",
            "resenas": ".resenas, .reviews-count, .num-reviews",
            "formato": ".formato, .format, .book-format",
            "disponibilidad": ".disponibilidad, .availability, .stock-status",
            "url_busqueda": "{url_base}/buscar?q={termino}&page={pagina}",
            "url_ofertas": "{url_base}/ofertas",
        }

    async def construir_url_busqueda(self, filtro: FiltroScraping) -> str:
        """
        Construye la URL de busqueda para la libreria fisica.

        Parametros:
            filtro: Criterios de busqueda.

        Retorna:
            URL completa para la busqueda.
        """
        plantilla = self._selectores.get(
            "url_busqueda",
            "{url_base}/buscar?q={termino}&page={pagina}",
        )
        return plantilla.format(
            url_base=self._url_base,
            termino=quote_plus(filtro.termino_busqueda),
            pagina=filtro.pagina,
        )

    async def buscar_libros(self, filtro: FiltroScraping) -> List[Libro]:
        """
        Busca libros en la libreria fisica segun los filtros.

        Parametros:
            filtro: Criterios de busqueda y filtraje.

        Retorna:
            Lista de libros encontrados.
        """
        url = await self.construir_url_busqueda(filtro)
        self._logger.info("Buscando en %s: '%s'", self._nombre_fuente, filtro.termino_busqueda)

        pagina = await self._cliente.obtener_pagina(url)
        if pagina is None:
            self._logger.warning("No se pudo acceder a %s", url)
            return []

        libros = self._parsear_resultados(pagina, filtro)
        self._logger.info(
            "Encontrados %d libros en %s", len(libros), self._nombre_fuente
        )
        return libros

    async def extraer_detalles_libro(self, url_libro: str) -> Optional[Libro]:
        """
        Extrae los detalles completos de un libro desde su pagina individual.

        Parametros:
            url_libro: URL directa a la pagina del libro.

        Retorna:
            Libro con todos los detalles, o None si falla.
        """
        self._logger.info("Extrayendo detalles de: %s", url_libro)

        pagina = await self._cliente.obtener_pagina(url_libro)
        if pagina is None:
            return None

        try:
            titulo = self._extraer_texto(pagina, "h1, .titulo-detalle, .product-title")
            autor = self._extraer_texto(pagina, ".autor-detalle, .author-detail, .book-author")
            precio_texto = self._extraer_texto(pagina, self._selectores["precio"])
            editorial = self._extraer_texto(pagina, self._selectores["editorial"])
            isbn = self._extraer_texto(pagina, self._selectores["isbn"])
            categoria = self._extraer_texto(pagina, self._selectores["categoria"])

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

            libro = self._crear_libro(
                titulo=titulo,
                nombre_autor=autor or "Autor desconocido",
                url_compra=url_compra,
                estado=EstadoLibro.NUEVO,
                precio=extraer_precio(precio_texto),
                formato=FormatoLibro.TAPA_BLANDA,
                editorial=editorial,
                categorias=[categoria] if categoria else [],
                isbn=self._normalizar_isbn(isbn),
                url_fuente=url_libro,
            )
            return libro

        except Exception as error:
            self._logger.error("Error al extraer detalles de %s: %s", url_libro, str(error))
            return None

    async def obtener_ofertas(
        self,
        precio_maximo: float = 10.0,
        limite: int = 20,
    ) -> List[Libro]:
        """
        Busca libros en oferta o con precios muy bajos.

        Consulta la seccion de ofertas de la libreria y filtra por
        precio maximo. Prioriza libros con mayor descuento.

        Parametros:
            precio_maximo: Precio maximo para considerar oferta (en euros).
            limite: Numero maximo de resultados.

        Retorna:
            Lista de libros en oferta ordenados por precio ascendente.
        """
        url_ofertas = self._selectores.get("url_ofertas", "").format(
            url_base=self._url_base
        )
        self._logger.info(
            "Buscando ofertas en %s (precio maximo: %.2f)",
            self._nombre_fuente, precio_maximo,
        )

        pagina = await self._cliente.obtener_pagina(url_ofertas)
        if pagina is None:
            self._logger.warning("No se pudo acceder a ofertas en %s", self._nombre_fuente)
            return []

        # Crear filtro con precio maximo para reutilizar el parser
        filtro_ofertas = FiltroScraping(
            termino_busqueda="ofertas",
            precio_maximo=precio_maximo,
            resultados_por_pagina=limite,
        )

        libros = self._parsear_resultados(pagina, filtro_ofertas)

        # Filtrar por precio maximo y ordenar por precio ascendente
        libros_filtrados = [
            libro for libro in libros
            if libro.calificacion is None or True  # Se incluyen todos, el filtro de precio se aplica en el parseo
        ]

        return libros_filtrados[:limite]

    # -- Metodos internos de parseo --

    def _parsear_resultados(
        self,
        pagina: BeautifulSoup,
        filtro: FiltroScraping,
    ) -> List[Libro]:
        """
        Parsea la pagina de resultados y extrae la lista de libros.

        Parametros:
            pagina: HTML parseado de la pagina de resultados.
            filtro: Filtros para aplicar durante el parseo.

        Retorna:
            Lista de libros extraidos de la pagina.
        """
        libros = []
        contenedores = pagina.select(self._selectores["contenedor_libro"])

        for contenedor in contenedores:
            try:
                libro = self._parsear_contenedor_libro(contenedor)
                if libro and self._cumple_filtros(libro, filtro):
                    libros.append(libro)
            except Exception as error:
                self._logger.debug("Error al parsear un libro: %s", str(error))
                continue

        return libros

    def _parsear_contenedor_libro(self, contenedor: BeautifulSoup) -> Optional[Libro]:
        """
        Extrae los datos de un libro desde su contenedor HTML.

        Descarta silenciosamente los libros que no tengan un enlace
        valido (href real que apunte a una URL absoluta).

        Parametros:
            contenedor: Elemento HTML que contiene los datos del libro.

        Retorna:
            Libro extraido, o None si no se pudieron obtener los datos minimos
            o si el enlace de compra no es valido.
        """
        titulo = self._extraer_texto(contenedor, self._selectores["titulo"])
        if not titulo:
            return None

        autor = self._extraer_texto(contenedor, self._selectores["autor"])
        precio_texto = self._extraer_texto(contenedor, self._selectores["precio"])
        precio_oferta_texto = self._extraer_texto(contenedor, self._selectores["precio_oferta"])
        editorial = self._extraer_texto(contenedor, self._selectores["editorial"])
        categoria = self._extraer_texto(contenedor, self._selectores["categoria"])
        formato_texto = self._extraer_texto(contenedor, self._selectores["formato"])

        # Preferir precio de oferta si existe
        precio = extraer_precio(precio_oferta_texto) or extraer_precio(precio_texto)

        # Determinar formato
        formato = self._determinar_formato(formato_texto)

        # Extraer URL real del enlace (atributo href)
        enlace = contenedor.select_one(self._selectores["enlace"])
        url_compra = None
        if enlace and enlace.get("href"):
            url_compra = self._construir_url_absoluta(enlace["href"])

        # Descarte silencioso: si no hay URL de compra valida, omitir el libro
        if not self._validar_url_compra(url_compra):
            self._logger.debug(
                "Descartado libro '%s': sin enlace de compra valido", titulo
            )
            return None

        # Extraer imagen
        imagen = contenedor.select_one(self._selectores["imagen"])
        imagen_url = None
        if imagen:
            imagen_url = imagen.get("src") or imagen.get("data-src")

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
        )

    def _determinar_formato(self, texto_formato: Optional[str]) -> FormatoLibro:
        """
        Determina el formato del libro a partir de su descripcion textual.

        Parametros:
            texto_formato: Texto que describe el formato.

        Retorna:
            FormatoLibro correspondiente.
        """
        if not texto_formato:
            return FormatoLibro.OTRO

        texto = texto_formato.lower()
        if "tapa dura" in texto or "hardcover" in texto or "carton" in texto:
            return FormatoLibro.TAPA_DURA
        elif "tapa blanda" in texto or "paperback" in texto or "rustica" in texto:
            return FormatoLibro.TAPA_BLANDA
        elif "bolsillo" in texto or "pocket" in texto:
            return FormatoLibro.BOLSILLO
        elif "ebook" in texto or "digital" in texto or "kindle" in texto:
            return FormatoLibro.EBOOK
        elif "audiolibro" in texto or "audio" in texto:
            return FormatoLibro.AUDIOLIBRO
        return FormatoLibro.OTRO

    def _cumple_filtros(self, libro: Libro, filtro: FiltroScraping) -> bool:
        """
        Verifica si un libro cumple con los criterios de filtraje.

        Parametros:
            libro: Libro a verificar.
            filtro: Criterios de filtrado.

        Retorna:
            True si el libro cumple todos los filtros, False en caso contrario.
        """
        # Filtro por categoria
        if filtro.categoria and libro.categorias:
            if not any(
                filtro.categoria.lower() in cat.lower() for cat in libro.categorias
            ):
                return False

        # Filtro por idioma
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

    def _normalizar_isbn(self, isbn: Optional[str]) -> Optional[str]:
        """
        Normaliza un ISBN eliminando guiones y espacios.

        Parametros:
            isbn: ISBN en cualquier formato.

        Retorna:
            ISBN limpio (solo digitos), o None si no es valido.
        """
        if not isbn:
            return None
        import re
        limpio = re.sub(r"[^0-9]", "", isbn)
        if len(limpio) in (10, 13):
            return limpio
        return None
