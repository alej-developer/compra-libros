"""
Modelo de datos: ResultadoBusqueda

Encapsula los resultados de una operación de scraping, incluyendo
los libros encontrados, metadatos de la búsqueda y estadísticas.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from .libro import Libro
from .edicion import Edicion


class LibroConEdiciones(BaseModel):
    """
    Asocia un libro con sus ediciones disponibles en distintas tiendas.

    Atributos:
        libro: Datos del libro.
        ediciones: Lista de ediciones disponibles en diferentes tiendas.
        numero_resenas: Cantidad de reseñas (para el algoritmo de filtrado).
        es_autor_independiente: Indica si el autor se considera independiente.
        puntuacion_independencia: Puntuación calculada por el algoritmo de filtrado.
    """

    libro: Libro
    ediciones: List[Edicion] = Field(default_factory=list)
    numero_resenas: Optional[int] = Field(
        default=None,
        ge=0,
        description="Cantidad de reseñas del libro (para algoritmo de filtrado)",
    )
    es_autor_independiente: bool = Field(
        default=False,
        description="Indica si el autor se considera independiente o poco conocido",
    )
    puntuacion_independencia: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Puntuación del algoritmo de filtrado (0-100, mayor = más independiente)",
    )

    @property
    def precio_minimo(self) -> Optional[float]:
        """Retorna el precio más bajo entre todas las ediciones disponibles."""
        precios = [e.precio for e in self.ediciones if e.precio is not None]
        return min(precios) if precios else None

    class Config:
        """Configuración del modelo."""

        json_schema_extra = {
            "example": {
                "libro": {
                    "titulo": "El jardín olvidado",
                    "autores": [{"nombre": "María López"}],
                    "editorial": "Ediciones Independientes",
                },
                "ediciones": [
                    {
                        "tienda": "Casa del Libro",
                        "precio": 8.95,
                        "moneda": "EUR",
                        "formato": "tapa_blanda",
                        "disponibilidad": "disponible",
                    }
                ],
                "numero_resenas": 12,
                "es_autor_independiente": True,
                "puntuacion_independencia": 82.5,
            }
        }


class ResultadoBusqueda(BaseModel):
    """
    Encapsula los resultados completos de una operación de scraping.

    Atributos:
        libros: Lista de libros con sus ediciones.
        total_encontrados: Número total de resultados encontrados.
        pagina_actual: Página actual de resultados.
        total_paginas: Número total de páginas disponibles.
        termino_busqueda: Término de búsqueda utilizado.
        fuentes_consultadas: Lista de fuentes que se consultaron.
        tiempo_ejecucion_segundos: Tiempo total de la operación en segundos.
        errores: Lista de errores ocurridos durante la búsqueda (opcional).
    """

    libros: List[LibroConEdiciones] = Field(default_factory=list)
    total_encontrados: int = Field(
        default=0,
        ge=0,
        description="Número total de resultados encontrados",
    )
    pagina_actual: int = Field(default=1, ge=1)
    total_paginas: int = Field(default=1, ge=1)
    termino_busqueda: str = Field(default="")
    fuentes_consultadas: List[str] = Field(default_factory=list)
    tiempo_ejecucion_segundos: float = Field(
        default=0.0,
        ge=0.0,
        description="Tiempo total de ejecución en segundos",
    )
    errores: List[str] = Field(
        default_factory=list,
        description="Errores ocurridos durante la búsqueda",
    )
    fecha_consulta: datetime = Field(
        default_factory=datetime.now,
        description="Fecha y hora de la consulta",
    )

    class Config:
        """Configuración del modelo."""

        json_schema_extra = {
            "example": {
                "total_encontrados": 15,
                "pagina_actual": 1,
                "total_paginas": 2,
                "termino_busqueda": "novela independiente",
                "fuentes_consultadas": ["Casa del Libro", "Amazon Kindle"],
                "tiempo_ejecucion_segundos": 4.32,
                "errores": [],
            }
        }
