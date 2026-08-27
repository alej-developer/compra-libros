"""
Configuracion central de la aplicacion.

Carga las variables de entorno desde un archivo .env y define
los parametros de configuracion globales del servidor.
"""

from pydantic_settings import BaseSettings
from typing import List


class Configuracion(BaseSettings):
    """
    Clase de configuracion que centraliza todos los parametros del proyecto.

    Los valores se cargan automaticamente desde variables de entorno
    o desde un archivo .env en la raiz del backend.
    """

    # -- Servidor --
    nombre_app: str = "API de Scraping de Libros"
    version_app: str = "0.1.0"
    descripcion_app: str = (
        "API para buscar, comparar y obtener informacion de libros "
        "desde multiples tiendas en linea mediante web scraping."
    )
    modo_debug: bool = False
    host: str = "0.0.0.0"
    puerto: int = 8000

    # -- CORS --
    origenes_permitidos: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # -- Scraping --
    tiempo_espera_scraping: int = 30  # segundos
    maximo_reintentos: int = 3
    agente_usuario: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Instancia global de configuracion
configuracion = Configuracion()
