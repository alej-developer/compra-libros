"""
Clase abstracta base para los scrapers de librerias.

Define la interfaz comun que deben implementar todos los scrapers del sistema.
Proporciona la infraestructura compartida para realizar peticiones HTTP seguras,
rotacion de User-Agents y tiempos de espera aleatorios.
"""

from abc import ABC, abstractmethod
import logging
from typing import List, Optional
from datetime import date
from urllib.parse import urljoin

from app.modelos import Libro, Autor, Edicion, FiltroScraping
from app.modelos.libro import EstadoLibro
from app.modelos.edicion import FormatoLibro, EstadoDisponibilidad
from app.scraping.utilidades import (
    ClienteHttp,
    RotadorUserAgent,
    GestorEspera,
    limpiar_texto,
)


class ScraperBase(ABC):
    """
    Clase abstracta base para todos los scrapers de librerias.

    Define la interfaz obligatoria que cada scraper concreto debe implementar,
    y proporciona la infraestructura comun de seguridad y privacidad:
    - Rotacion automatica de User-Agents.
    - Tiempos de espera aleatorios entre peticiones.
    - Cliente HTTP con reintentos y manejo de errores.
    - Registro de eventos (logging) por fuente.

    No se almacena ni se rastrea ningun dato de los usuarios del sistema.

    Atributos protegidos:
        _nombre_fuente: Nombre identificador de la fuente de datos.
        _url_base: URL raiz del sitio web a scrapear.
        _tipo_fuente: Tipo de fuente ('fisica', 'digital' o 'segunda_mano').
        _pais: Pais de origen de la tienda.
        _cliente: Cliente HTTP con medidas de seguridad.
        _logger: Logger especifico para esta fuente.
    """

    def __init__(
        self,
        nombre_fuente: str,
        url_base: str,
        tipo_fuente: str,
        pais: str = "Desconocido",
    ) -> None:
        """
        Inicializa el scraper base con la configuracion de la fuente.

        Parametros:
            nombre_fuente: Nombre identificador de la fuente.
            url_base: URL raiz del sitio web objetivo.
            tipo_fuente: 'fisica' para librerias fisicas, 'digital' para plataformas digitales,
                         'segunda_mano' para librerias de libros usados.
            pais: Pais de origen de la tienda.
        """
        self._nombre_fuente = nombre_fuente
        self._url_base = url_base.rstrip("/")
        self._tipo_fuente = tipo_fuente
        self._pais = pais
        self._cliente = ClienteHttp(
            rotador_ua=RotadorUserAgent(),
            gestor_espera=GestorEspera(),
        )
        self._logger = logging.getLogger(f"scraping.{nombre_fuente}")

    # -- Propiedades de solo lectura --

    @property
    def nombre_fuente(self) -> str:
        """Nombre identificador de la fuente de datos."""
        return self._nombre_fuente

    @property
    def url_base(self) -> str:
        """URL raiz del sitio web objetivo."""
        return self._url_base

    @property
    def tipo_fuente(self) -> str:
        """Tipo de fuente: 'fisica', 'digital' o 'segunda_mano'."""
        return self._tipo_fuente

    @property
    def pais(self) -> str:
        """Pais de origen de la tienda."""
        return self._pais

    # -- Metodos abstractos (interfaz obligatoria) --

    @abstractmethod
    async def buscar_libros(self, filtro: FiltroScraping) -> List[Libro]:
        """
        Busca libros segun los filtros proporcionados.

        Cada scraper concreto debe implementar la logica de busqueda
        especifica para su sitio web objetivo.

        Parametros:
            filtro: Criterios de busqueda y filtraje.

        Retorna:
            Lista de libros encontrados que coinciden con los filtros.
        """
        ...

    @abstractmethod
    async def extraer_detalles_libro(self, url_libro: str) -> Optional[Libro]:
        """
        Extrae los detalles completos de un libro dado su URL.

        Parametros:
            url_libro: URL directa a la pagina del libro.

        Retorna:
            Libro con todos los detalles extraidos, o None si falla.
        """
        ...

    @abstractmethod
    async def obtener_ofertas(
        self,
        precio_maximo: float = 10.0,
        limite: int = 20,
    ) -> List[Libro]:
        """
        Busca libros con precios muy bajos (ofertas, descuentos, liquidaciones).

        Cada scraper debe implementar la logica especifica para encontrar
        libros con precios reducidos en su plataforma.

        Parametros:
            precio_maximo: Precio maximo en la moneda local para considerar oferta.
            limite: Numero maximo de resultados a retornar.

        Retorna:
            Lista de libros en oferta o con precios muy bajos.
        """
        ...

    @abstractmethod
    async def construir_url_busqueda(self, filtro: FiltroScraping) -> str:
        """
        Construye la URL de busqueda especifica para esta fuente.

        Parametros:
            filtro: Criterios de busqueda.

        Retorna:
            URL completa para realizar la busqueda.
        """
        ...

    # -- Metodos protegidos compartidos --

    def _construir_url_absoluta(self, href: Optional[str]) -> Optional[str]:
        """
        Convierte una URL relativa en absoluta usando la URL base del scraper.

        Si la URL ya es absoluta (comienza con http:// o https://), se retorna
        tal cual. Si es relativa, se concatena con la URL base del scraper.

        Parametros:
            href: URL extraida del atributo href de un enlace HTML.

        Retorna:
            URL absoluta completa, o None si href es None o vacio.
        """
        if not href or not href.strip():
            return None
        href = href.strip()
        if href.startswith(("http://", "https://")):
            return href
        return urljoin(self._url_base + "/", href.lstrip("/"))

    def _validar_url_compra(self, url: Optional[str]) -> bool:
        """
        Verifica si una URL de compra es valida para ser incluida en los resultados.

        Una URL se considera valida si no es None y comienza con http:// o https://.

        Parametros:
            url: URL a validar.

        Retorna:
            True si la URL es valida, False en caso contrario.
        """
        if not url:
            return False
        return url.startswith(("http://", "https://"))

    def _crear_libro(
        self,
        titulo: str,
        nombre_autor: str,
        url_compra: str,
        estado: EstadoLibro = EstadoLibro.NUEVO,
        precio: Optional[float] = None,
        formato: FormatoLibro = FormatoLibro.OTRO,
        editorial: Optional[str] = None,
        categorias: Optional[List[str]] = None,
        isbn: Optional[str] = None,
        imagen_url: Optional[str] = None,
        url_fuente: Optional[str] = None,
        idioma: Optional[str] = None,
        calificacion: Optional[float] = None,
        numero_resenas: Optional[int] = None,
    ) -> Libro:
        """
        Metodo auxiliar para crear un objeto Libro con datos normalizados.

        Centraliza la creacion de libros para garantizar que todos los
        scrapers produzcan objetos consistentes.

        Parametros:
            titulo: Titulo del libro.
            nombre_autor: Nombre del autor.
            url_compra: Enlace directo real para adquirir el libro.
            estado: Condicion fisica del libro (Nuevo o De segunda mano).
            precio: Precio del libro (opcional).
            formato: Formato del libro.
            editorial: Nombre de la editorial (opcional).
            categorias: Lista de categorias/generos (opcional).
            isbn: Codigo ISBN (opcional).
            imagen_url: URL de la imagen de portada (opcional).
            url_fuente: URL original del libro (opcional).
            idioma: Idioma del libro (opcional).
            calificacion: Puntuacion del libro (opcional).
            numero_resenas: Cantidad de resenas (opcional, para filtrado).

        Retorna:
            Instancia de Libro con los datos proporcionados.
        """
        autor = Autor(
            nombre=limpiar_texto(nombre_autor) or "Autor desconocido",
        )

        libro = Libro(
            titulo=limpiar_texto(titulo) or "Sin titulo",
            autores=[autor],
            isbn=isbn,
            editorial=limpiar_texto(editorial),
            categorias=categorias or [],
            imagen_url=imagen_url,
            url_fuente=url_fuente,
            idioma=idioma,
            calificacion=calificacion,
            url_compra=url_compra,
            estado=estado,
        )

        return libro

    def _crear_edicion(
        self,
        tienda: str,
        precio: Optional[float] = None,
        moneda: str = "EUR",
        formato: FormatoLibro = FormatoLibro.OTRO,
        url_compra: Optional[str] = None,
        disponibilidad: EstadoDisponibilidad = EstadoDisponibilidad.DESCONOCIDO,
        isbn: Optional[str] = None,
        numero_paginas: Optional[int] = None,
        idioma: Optional[str] = None,
    ) -> Edicion:
        """
        Metodo auxiliar para crear un objeto Edicion con datos normalizados.

        Parametros:
            tienda: Nombre de la tienda.
            precio: Precio de la edicion (opcional).
            moneda: Codigo ISO de la moneda.
            formato: Formato de la edicion.
            url_compra: URL para comprar (opcional).
            disponibilidad: Estado de disponibilidad.
            isbn: Codigo ISBN de la edicion (opcional).
            numero_paginas: Cantidad de paginas (opcional).
            idioma: Idioma de la edicion (opcional).

        Retorna:
            Instancia de Edicion con los datos proporcionados.
        """
        return Edicion(
            tienda=tienda,
            precio=precio,
            moneda=moneda,
            formato=formato,
            url_compra=url_compra,
            disponibilidad=disponibilidad,
            isbn=isbn,
            numero_paginas=numero_paginas,
            idioma=idioma,
            fecha_scraping=date.today(),
        )

    def __repr__(self) -> str:
        """Representacion en cadena del scraper."""
        return (
            f"{self.__class__.__name__}("
            f"fuente='{self._nombre_fuente}', "
            f"tipo='{self._tipo_fuente}', "
            f"pais='{self._pais}')"
        )

