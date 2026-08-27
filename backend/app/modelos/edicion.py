"""
Modelo de datos: Edicion

Representa una edicion especifica de un libro, incluyendo formato, precio
y disponibilidad en una tienda o plataforma concreta.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from enum import Enum


class FormatoLibro(str, Enum):
    """Formatos disponibles para una edicion de libro."""

    TAPA_DURA = "tapa_dura"
    TAPA_BLANDA = "tapa_blanda"
    EBOOK = "ebook"
    AUDIOLIBRO = "audiolibro"
    BOLSILLO = "bolsillo"
    OTRO = "otro"


class EstadoDisponibilidad(str, Enum):
    """Estados posibles de disponibilidad de una edicion."""

    DISPONIBLE = "disponible"
    AGOTADO = "agotado"
    PREVENTA = "preventa"
    DESCONTINUADO = "descontinuado"
    DESCONOCIDO = "desconocido"


class Edicion(BaseModel):
    """
    Clase que representa una edicion especifica de un libro.

    Una edicion captura la informacion de una version particular del libro
    en una tienda o plataforma, permitiendo comparar precios y formatos.

    Atributos:
        isbn: Codigo ISBN de esta edicion (opcional).
        formato: Formato fisico o digital de la edicion.
        precio: Precio de venta en la moneda especificada.
        moneda: Codigo ISO de la moneda del precio.
        tienda: Nombre de la tienda o plataforma donde se encontro.
        url_compra: Enlace directo para comprar esta edicion.
        disponibilidad: Estado actual de disponibilidad.
        fecha_publicacion: Fecha de publicacion de esta edicion (opcional).
        numero_paginas: Cantidad de paginas de esta edicion (opcional).
        idioma: Idioma de esta edicion especifica (opcional).
        fecha_scraping: Fecha en que se extrajo esta informacion.
    """

    isbn: Optional[str] = Field(
        default=None,
        pattern=r"^(?:\d{10}|\d{13})$",
        description="Codigo ISBN-10 o ISBN-13 de la edicion (solo digitos)",
    )
    formato: FormatoLibro = Field(
        default=FormatoLibro.OTRO,
        description="Formato de la edicion",
    )
    precio: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Precio de venta de la edicion",
        examples=[19.99],
    )
    moneda: str = Field(
        default="EUR",
        max_length=3,
        description="Codigo ISO 4217 de la moneda",
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
        description="Enlace directo para comprar la edicion",
    )
    disponibilidad: EstadoDisponibilidad = Field(
        default=EstadoDisponibilidad.DESCONOCIDO,
        description="Estado actual de disponibilidad",
    )
    fecha_publicacion: Optional[date] = Field(
        default=None,
        description="Fecha de publicacion de la edicion",
    )
    numero_paginas: Optional[int] = Field(
        default=None,
        gt=0,
        description="Cantidad de paginas de la edicion",
    )
    idioma: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Idioma de la edicion",
        examples=["Espanol"],
    )
    fecha_scraping: Optional[date] = Field(
        default=None,
        description="Fecha en que se extrajo la informacion",
    )

    class Config:
        """Configuracion del modelo Edicion."""

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
