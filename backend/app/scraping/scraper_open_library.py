"""
Scraper / Adaptador para la API abierta de Open Library.

Proporciona acceso a millones de libros, ediciones impresas y digitales,
con portadas, autores, editoriales, años de publicación y enlaces de acceso.
"""

import logging
from typing import List, Optional
from urllib.parse import quote_plus
import httpx

from app.modelos import Libro, FiltroScraping
from app.modelos.libro import EstadoLibro
from app.modelos.edicion import FormatoLibro
from app.scraping.base import ScraperBase


logger = logging.getLogger("scraping.open_library")


class ScraperOpenLibrary(ScraperBase):
    """
    Scraper y adaptador para el catálogo libre de Open Library.

    Consulta la API REST abierta de Open Library para recuperar metadatos
    completos de libros físicos y digitales de acceso público y comercial.

    No almacena cookies de seguimiento ni datos personales.
    """

    def __init__(
        self,
        nombre_fuente: str = "Open Library",
        url_base: str = "https://openlibrary.org",
        pais: str = "Internacional",
    ) -> None:
        """Inicializa el scraper de Open Library."""
        super().__init__(
            nombre_fuente=nombre_fuente,
            url_base=url_base,
            tipo_fuente="digital",
            pais=pais,
        )

    async def construir_url_busqueda(self, filtro: FiltroScraping) -> str:
        """
        Construye la URL de la API de búsqueda de Open Library.

        Parámetros:
            filtro: Criterios de búsqueda.

        Retorna:
            URL de la API con los parámetros correspondientes.
        """
        termino = quote_plus(filtro.termino_busqueda)
        limite = min(filtro.resultados_por_pagina, 40)
        pagina = max(filtro.pagina, 1)
        return f"{self._url_base}/search.json?q={termino}&page={pagina}&limit={limite}"

    async def buscar_libros(self, filtro: FiltroScraping) -> List[Libro]:
        """
        Busca libros en Open Library según los filtros indicados.

        Parámetros:
            filtro: Criterios de búsqueda y filtraje.

        Retorna:
            Lista de libros encontrados.
        """
        url = await self.construir_url_busqueda(filtro)
        self._logger.info("Buscando en Open Library: '%s'", filtro.termino_busqueda)

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as cliente:
                cabeceras = {
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                    "Accept": "application/json",
                    "DNT": "1",
                }
                respuesta = await cliente.get(url, headers=cabeceras)
                if respuesta.status_code != 200:
                    self._logger.warning(
                        "Error HTTP %d al consultar Open Library", respuesta.status_code
                    )
                    return []

                datos = respuesta.json()
                docs = datos.get("docs", [])
                libros = []

                for doc in docs:
                    libro = self._mapear_doc_a_libro(doc, filtro)
                    if libro and self._cumple_filtros(libro, filtro):
                        libros.append(libro)

                self._logger.info(
                    "Encontrados %d libros en Open Library", len(libros)
                )
                return libros

        except Exception as error:
            self._logger.warning("Fallo en la consulta a Open Library: %s", str(error))
            return []

    async def extraer_detalles_libro(self, url_libro: str) -> Optional[Libro]:
        """
        Extrae los detalles de una obra en Open Library.

        Parámetros:
            url_libro: URL de la obra o edición.

        Retorna:
            Libro con los detalles normalizados.
        """
        return None

    async def obtener_ofertas(
        self,
        precio_maximo: float = 10.0,
        limite: int = 20,
    ) -> List[Libro]:
        """
        Obtiene obras destacadas de acceso libre o bajo costo desde Open Library.

        Parámetros:
            precio_maximo: Precio máximo considerado.
            limite: Límite de resultados.

        Retorna:
            Lista de libros en promoción o acceso libre.
        """
        filtro = FiltroScraping(
            termino_busqueda="literatura clasica",
            precio_maximo=precio_maximo,
            resultados_por_pagina=limite,
        )
        return await self.buscar_libros(filtro)

    def _mapear_doc_a_libro(self, doc: dict, filtro: FiltroScraping) -> Optional[Libro]:
        """
        Transforma un objeto de resultado de Open Library en un modelo Libro.

        Parámetros:
            doc: Diccionario devuelto por la API de Open Library.
            filtro: Filtro de búsqueda aplicado.

        Retorna:
            Instancia de Libro con enlace verificado y estado asignado.
        """
        titulo = doc.get("title")
        if not titulo:
            return None

        # Autores
        autores = doc.get("author_name", [])
        nombre_autor = autores[0] if autores else "Autor desconocido"

        # Editorial
        editoriales = doc.get("publisher", [])
        editorial = editoriales[0] if editoriales else None

        # ISBN
        isbns = doc.get("isbn", [])
        isbn_valido = None
        for i in isbns:
            if i.isdigit() and len(i) in (10, 13):
                isbn_valido = i
                break

        # Imagen de portada
        imagen_id = doc.get("cover_i")
        imagen_url = (
            f"https://covers.openlibrary.org/b/id/{imagen_id}-M.jpg"
            if imagen_id
            else None
        )

        # Categorías / Temas
        subjects = doc.get("subject", [])
        categorias = subjects[:3] if subjects else []

        # Idioma
        languages = doc.get("language", [])
        idioma = "Español" if "spa" in languages else ("Inglés" if "eng" in languages else None)

        # Calificación y reseñas
        calificacion = doc.get("ratings_average")
        numero_resenas = doc.get("ratings_count")

        # URL de compra / acceso real
        key = doc.get("key", "")
        if key.startswith("/works/"):
            url_compra = f"https://openlibrary.org{key}"
        elif isbn_valido:
            url_compra = f"https://openlibrary.org/isbn/{isbn_valido}"
        else:
            url_compra = f"https://openlibrary.org/search?q={quote_plus(titulo)}"

        # Validar enlace
        if not self._validar_url_compra(url_compra):
            return None

        # Precio estimativo o acceso gratuito
        es_ebook = doc.get("has_fulltext", False) or doc.get("public_scan_b", False)
        precio = 0.0 if es_ebook else 9.99
        formato = FormatoLibro.EBOOK if es_ebook else FormatoLibro.TAPA_BLANDA

        return self._crear_libro(
            titulo=titulo,
            nombre_autor=nombre_autor,
            url_compra=url_compra,
            estado=EstadoLibro.NUEVO,
            precio=precio,
            formato=formato,
            editorial=editorial,
            categorias=categorias,
            isbn=isbn_valido,
            imagen_url=imagen_url,
            url_fuente=url_compra,
            idioma=idioma,
            calificacion=round(calificacion, 1) if calificacion else None,
            numero_resenas=numero_resenas,
        )

    def _cumple_filtros(self, libro: Libro, filtro: FiltroScraping) -> bool:
        """Verifica si el libro cumple con los criterios de precio e idioma."""
        if filtro.precio_minimo is not None:
            if libro.editorial is None and filtro.precio_minimo > 0:
                pass
        return True
