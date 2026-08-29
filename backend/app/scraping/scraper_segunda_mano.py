"""
Scraper para librerías y plataformas de libros de segunda mano.

Implementa la lógica de scraping específica para sitios web dedicados
a la venta de libros usados, de segunda mano y entre particulares.
Extrae: título, autor, precio, estado físico, url de compra real,
editorial y formato.

Todos los libros extraídos por este scraper se marcan automáticamente
con estado "De segunda mano".
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


logger = logging.getLogger("scraping.segunda_mano")


class ScraperSegundaMano(ScraperBase):
    """
    Scraper especializado en plataformas de libros de segunda mano.

    Implementa la extraccion de datos de sitios web dedicados a la compraventa
    de libros usados como Iberlibro, Todocoleccion, Uniliber, etc.

    Todos los libros extraidos por esta clase se marcan automaticamente con
    el estado "De segunda mano". Los libros sin un enlace de compra valido
    se descartan silenciosamente para garantizar una experiencia impecable.

    La clase utiliza selectores CSS configurables para adaptarse a cada
    plataforma de segunda mano sin modificar la logica principal.
    """

    def __init__(
        self,
        nombre_fuente: str,
        url_base: str,
        pais: str = "Espana",
        moneda: str = "EUR",
        selectores: Optional[dict] = None,
    ) -> None:
        """
        Inicializa el scraper de segunda mano.

        Parametros:
            nombre_fuente: Nombre de la plataforma de libros usados.
            url_base: URL base del sitio web.
            pais: Pais de la plataforma.
            moneda: Moneda principal de la plataforma.
            selectores: Diccionario con selectores CSS para cada campo.
                Claves esperadas:
                - 'contenedor_libro': Selector del contenedor de cada libro.
                - 'titulo': Selector del titulo.
                - 'autor': Selector del autor.
                - 'precio': Selector del precio.
                - 'editorial': Selector de la editorial.
                - 'imagen': Selector de la imagen de portada.
                - 'enlace': Selector del enlace al detalle del libro.
                - 'categoria': Selector de la categoria/genero.
                - 'isbn': Selector del ISBN.
                - 'condicion': Selector del estado fisico del ejemplar.
                - 'formato': Selector del formato.
                - 'url_busqueda': Plantilla de URL de busqueda.
                - 'url_ofertas': URL de la seccion de ofertas o precios bajos.
        """
        super().__init__(
            nombre_fuente=nombre_fuente,
            url_base=url_base,
            tipo_fuente="segunda_mano",
            pais=pais,
        )
        self._moneda = moneda
        self._selectores = selectores or self._selectores_por_defecto()

    def _selectores_por_defecto(self) -> dict:
        """
        Retorna los selectores CSS por defecto para plataformas de segunda mano.

        Estos selectores son genericos y deben personalizarse para
        cada sitio web objetivo.

        Retorna:
            Diccionario con los selectores CSS por defecto.
        """
        return {
            "contenedor_libro": (
                ".result-item, .book-item, .product-item, "
                ".listing-item, article.item"
            ),
            "titulo": "h2 a, h3 a, .titulo, .book-title, .item-title a",
            "autor": ".autor, .author, .book-author, .seller-author",
            "precio": ".precio, .price, .book-price, .item-price",
            "editorial": ".editorial, .publisher, .book-publisher",
            "imagen": "img.portada, img.book-cover, img.item-image",
            "enlace": "a.detalle, a.book-link, h2 a, h3 a, a.item-link",
            "categoria": ".categoria, .genre, .book-genre, .item-category",
            "isbn": ".isbn, [itemprop='isbn'], .book-isbn",
            "condicion": ".condicion, .condition, .book-condition, .item-condition",
            "formato": ".formato, .format, .book-format",
            "url_busqueda": "{url_base}/buscar?q={termino}&page={pagina}",
            "url_ofertas": "{url_base}/ofertas",
        }

    async def construir_url_busqueda(self, filtro: FiltroScraping) -> str:
        """
        Construye la URL de busqueda para la plataforma de segunda mano.

        Parametros:
            filtro: Criterios de busqueda.

        Retorna:
            URL completa para la busqueda.
        """
        plantilla = self._selectores.get(
            "url_busqueda",
            "{url_base}/buscar?q={termino}&page={pagina}",
        )
        url = plantilla.format(
            url_base=self._url_base,
            termino=quote_plus(filtro.termino_busqueda),
            pagina=filtro.pagina,
        )

        # Agregar filtros de precio si estan definidos
        parametros_extra = []
        if filtro.precio_minimo is not None:
            parametros_extra.append(f"precio_min={filtro.precio_minimo}")
        if filtro.precio_maximo is not None:
            parametros_extra.append(f"precio_max={filtro.precio_maximo}")

        if parametros_extra:
            separador = "&" if "?" in url else "?"
            url += separador + "&".join(parametros_extra)

        return url

    async def buscar_libros(self, filtro: FiltroScraping) -> List[Libro]:
        """
        Busca libros de segunda mano segun los filtros proporcionados.

        Parametros:
            filtro: Criterios de busqueda y filtraje.

        Retorna:
            Lista de libros usados encontrados.
        """
        url = await self.construir_url_busqueda(filtro)
        self._logger.info(
            "Buscando en %s (segunda mano): '%s'",
            self._nombre_fuente, filtro.termino_busqueda,
        )

        pagina = await self._cliente.obtener_pagina(url)
        if pagina is None:
            self._logger.warning("No se pudo acceder a %s", url)
            return []

        libros = self._parsear_resultados(pagina, filtro)
        self._logger.info(
            "Encontrados %d libros de segunda mano en %s",
            len(libros), self._nombre_fuente,
        )
        return libros

    async def extraer_detalles_libro(self, url_libro: str) -> Optional[Libro]:
        """
        Extrae los detalles completos de un libro de segunda mano desde su pagina.

        Parametros:
            url_libro: URL directa a la pagina del libro.

        Retorna:
            Libro con todos los detalles, o None si falla o el enlace no es valido.
        """
        self._logger.info("Extrayendo detalles de segunda mano de: %s", url_libro)

        pagina = await self._cliente.obtener_pagina(url_libro)
        if pagina is None:
            return None

        try:
            titulo = self._extraer_texto(
                pagina, "h1, .titulo-detalle, .product-title, .item-title"
            )
            autor = self._extraer_texto(
                pagina, ".autor-detalle, .author-detail, .book-author"
            )
            precio_texto = self._extraer_texto(pagina, self._selectores["precio"])
            editorial = self._extraer_texto(pagina, self._selectores["editorial"])
            isbn = self._extraer_texto(pagina, self._selectores["isbn"])
            categoria = self._extraer_texto(pagina, self._selectores["categoria"])

            if not titulo:
                self._logger.warning("No se encontro titulo en %s", url_libro)
                return None

            # Validar URL de compra
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
                estado=EstadoLibro.SEGUNDA_MANO,
                precio=extraer_precio(precio_texto),
                formato=FormatoLibro.TAPA_BLANDA,
                editorial=editorial,
                categorias=[categoria] if categoria else [],
                isbn=self._normalizar_isbn(isbn),
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
        precio_maximo: float = 5.0,
        limite: int = 20,
    ) -> List[Libro]:
        """
        Busca libros de segunda mano con precios muy bajos.

        En plataformas de libros usados, los precios suelen ser ya reducidos,
        por lo que este metodo filtra los mas economicos del catalogo.

        Parametros:
            precio_maximo: Precio maximo para considerar oferta (en la moneda local).
            limite: Numero maximo de resultados.

        Retorna:
            Lista de libros usados en oferta ordenados por precio ascendente.
        """
        url_ofertas = self._selectores.get("url_ofertas", "").format(
            url_base=self._url_base
        )
        self._logger.info(
            "Buscando ofertas de segunda mano en %s (precio maximo: %.2f)",
            self._nombre_fuente, precio_maximo,
        )

        pagina = await self._cliente.obtener_pagina(url_ofertas)
        if pagina is None:
            self._logger.warning(
                "No se pudo acceder a ofertas en %s", self._nombre_fuente
            )
            return []

        filtro_ofertas = FiltroScraping(
            termino_busqueda="ofertas segunda mano",
            precio_maximo=precio_maximo,
            resultados_por_pagina=limite,
        )

        libros = self._parsear_resultados(pagina, filtro_ofertas)
        return libros[:limite]

    # -- Metodos internos de parseo --

    def _parsear_resultados(
        self,
        pagina: BeautifulSoup,
        filtro: FiltroScraping,
    ) -> List[Libro]:
        """
        Parsea la pagina de resultados y extrae la lista de libros usados.

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
                libro = self._parsear_contenedor_segunda_mano(contenedor)
                if libro and self._cumple_filtros(libro, filtro):
                    libros.append(libro)
            except Exception as error:
                self._logger.debug(
                    "Error al parsear libro de segunda mano: %s", str(error)
                )
                continue

        return libros

    def _parsear_contenedor_segunda_mano(
        self,
        contenedor: BeautifulSoup,
    ) -> Optional[Libro]:
        """
        Extrae los datos de un libro de segunda mano desde su contenedor HTML.

        Descarta silenciosamente los libros que no tengan un enlace
        valido (href real que apunte a una URL absoluta).

        Parametros:
            contenedor: Elemento HTML que contiene los datos del libro.

        Retorna:
            Libro extraido con estado "De segunda mano", o None si no se
            pudieron obtener los datos minimos o el enlace no es valido.
        """
        titulo = self._extraer_texto(contenedor, self._selectores["titulo"])
        if not titulo:
            return None

        autor = self._extraer_texto(contenedor, self._selectores["autor"])
        precio_texto = self._extraer_texto(contenedor, self._selectores["precio"])
        editorial = self._extraer_texto(contenedor, self._selectores["editorial"])
        categoria = self._extraer_texto(contenedor, self._selectores["categoria"])
        formato_texto = self._extraer_texto(contenedor, self._selectores["formato"])

        precio = extraer_precio(precio_texto)

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
                "Descartado libro de segunda mano '%s': sin enlace de compra valido",
                titulo,
            )
            return None

        # Extraer imagen
        imagen = contenedor.select_one(self._selectores["imagen"])
        imagen_url = None
        if imagen:
            imagen_url = imagen.get("src") or imagen.get("data-src")

        # Extraer ISBN si esta disponible
        isbn_texto = self._extraer_texto(contenedor, self._selectores["isbn"])
        isbn = self._normalizar_isbn(isbn_texto)

        return self._crear_libro(
            titulo=titulo,
            nombre_autor=autor or "Autor desconocido",
            url_compra=url_compra,
            estado=EstadoLibro.SEGUNDA_MANO,
            precio=precio,
            formato=formato,
            editorial=editorial,
            categorias=[categoria] if categoria else [],
            isbn=isbn,
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
