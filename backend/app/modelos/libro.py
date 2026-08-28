"""
Modelo de datos: Libro

Representa un libro obtenido mediante web scraping, con toda la informacion
relevante para la busqueda y comparacion de precios.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum
from .autor import Autor


class EstadoLibro(str, Enum):
    """Estados posibles del libro segun su condicion fisica."""

    NUEVO = "Nuevo"
    SEGUNDA_MANO = "De segunda mano"


class Libro(BaseModel):
    """
    Clase que representa un libro con sus datos principales.

    Atributos:
        titulo: Titulo completo del libro.
        autores: Lista de autores del libro.
        isbn: Codigo ISBN del libro (opcional, formato ISBN-10 o ISBN-13).
        editorial: Nombre de la editorial (opcional).
        descripcion: Sinopsis o descripcion del libro (opcional).
        imagen_url: Enlace a la imagen de portada del libro (opcional).
        categorias: Lista de categorias o generos del libro.
        idioma: Idioma principal del libro (opcional).
        calificacion: Puntuacion promedio del libro (opcional, de 0.0 a 5.0).
        url_fuente: Enlace a la pagina original de donde se extrajo el libro.
        url_compra: Enlace directo real para adquirir el libro.
        estado: Condicion fisica del libro (Nuevo o De segunda mano).
    """

    titulo: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Titulo completo del libro",
        examples=["Cien anos de soledad"],
    )
    autores: List[Autor] = Field(
        default_factory=list,
        description="Lista de autores del libro",
    )
    isbn: Optional[str] = Field(
        default=None,
        pattern=r"^(?:\d{10}|\d{13})$",
        description="Codigo ISBN-10 o ISBN-13 del libro (solo digitos)",
        examples=["9780307474728"],
    )
    editorial: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Nombre de la editorial",
        examples=["Editorial Sudamericana"],
    )
    descripcion: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Sinopsis o descripcion del libro",
    )
    imagen_url: Optional[str] = Field(
        default=None,
        description="Enlace a la imagen de portada",
    )
    categorias: List[str] = Field(
        default_factory=list,
        description="Lista de categorias o generos literarios",
        examples=[["Novela", "Realismo magico"]],
    )
    idioma: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Idioma principal del libro",
        examples=["Espanol"],
    )
    calificacion: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=5.0,
        description="Puntuacion promedio del libro (0.0 a 5.0)",
    )
    url_fuente: Optional[str] = Field(
        default=None,
        description="Enlace a la pagina original de donde se extrajo el libro",
    )
    url_compra: str = Field(
        ...,
        min_length=1,
        description="Enlace directo real para adquirir el libro",
        examples=["https://www.casadellibro.com/libro/cien-anos-de-soledad/123"],
    )
    estado: EstadoLibro = Field(
        default=EstadoLibro.NUEVO,
        description="Condicion fisica del libro: Nuevo o De segunda mano",
    )

    @field_validator("url_compra")
    @classmethod
    def validar_url_compra(cls, valor: str) -> str:
        """Valida que la URL de compra sea una direccion HTTP absoluta."""
        if not valor.startswith(("http://", "https://")):
            raise ValueError(
                "La URL de compra debe ser una direccion absoluta que comience con http:// o https://"
            )
        return valor

    class Config:
        """Configuracion del modelo Libro."""

        json_schema_extra = {
            "example": {
                "titulo": "Cien anos de soledad",
                "autores": [
                    {
                        "nombre": "Gabriel Garcia Marquez",
                        "nacionalidad": "Colombia",
                    }
                ],
                "isbn": "9780307474728",
                "editorial": "Editorial Sudamericana",
                "descripcion": "La historia de la familia Buendia en Macondo.",
                "categorias": ["Novela", "Realismo magico"],
                "idioma": "Espanol",
                "calificacion": 4.8,
                "url_fuente": "https://ejemplo.com/libros/cien-anos-de-soledad",
                "url_compra": "https://www.casadellibro.com/libro/cien-anos-de-soledad/123",
                "estado": "Nuevo",
            }
        }
