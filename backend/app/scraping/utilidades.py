"""
Modulo de utilidades para el motor de scraping.

Proporciona herramientas de seguridad y privacidad: rotacion de User-Agents,
gestion de tiempos de espera aleatorios, y manejo centralizado de excepciones.
No se almacena ni se rastrea ningun dato de los usuarios.
"""

import random
import asyncio
import logging
import time
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.configuracion import configuracion


# -- Registro de eventos (logger) del modulo --
logger = logging.getLogger("scraping.utilidades")


# -- Lista de User-Agents para rotacion --
# Se incluyen agentes de navegadores reales y actualizados para evitar
# deteccion como bot. No se transmite informacion identificable del usuario.
_LISTA_USER_AGENTS = [
    # Chrome en Windows
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0.0.0 Safari/537.36"
    ),
    # Chrome en macOS
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    # Firefox en Windows
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) "
        "Gecko/20100101 Firefox/121.0"
    ),
    # Firefox en Linux
    (
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) "
        "Gecko/20100101 Firefox/121.0"
    ),
    # Safari en macOS
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.2 Safari/605.1.15"
    ),
    # Edge en Windows
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    ),
    # Chrome en Android
    (
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
]


class RotadorUserAgent:
    """
    Gestiona la rotacion de cadenas User-Agent para las peticiones HTTP.

    Selecciona aleatoriamente un User-Agent de la lista predefinida en cada
    peticion, reduciendo la probabilidad de deteccion como bot.
    No almacena informacion sobre el usuario ni sobre las peticiones realizadas.
    """

    def __init__(self) -> None:
        """Inicializa el rotador con la lista predefinida de User-Agents."""
        self._agentes = list(_LISTA_USER_AGENTS)
        self._indice_actual = 0
        random.shuffle(self._agentes)

    def obtener_siguiente(self) -> str:
        """
        Retorna el siguiente User-Agent de la lista rotada.

        Retorna:
            str: Cadena User-Agent seleccionada.
        """
        agente = self._agentes[self._indice_actual]
        self._indice_actual = (self._indice_actual + 1) % len(self._agentes)
        return agente

    def obtener_aleatorio(self) -> str:
        """
        Retorna un User-Agent aleatorio de la lista.

        Retorna:
            str: Cadena User-Agent seleccionada al azar.
        """
        return random.choice(self._agentes)


class GestorEspera:
    """
    Gestiona los tiempos de espera entre peticiones HTTP.

    Implementa pausas aleatorias para no saturar los servidores objetivo
    y simular un comportamiento de navegacion humano. Los tiempos son
    configurables y se aplican de forma automatica antes de cada peticion.
    """

    def __init__(
        self,
        espera_minima: float = 1.0,
        espera_maxima: float = 4.0,
        espera_entre_paginas: float = 2.0,
    ) -> None:
        """
        Inicializa el gestor de espera con los tiempos configurados.

        Parametros:
            espera_minima: Tiempo minimo de espera en segundos.
            espera_maxima: Tiempo maximo de espera en segundos.
            espera_entre_paginas: Tiempo adicional entre paginas consecutivas.
        """
        self._espera_minima = espera_minima
        self._espera_maxima = espera_maxima
        self._espera_entre_paginas = espera_entre_paginas
        self._ultima_peticion: float = 0.0

    async def esperar(self) -> None:
        """
        Pausa la ejecucion un tiempo aleatorio antes de la siguiente peticion.

        La pausa se calcula entre espera_minima y espera_maxima, con una
        variacion adicional para mayor naturalidad.
        """
        espera = random.uniform(self._espera_minima, self._espera_maxima)

        # Agregar una variacion extra del 20% para mayor impredecibilidad
        variacion = espera * random.uniform(-0.2, 0.2)
        espera_final = max(0.5, espera + variacion)

        logger.debug("Esperando %.2f segundos antes de la siguiente peticion", espera_final)
        await asyncio.sleep(espera_final)
        self._ultima_peticion = time.time()

    async def esperar_entre_paginas(self) -> None:
        """
        Pausa mas prolongada entre paginas de resultados.

        Se utiliza una espera mayor para no generar patrones de trafico
        sospechosos al navegar multiples paginas de resultados.
        """
        espera = self._espera_entre_paginas + random.uniform(0.5, 2.0)
        logger.debug("Esperando %.2f segundos entre paginas", espera)
        await asyncio.sleep(espera)
        self._ultima_peticion = time.time()


class ClienteHttp:
    """
    Cliente HTTP con medidas de seguridad integradas.

    Encapsula las peticiones HTTP con rotacion de User-Agent, tiempos
    de espera aleatorios, reintentos automaticos y manejo de errores.
    No almacena cookies de seguimiento ni datos identificables del usuario.
    """

    def __init__(
        self,
        rotador_ua: Optional[RotadorUserAgent] = None,
        gestor_espera: Optional[GestorEspera] = None,
        maximo_reintentos: int = 3,
        tiempo_espera: int = 30,
    ) -> None:
        """
        Inicializa el cliente HTTP con las medidas de seguridad.

        Parametros:
            rotador_ua: Instancia del rotador de User-Agents.
            gestor_espera: Instancia del gestor de tiempos de espera.
            maximo_reintentos: Numero maximo de reintentos ante fallos.
            tiempo_espera: Tiempo maximo de espera por peticion en segundos.
        """
        self._rotador_ua = rotador_ua or RotadorUserAgent()
        self._gestor_espera = gestor_espera or GestorEspera()
        self._maximo_reintentos = maximo_reintentos
        self._tiempo_espera = tiempo_espera

    async def obtener_pagina(
        self,
        url: str,
        parametros: Optional[dict] = None,
    ) -> Optional[BeautifulSoup]:
        """
        Realiza una peticion GET y retorna el contenido parseado como HTML.

        Aplica automaticamente rotacion de User-Agent, espera aleatoria
        antes de la peticion, y reintentos en caso de error.

        Parametros:
            url: URL objetivo de la peticion.
            parametros: Parametros de consulta opcionales.

        Retorna:
            BeautifulSoup con el HTML parseado, o None si falla.
        """
        await self._gestor_espera.esperar()

        cabeceras = {
            "User-Agent": self._rotador_ua.obtener_siguiente(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "DNT": "1",  # Do Not Track: respetamos la privacidad
        }

        for intento in range(1, self._maximo_reintentos + 1):
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=self._tiempo_espera,
                ) as cliente:
                    respuesta = await cliente.get(
                        url,
                        headers=cabeceras,
                        params=parametros,
                    )
                    respuesta.raise_for_status()
                    return BeautifulSoup(respuesta.text, "lxml")

            except httpx.TimeoutException:
                logger.warning(
                    "Tiempo de espera agotado en %s (intento %d/%d)",
                    url, intento, self._maximo_reintentos,
                )
            except httpx.HTTPStatusError as error:
                codigo = error.response.status_code
                logger.warning(
                    "Error HTTP %d en %s (intento %d/%d)",
                    codigo, url, intento, self._maximo_reintentos,
                )
                # Si es un error 429 (demasiadas peticiones), esperar mas
                if codigo == 429:
                    espera_extra = random.uniform(10.0, 30.0)
                    logger.info("Detectado limite de tasa. Esperando %.1f segundos", espera_extra)
                    await asyncio.sleep(espera_extra)
                # Si es un error 403 o 401, rotar User-Agent y reintentar
                elif codigo in (401, 403):
                    cabeceras["User-Agent"] = self._rotador_ua.obtener_aleatorio()
                # Si es un error de servidor (5xx), reintentar
                elif codigo >= 500:
                    await asyncio.sleep(random.uniform(2.0, 5.0))
                else:
                    # Para otros errores de cliente (4xx), no reintentar
                    logger.error("Error de cliente %d en %s. No se reintenta.", codigo, url)
                    return None
            except httpx.RequestError as error:
                logger.warning(
                    "Error de conexion en %s: %s (intento %d/%d)",
                    url, str(error), intento, self._maximo_reintentos,
                )
                await asyncio.sleep(random.uniform(1.0, 3.0))
            except Exception as error:
                logger.error(
                    "Error inesperado al acceder a %s: %s",
                    url, str(error),
                )
                return None

        logger.error("Agotados los %d reintentos para %s", self._maximo_reintentos, url)
        return None


def limpiar_texto(texto: Optional[str]) -> Optional[str]:
    """
    Limpia y normaliza un texto extraido de HTML.

    Elimina espacios en blanco excesivos, saltos de linea innecesarios
    y caracteres no imprimibles.

    Parametros:
        texto: Texto a limpiar.

    Retorna:
        Texto limpio, o None si la entrada es None o vacia.
    """
    if not texto:
        return None
    limpio = " ".join(texto.split())
    return limpio.strip() if limpio else None


def extraer_precio(texto_precio: Optional[str]) -> Optional[float]:
    """
    Extrae un valor numerico de precio desde un texto con formato variable.

    Maneja formatos comunes como: "12,99 EUR", "$19.99", "15.50", "9,90".

    Parametros:
        texto_precio: Texto que contiene el precio.

    Retorna:
        Valor numerico del precio, o None si no se puede extraer.
    """
    if not texto_precio:
        return None

    import re

    # Eliminar simbolos de moneda y espacios
    limpio = re.sub(r"[^\d.,]", "", texto_precio.strip())

    if not limpio:
        return None

    try:
        # Si contiene coma y punto, determinar cual es el separador decimal
        if "," in limpio and "." in limpio:
            # Formato europeo: 1.234,56
            if limpio.rindex(",") > limpio.rindex("."):
                limpio = limpio.replace(".", "").replace(",", ".")
            # Formato anglosajón: 1,234.56
            else:
                limpio = limpio.replace(",", "")
        elif "," in limpio:
            # Solo coma: asumir separador decimal europeo
            limpio = limpio.replace(",", ".")

        return float(limpio)
    except (ValueError, AttributeError):
        logger.warning("No se pudo extraer precio de: '%s'", texto_precio)
        return None
