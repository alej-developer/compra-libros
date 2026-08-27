"""
Algoritmo de filtrado para detectar autores poco conocidos o independientes.

Implementa un sistema de puntuacion que cruza multiples indicadores para
determinar si un autor es independiente o poco conocido:
- Numero de resenas (menos resenas = mayor probabilidad de ser independiente).
- Popularidad del sello editorial (editoriales pequenas = autor independiente).
- Presencia en listas de bestsellers (ausencia = posible autor independiente).
"""

import logging
from typing import List, Optional, Set

from app.modelos import Libro
from app.modelos.resultado_busqueda import LibroConEdiciones


logger = logging.getLogger("scraping.filtro_autores")


# -- Editoriales conocidas como grandes sellos --
# Los libros de estas editoriales se consideran de autores establecidos.
# Esta lista se puede ampliar segun las necesidades del proyecto.
_EDITORIALES_GRANDES = {
    # Espanol
    "planeta", "alfaguara", "penguin random house", "anagrama", "tusquets",
    "seix barral", "destino", "espasa", "debolsillo", "plaza & janes",
    "grijalbo", "lumen", "salamandra", "rba", "ediciones b",
    "suma de letras", "maeva", "booket", "bruguera", "circulo de lectores",
    "santillana", "debate", "taurus", "ariel", "paidos",
    # Internacional
    "harpercollins", "simon & schuster", "hachette", "macmillan",
    "wiley", "pearson", "oxford university press", "cambridge university press",
    "scholastic", "bloomsbury", "vintage", "little brown",
    "random house", "penguin", "knopf", "doubleday",
}


class FiltroAutoresIndependientes:
    """
    Algoritmo de filtrado que prioriza autores poco conocidos o independientes.

    El sistema asigna una puntuacion de independencia (0-100) a cada libro
    basandose en multiples indicadores. Una puntuacion mas alta indica mayor
    probabilidad de que el autor sea independiente o poco conocido.

    Indicadores y pesos:
        - Numero de resenas (40%): Menos resenas = mayor puntuacion.
        - Editorial (35%): Editorial independiente = mayor puntuacion.
        - Calificacion (15%): Calificaciones atipicas (muy altas con pocas
          resenas) sugieren nicho independiente.
        - Formato (10%): Autopublicacion digital tiene mayor puntuacion.

    No se almacenan datos personales de los autores ni de los usuarios.
    """

    def __init__(
        self,
        umbral_resenas_bajo: int = 50,
        umbral_resenas_medio: int = 500,
        editoriales_grandes: Optional[Set[str]] = None,
        peso_resenas: float = 0.40,
        peso_editorial: float = 0.35,
        peso_calificacion: float = 0.15,
        peso_formato: float = 0.10,
    ) -> None:
        """
        Inicializa el filtro de autores independientes.

        Parametros:
            umbral_resenas_bajo: Resenas por debajo de este numero se
                consideran pocas (indica autor poco conocido).
            umbral_resenas_medio: Resenas por debajo de este numero se
                consideran moderadas.
            editoriales_grandes: Conjunto de nombres de editoriales grandes.
                Si no se proporciona, se usa la lista predefinida.
            peso_resenas: Peso del indicador de resenas (0.0 a 1.0).
            peso_editorial: Peso del indicador de editorial (0.0 a 1.0).
            peso_calificacion: Peso del indicador de calificacion (0.0 a 1.0).
            peso_formato: Peso del indicador de formato (0.0 a 1.0).
        """
        self._umbral_resenas_bajo = umbral_resenas_bajo
        self._umbral_resenas_medio = umbral_resenas_medio
        self._editoriales_grandes = editoriales_grandes or _EDITORIALES_GRANDES
        self._peso_resenas = peso_resenas
        self._peso_editorial = peso_editorial
        self._peso_calificacion = peso_calificacion
        self._peso_formato = peso_formato

    def filtrar_y_puntuar(
        self,
        libros: List[LibroConEdiciones],
        puntuacion_minima: float = 50.0,
    ) -> List[LibroConEdiciones]:
        """
        Filtra y puntua libros priorizando autores independientes.

        Asigna una puntuacion de independencia a cada libro y retorna
        solo aquellos que superan la puntuacion minima, ordenados de
        mayor a menor puntuacion.

        Parametros:
            libros: Lista de libros con ediciones a evaluar.
            puntuacion_minima: Puntuacion minima para incluir un libro
                en los resultados (0.0 a 100.0).

        Retorna:
            Lista de libros que superan la puntuacion minima, ordenados
            por puntuacion de independencia descendente.
        """
        libros_puntuados = []

        for libro_ediciones in libros:
            puntuacion = self.calcular_puntuacion(libro_ediciones)
            libro_ediciones.puntuacion_independencia = puntuacion
            libro_ediciones.es_autor_independiente = puntuacion >= puntuacion_minima

            if libro_ediciones.es_autor_independiente:
                libros_puntuados.append(libro_ediciones)

        # Ordenar por puntuacion descendente
        libros_puntuados.sort(
            key=lambda x: x.puntuacion_independencia,
            reverse=True,
        )

        logger.info(
            "Filtrado de autores independientes: %d/%d libros superan la puntuacion minima (%.1f)",
            len(libros_puntuados), len(libros), puntuacion_minima,
        )

        return libros_puntuados

    def calcular_puntuacion(self, libro_ediciones: LibroConEdiciones) -> float:
        """
        Calcula la puntuacion de independencia de un libro.

        Combina los indicadores de resenas, editorial, calificacion y formato
        con sus respectivos pesos para obtener una puntuacion final.

        Parametros:
            libro_ediciones: Libro con sus ediciones a evaluar.

        Retorna:
            Puntuacion de independencia (0.0 a 100.0).
        """
        puntuacion_resenas = self._puntuar_por_resenas(libro_ediciones.numero_resenas)
        puntuacion_editorial = self._puntuar_por_editorial(libro_ediciones.libro.editorial)
        puntuacion_calificacion = self._puntuar_por_calificacion(
            libro_ediciones.libro.calificacion,
            libro_ediciones.numero_resenas,
        )
        puntuacion_formato = self._puntuar_por_formato(libro_ediciones.ediciones)

        puntuacion_total = (
            puntuacion_resenas * self._peso_resenas
            + puntuacion_editorial * self._peso_editorial
            + puntuacion_calificacion * self._peso_calificacion
            + puntuacion_formato * self._peso_formato
        )

        # Normalizar a 0-100
        puntuacion_final = min(100.0, max(0.0, puntuacion_total))

        logger.debug(
            "Puntuacion para '%s': resenas=%.1f, editorial=%.1f, "
            "calificacion=%.1f, formato=%.1f -> total=%.1f",
            libro_ediciones.libro.titulo,
            puntuacion_resenas,
            puntuacion_editorial,
            puntuacion_calificacion,
            puntuacion_formato,
            puntuacion_final,
        )

        return round(puntuacion_final, 2)

    def _puntuar_por_resenas(self, numero_resenas: Optional[int]) -> float:
        """
        Calcula la puntuacion basada en el numero de resenas.

        Menos resenas = mayor puntuacion (indica autor menos conocido).
        Sin dato de resenas se asigna una puntuacion neutra.

        Parametros:
            numero_resenas: Cantidad de resenas del libro.

        Retorna:
            Puntuacion de 0.0 a 100.0.
        """
        if numero_resenas is None:
            # Sin datos, asignar puntuacion neutra-alta (probablemente poco conocido)
            return 65.0

        if numero_resenas <= 5:
            return 100.0
        elif numero_resenas <= self._umbral_resenas_bajo:
            # Escala lineal de 100 a 70
            rango = self._umbral_resenas_bajo - 5
            return 100.0 - (numero_resenas - 5) / rango * 30.0
        elif numero_resenas <= self._umbral_resenas_medio:
            # Escala lineal de 70 a 30
            rango = self._umbral_resenas_medio - self._umbral_resenas_bajo
            return 70.0 - (numero_resenas - self._umbral_resenas_bajo) / rango * 40.0
        else:
            # Mas de 500 resenas: autor probablemente conocido
            # Decae rapidamente hacia 0
            exceso = numero_resenas - self._umbral_resenas_medio
            return max(0.0, 30.0 - exceso / 100.0 * 10.0)

    def _puntuar_por_editorial(self, editorial: Optional[str]) -> float:
        """
        Calcula la puntuacion basada en la editorial.

        Editoriales independientes o desconocidas reciben mayor puntuacion.
        Grandes sellos editoriales reciben puntuacion baja.

        Parametros:
            editorial: Nombre de la editorial.

        Retorna:
            Puntuacion de 0.0 a 100.0.
        """
        if not editorial:
            # Sin editorial: probablemente autopublicado
            return 90.0

        editorial_lower = editorial.lower().strip()

        # Verificar si es un gran sello editorial
        for sello in self._editoriales_grandes:
            if sello in editorial_lower or editorial_lower in sello:
                return 10.0

        # Indicadores de autopublicacion
        indicadores_indie = [
            "independently published",
            "autopublicado",
            "self-published",
            "createspace",
            "kindle direct",
            "kdp",
            "draft2digital",
            "smashwords",
            "lulu",
            "blurb",
        ]
        for indicador in indicadores_indie:
            if indicador in editorial_lower:
                return 100.0

        # Editorial desconocida: probablemente independiente
        return 75.0

    def _puntuar_por_calificacion(
        self,
        calificacion: Optional[float],
        numero_resenas: Optional[int],
    ) -> float:
        """
        Calcula la puntuacion basada en la calificacion y su relacion con las resenas.

        Libros con calificaciones altas pero pocas resenas sugieren un nicho
        independiente (publico reducido pero fiel).

        Parametros:
            calificacion: Puntuacion del libro (0.0 a 5.0).
            numero_resenas: Cantidad de resenas.

        Retorna:
            Puntuacion de 0.0 a 100.0.
        """
        if calificacion is None:
            return 50.0  # Sin datos, puntuacion neutra

        # Calificacion alta con pocas resenas = nicho independiente
        if numero_resenas is not None and numero_resenas <= self._umbral_resenas_bajo:
            if calificacion >= 4.0:
                return 90.0
            elif calificacion >= 3.5:
                return 70.0
            else:
                return 50.0

        # Calificacion alta con muchas resenas = autor conocido
        if numero_resenas is not None and numero_resenas > self._umbral_resenas_medio:
            return 20.0

        return 50.0

    def _puntuar_por_formato(self, ediciones: list) -> float:
        """
        Calcula la puntuacion basada en los formatos disponibles.

        Los autores independientes tienden a publicar principalmente
        en formato digital (ebook). Si solo hay ediciones digitales,
        la puntuacion es mayor.

        Parametros:
            ediciones: Lista de ediciones del libro.

        Retorna:
            Puntuacion de 0.0 a 100.0.
        """
        if not ediciones:
            return 50.0  # Sin datos de ediciones

        from app.modelos.edicion import FormatoLibro

        formatos = {e.formato for e in ediciones}

        # Solo formato digital = probablemente autopublicado
        formatos_digitales = {FormatoLibro.EBOOK, FormatoLibro.AUDIOLIBRO}
        if formatos.issubset(formatos_digitales):
            return 85.0

        # Multiples formatos incluyendo tapa dura = editorial grande
        if FormatoLibro.TAPA_DURA in formatos and FormatoLibro.TAPA_BLANDA in formatos:
            return 25.0

        # Solo tapa blanda o bolsillo
        formatos_economicos = {FormatoLibro.TAPA_BLANDA, FormatoLibro.BOLSILLO, FormatoLibro.OTRO}
        if formatos.issubset(formatos_economicos):
            return 65.0

        return 50.0

    def obtener_estadisticas(
        self,
        libros: List[LibroConEdiciones],
    ) -> dict:
        """
        Genera estadisticas del filtrado de autores independientes.

        Parametros:
            libros: Lista de libros ya puntuados.

        Retorna:
            Diccionario con estadisticas del filtrado.
        """
        if not libros:
            return {
                "total_libros": 0,
                "autores_independientes": 0,
                "autores_establecidos": 0,
                "puntuacion_promedio": 0.0,
                "puntuacion_maxima": 0.0,
                "puntuacion_minima": 0.0,
            }

        puntuaciones = [l.puntuacion_independencia for l in libros]
        independientes = [l for l in libros if l.es_autor_independiente]

        return {
            "total_libros": len(libros),
            "autores_independientes": len(independientes),
            "autores_establecidos": len(libros) - len(independientes),
            "puntuacion_promedio": round(sum(puntuaciones) / len(puntuaciones), 2),
            "puntuacion_maxima": round(max(puntuaciones), 2),
            "puntuacion_minima": round(min(puntuaciones), 2),
        }
