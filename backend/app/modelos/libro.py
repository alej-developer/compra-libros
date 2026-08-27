"""
Modelo de datos: Libro

Representa un libro obtenido mediante web scraping, con toda la informacion
relevante para la busqueda y comparacion de precios.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from .autor import Autor


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
            }
        }
