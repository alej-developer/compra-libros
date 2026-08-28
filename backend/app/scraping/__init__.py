# Paquete del motor de scraping

from .base import ScraperBase
from .scraper_libreria_fisica import ScraperLibreriaFisica
from .scraper_plataforma_digital import ScraperPlataformaDigital
from .scraper_segunda_mano import ScraperSegundaMano
from .filtro_autores import FiltroAutoresIndependientes
from .utilidades import (
    RotadorUserAgent,
    GestorEspera,
    ClienteHttp,
    limpiar_texto,
    extraer_precio,
)

__all__ = [
    "ScraperBase",
    "ScraperLibreriaFisica",
    "ScraperPlataformaDigital",
    "ScraperSegundaMano",
    "FiltroAutoresIndependientes",
    "RotadorUserAgent",
    "GestorEspera",
    "ClienteHttp",
    "limpiar_texto",
    "extraer_precio",
]
