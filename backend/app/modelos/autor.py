"""
Modelo de datos: Autor

Representa a un autor de libros con su informacion biografica basica.
Utiliza Pydantic para la validacion automatica de datos.
"""

from pydantic import BaseModel, Field
from typing import Optional


class Autor(BaseModel):
    """
    Clase que representa a un autor de libros.

    Atributos:
        nombre: Nombre completo del autor.
        nacionalidad: Pais de origen del autor (opcional).
        biografia: Resumen biografico del autor (opcional).
        url_perfil: Enlace al perfil del autor en la fuente de scraping (opcional).
    """

    nombre: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre completo del autor",
        examples=["Gabriel Garcia Marquez"],
    )
    nacionalidad: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Pais de origen del autor",
        examples=["Colombia"],
    )
    biografia: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Resumen biografico del autor",
    )
    url_perfil: Optional[str] = Field(
        default=None,
        description="Enlace al perfil del autor en la fuente original",
    )

    class Config:
        """Configuracion del modelo Autor."""

        json_schema_extra = {
            "example": {
                "nombre": "Gabriel Garcia Marquez",
                "nacionalidad": "Colombia",
                "biografia": "Escritor y periodista colombiano, premio Nobel de Literatura.",
                "url_perfil": "https://ejemplo.com/autores/garcia-marquez",
            }
        }
