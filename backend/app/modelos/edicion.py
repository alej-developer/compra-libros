"""
Modelo de datos: Edición

Representa una edición específica de un libro, incluyendo formato, precio
y disponibilidad en una tienda o plataforma concreta.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from enum import Enum


class FormatoLibro(str, Enum):
    """Formatos disponibles para una edición de libro."""

    TAPA_DURA = "tapa_dura"
    TAPA_BLANDA = "tapa_blanda"
    EBOOK = "ebook"
    AUDIOLIBRO = "audiolibro"
    BOLSILLO = "bolsillo"
    OTRO = "otro"


class EstadoDisponibilidad(str, Enum):
    """Estados posibles de disponibilidad de una edición."""

    DISPONIBLE = "disponible"
    AGOTADO = "agotado"
    PREVENTA = "preventa"
    DESCONTINUADO = "descontinuado"
    DESCONOCIDO = "desconocido"


class Edicion(BaseModel):
    """
    Clase que representa una edición específica de un libro.

    Una edición captura la información de una versión particular del libro
    en una tienda o plataforma, permitiendo comparar precios y formatos.

    Atributos:
        isbn: Código ISBN de esta edición (opcional).
        formato: Formato físico o digital de la edición.
        precio: Precio de venta en la moneda especificada.
        moneda: Código ISO de la moneda del precio.
        tienda: Nombre de la tienda o plataforma donde se encontró.
        url_compra: Enlace directo para comprar esta edición.
        disponibilidad: Estado actual de disponibilidad.
        fecha_publicacion: Fecha de publicación de esta edición (opcional).
        numero_paginas: Cantidad de páginas de esta edición (opcional).
        idioma: Idioma de esta edición específica (opcional).
        fecha_scraping: Fecha en que se extrajo esta información.
    """

    isbn: Optional[str] = Field(
        default=None,
        pattern=r"^(?:\d{10}|\d{13})$",
        description="Código ISBN-10 o ISBN-13 de la edición (solo dígitos)",
    )
    formato: FormatoLibro = Field(
        default=FormatoLibro.OTRO,
        description="Formato de la edición",
    )
    precio: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Precio de venta de la edición",
        examples=[19.99],
    )
    moneda: str = Field(
        default="EUR",
        max_length=3,
        description="Código ISO 4217 de la moneda",
        examples=["EUR", "USD", "MXN"],
    )
    tienda: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre de la tienda o plataforma",
        examples=["Casa del Libro", "Amazon"],
    )
    url_compra: Optional[str] = Field(
        default=None,
        description="Enlace directo para comprar la edición",
    )
    disponibilidad: EstadoDisponibilidad = Field(
        default=EstadoDisponibilidad.DESCONOCIDO,
        description="Estado actual de disponibilidad",
    )
    fecha_publicacion: Optional[date] = Field(
        default=None,
        description="Fecha de publicación de la edición",
    )
    numero_paginas: Optional[int] = Field(
        default=None,
        gt=0,
        description="Cantidad de páginas de la edición",
    )
    idioma: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Idioma de la edición",
        examples=["Español"],
    )
    fecha_scraping: Optional[date] = Field(
        default=None,
        description="Fecha en que se extrajo la información",
    )

    class Config:
        """Configuración del modelo Edicion."""

        json_schema_extra = {
            "example": {
                "isbn": "9780307474728",
                "formato": "tapa_blanda",
                "precio": 12.50,
                "moneda": "EUR",
                "tienda": "Casa del Libro",
                "url_compra": "https://ejemplo.com/comprar/cien-anos-tapa-blanda",
                "disponibilidad": "disponible",
                "fecha_publicacion": "2007-05-01",
                "numero_paginas": 432,
                "idioma": "Espanol",
                "fecha_scraping": "2026-08-27",
            }
        }
