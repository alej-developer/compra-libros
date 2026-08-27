"""
Modelo de datos: FiltroScraping

Define los criterios de busqueda y filtraje para las operaciones de
web scraping. Permite al usuario personalizar que libros se buscan
y desde que fuentes.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class OrdenResultados(str, Enum):
    """Criterios disponibles para ordenar los resultados del scraping."""

    PRECIO_ASCENDENTE = "precio_asc"
    PRECIO_DESCENDENTE = "precio_desc"
    CALIFICACION = "calificacion"
    RELEVANCIA = "relevancia"
    FECHA_PUBLICACION = "fecha_publicacion"
    TITULO_ALFABETICO = "titulo_alfabetico"


class FiltroScraping(BaseModel):
    """
    Clase que define los filtros aplicables a una busqueda de scraping.

    Permite al usuario especificar criterios para acotar los resultados
    de la busqueda de libros en las distintas fuentes configuradas.

    Atributos:
        termino_busqueda: Texto libre para buscar (titulo, autor, ISBN, etc.).
        categoria: Categoria o genero literario para filtrar (opcional).
        precio_minimo: Precio minimo del rango de busqueda (opcional).
        precio_maximo: Precio maximo del rango de busqueda (opcional).
        idioma: Idioma deseado para los resultados (opcional).
        tiendas: Lista de tiendas especificas donde buscar (opcional).
        solo_disponibles: Si es True, excluye resultados agotados.
        orden: Criterio de ordenacion de los resultados.
        pagina: Numero de pagina para la paginacion.
        resultados_por_pagina: Cantidad de resultados por pagina.
    """

    termino_busqueda: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Texto de busqueda (titulo, autor, ISBN, palabra clave)",
        examples=["Cien anos de soledad"],
    )
    categoria: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Categoria o genero literario para filtrar",
        examples=["Novela"],
    )
    precio_minimo: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Precio minimo del rango de busqueda",
    )
    precio_maximo: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Precio maximo del rango de busqueda",
    )
    idioma: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Idioma deseado de los resultados",
        examples=["Espanol"],
    )
    tiendas: Optional[List[str]] = Field(
        default=None,
        description="Lista de tiendas especificas donde buscar",
        examples=[["Casa del Libro", "Amazon"]],
    )
    solo_disponibles: bool = Field(
        default=True,
        description="Si es True, excluye resultados agotados o descontinuados",
    )
    orden: OrdenResultados = Field(
        default=OrdenResultados.RELEVANCIA,
        description="Criterio de ordenacion de los resultados",
    )
    pagina: int = Field(
        default=1,
        ge=1,
        description="Numero de pagina para la paginacion",
    )
    resultados_por_pagina: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Cantidad de resultados por pagina (maximo 100)",
    )

    class Config:
        """Configuracion del modelo FiltroScraping."""

        json_schema_extra = {
            "example": {
                "termino_busqueda": "Gabriel Garcia Marquez",
                "categoria": "Novela",
                "precio_minimo": 5.0,
                "precio_maximo": 30.0,
                "idioma": "Espanol",
                "tiendas": ["Casa del Libro", "Amazon"],
                "solo_disponibles": True,
                "orden": "precio_asc",
                "pagina": 1,
                "resultados_por_pagina": 20,
            }
        }
