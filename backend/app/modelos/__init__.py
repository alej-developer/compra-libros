# Paquete de modelos de datos para el scraping de libros

from .autor import Autor
from .libro import Libro
from .edicion import Edicion
from .filtro_scraping import FiltroScraping

__all__ = [
    "Autor",
    "Libro",
    "Edicion",
    "FiltroScraping",
]
