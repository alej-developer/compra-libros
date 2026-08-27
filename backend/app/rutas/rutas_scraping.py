"""
Rutas (endpoints) del motor de scraping.

Define los endpoints de la API para buscar libros, obtener ofertas
y filtrar autores independientes.
"""

from fastapi import APIRouter, Query
from typing import Optional

from app.modelos import FiltroScraping
from app.modelos.resultado_busqueda import ResultadoBusqueda
from app.servicios.servicio_scraping import ServicioScraping


# -- Instancia del servicio de scraping --
_servicio = ServicioScraping()

# -- Router con prefijo /api/scraping --
router = APIRouter(
    prefix="/api/scraping",
    tags=["Scraping"],
    responses={
        500: {"description": "Error interno del servidor durante el scraping"},
    },
)


@router.get(
    "/fuentes",
    summary="Listar fuentes disponibles",
    description="Retorna la lista de scrapers registrados con su informacion.",
)
async def listar_fuentes():
    """Retorna la lista de fuentes de scraping disponibles."""
    return {
        "fuentes": _servicio.scrapers_disponibles,
        "total": len(_servicio.scrapers_disponibles),
    }


@router.post(
    "/buscar",
    response_model=ResultadoBusqueda,
    summary="Buscar libros",
    description=(
        "Busca libros en todas las fuentes registradas segun los filtros "
        "proporcionados. Ejecuta las busquedas en paralelo y consolida "
        "los resultados eliminando duplicados."
    ),
)
async def buscar_libros(filtro: FiltroScraping) -> ResultadoBusqueda:
    """
    Busca libros en todas las fuentes registradas.

    Parametros:
        filtro: Criterios de busqueda y filtraje (en el cuerpo de la peticion).

    Retorna:
        ResultadoBusqueda con los libros encontrados.
    """
    return await _servicio.buscar(filtro)


@router.get(
    "/ofertas",
    response_model=ResultadoBusqueda,
    summary="Buscar ofertas",
    description=(
        "Busca libros con precios muy bajos (ofertas, descuentos, liquidaciones) "
        "en todas las fuentes registradas."
    ),
)
async def buscar_ofertas(
    precio_maximo: float = Query(
        default=10.0,
        ge=0.0,
        description="Precio maximo para considerar oferta (en EUR)",
    ),
    limite: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Numero maximo de resultados",
    ),
) -> ResultadoBusqueda:
    """
    Busca libros en oferta en todas las fuentes.

    Parametros:
        precio_maximo: Precio maximo para considerar una oferta.
        limite: Numero maximo de resultados a retornar.

    Retorna:
        ResultadoBusqueda con los libros en oferta.
    """
    return await _servicio.buscar_ofertas(
        precio_maximo=precio_maximo,
        limite=limite,
    )


@router.post(
    "/autores-independientes",
    response_model=ResultadoBusqueda,
    summary="Buscar autores independientes",
    description=(
        "Busca libros priorizando autores poco conocidos o independientes. "
        "Utiliza un algoritmo que cruza el numero de resenas, la popularidad "
        "del sello editorial y otros indicadores para asignar una puntuacion "
        "de independencia (0-100) a cada libro."
    ),
)
async def buscar_autores_independientes(
    filtro: FiltroScraping,
    puntuacion_minima: float = Query(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Puntuacion minima de independencia (0-100)",
    ),
) -> ResultadoBusqueda:
    """
    Busca libros de autores independientes o poco conocidos.

    Parametros:
        filtro: Criterios de busqueda (en el cuerpo de la peticion).
        puntuacion_minima: Puntuacion minima de independencia.

    Retorna:
        ResultadoBusqueda con libros de autores independientes.
    """
    return await _servicio.buscar_autores_independientes(
        filtro=filtro,
        puntuacion_minima=puntuacion_minima,
    )
