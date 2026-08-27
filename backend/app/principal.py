"""
Servidor principal de la API de Scraping de Libros.

Punto de entrada de la aplicacion FastAPI. Configura la instancia
de la aplicacion, registra los middlewares de CORS y define las
rutas base del sistema.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.configuracion import configuracion


def crear_aplicacion() -> FastAPI:
    """
    Fabrica de la aplicacion FastAPI.

    Crea y configura la instancia principal de la aplicacion,
    incluyendo metadatos, middlewares y rutas.

    Retorna:
        FastAPI: Instancia configurada de la aplicacion.
    """
    aplicacion = FastAPI(
        title=configuracion.nombre_app,
        version=configuracion.version_app,
        description=configuracion.descripcion_app,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # -- Configuracion de CORS --
    # Permite la comunicacion segura entre el frontend y el backend.
    # Los origenes permitidos se definen en la configuracion central.
    aplicacion.add_middleware(
        CORSMiddleware,
        allow_origins=configuracion.origenes_permitidos,
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
    Registra todas las rutas base de la aplicacion.

    Parametros:
        aplicacion: Instancia de FastAPI donde se registran las rutas.
    """

    @aplicacion.get(
        "/",
        summary="Raiz de la API",
        description="Endpoint de bienvenida que confirma que la API esta activa.",
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
        summary="Verificacion de salud",
        description="Endpoint para verificar que el servidor esta funcionando correctamente.",
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
