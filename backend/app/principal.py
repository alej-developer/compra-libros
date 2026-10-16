"""
Servidor principal de la API de Scraping de Libros.

Punto de entrada de la aplicación FastAPI. Configura la instancia
de la aplicación, registra los middlewares de CORS y define las
rutas base del sistema.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.configuracion import configuracion


def _origenes_cors_explicitos(origenes: list[str]) -> list[str]:
    """
    Lee orígenes CORS y rechaza el comodín.

    Con ``allow_credentials=True`` no se puede aceptar ``*``: el navegador
    y el middleware acabarían reflejando cualquier origen junto con
    credenciales. Solo vale una lista de URLs concretas.

    Parámetros:
        origenes: Lista declarada en la configuración o en el entorno.

    Retorna:
        list[str]: Orígenes explícitos, sin duplicados, en el orden dado.

    Lanza:
        ValueError: Si la lista queda vacía o algún origen está vacío
        o contiene ``*``.
    """
    explicitos: list[str] = []
    vistos: set[str] = set()
    for origen in origenes:
        valor = origen.strip()
        if not valor:
            raise ValueError("El origen CORS no puede estar vacío.")
        if "*" in valor:
            raise ValueError(
                "CORS con allow_credentials=True no acepta el origen '*'. "
                "Use una lista explícita de orígenes."
            )
        if valor not in vistos:
            vistos.add(valor)
            explicitos.append(valor)
    if not explicitos:
        raise ValueError("La lista de orígenes CORS explícitos no puede estar vacía.")
    return explicitos


def crear_aplicacion() -> FastAPI:
    """
    Fábrica de la aplicación FastAPI.

    Crea y configura la instancia principal de la aplicación,
    incluyendo metadatos, middlewares y rutas.

    Retorna:
        FastAPI: Instancia configurada de la aplicación.
    """
    aplicacion = FastAPI(
        title=configuracion.nombre_app,
        version=configuracion.version_app,
        description=configuracion.descripcion_app,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # -- Configuración de CORS --
    # Con credenciales solo se admiten orígenes explícitos. El comodín '*'
    # se rechaza: no puede combinarse con allow_credentials=True.
    origenes = _origenes_cors_explicitos(list(configuracion.origenes_permitidos))
    aplicacion.add_middleware(
        CORSMiddleware,
        allow_origins=origenes,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "Accept",
            "Origin",
            "X-Requested-With",
        ],
    )

    # -- Registro de rutas --
    _registrar_rutas(aplicacion)

    return aplicacion


def _registrar_rutas(aplicacion: FastAPI) -> None:
    """
    Registra todas las rutas de la aplicación.

    Incluye las rutas base (raíz, salud) y los routers de cada módulo
    funcional (scraping, etc.).

    Parámetros:
        aplicacion: Instancia de FastAPI donde se registran las rutas.
    """
    # Registrar router del motor de scraping
    from app.rutas.rutas_scraping import router as router_scraping
    aplicacion.include_router(router_scraping)

    @aplicacion.get(
        "/",
        summary="Raíz de la API",
        description="Endpoint de bienvenida que confirma que la API está activa.",
        tags=["General"],
    )
    async def raiz():
        """Retorna un mensaje de bienvenida y el estado del servidor."""
        return {
            "mensaje": "Bienvenido a la API de Scraping de Libros",
            "version": configuracion.version_app,
            "estado": "activo",
            "documentacion": "/docs",
        }

    @aplicacion.get(
        "/salud",
        summary="Verificación de salud",
        description="Endpoint para verificar que el servidor está funcionando correctamente.",
        tags=["General"],
    )
    async def verificar_salud():
        """Retorna el estado de salud del servidor."""
        return {
            "estado": "saludable",
            "version": configuracion.version_app,
        }


# Instancia principal de la aplicacion
app = crear_aplicacion()
