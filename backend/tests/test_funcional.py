"""
Pruebas funcionales para el sistema de scraping de libros.

Valida modelos de datos, validadores de URL, motor de scraping,
algoritmo de autores independientes y endpoints de la API FastAPI.
"""

import unittest
import asyncio
import sys
from pathlib import Path
import httpx
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.principal import crear_aplicacion
from app.modelos import Libro, Autor, Edicion, FiltroScraping, ResultadoBusqueda
from app.modelos.libro import EstadoLibro
from app.modelos.edicion import FormatoLibro
from app.scraping.filtro_autores import FiltroAutoresIndependientes
from app.scraping.scraper_segunda_mano import ScraperSegundaMano
from app.scraping.scraper_open_library import ScraperOpenLibrary
from app.servicios.servicio_scraping import ServicioScraping
from app.modelos.resultado_busqueda import LibroConEdiciones


aplicacion_prueba = crear_aplicacion()


class TestModelosDatos(unittest.TestCase):
    """Pruebas de validación de los modelos Pydantic."""

    def test_creacion_libro_valido(self):
        """Verifica la creación correcta de una instancia de Libro con URL y estado."""
        autor = Autor(nombre="Gabriel García Márquez", pais_origen="Colombia")
        libro = Libro(
            titulo="Cien años de soledad",
            autores=[autor],
            url_compra="https://www.casadellibro.com/libro-cien-anos/123",
            estado=EstadoLibro.NUEVO,
            editorial="Debolsillo",
            isbn="9788497592208",
        )
        self.assertEqual(libro.titulo, "Cien años de soledad")
        self.assertEqual(libro.url_compra, "https://www.casadellibro.com/libro-cien-anos/123")
        self.assertEqual(libro.estado, EstadoLibro.NUEVO)

    def test_validacion_url_compra_invalida(self):
        """Verifica que URLs no HTTP(S) o maliciosas sean rechazadas por el validador."""
        autor = Autor(nombre="Autor Prueba")
        
        with self.assertRaises(ValidationError):
            Libro(
                titulo="Libro con URL Inválida",
                autores=[autor],
                url_compra="javascript:alert(1)",
                estado=EstadoLibro.NUEVO,
            )

        with self.assertRaises(ValidationError):
            Libro(
                titulo="Libro con URL Relativa",
                autores=[autor],
                url_compra="/libro/12345",
                estado=EstadoLibro.SEGUNDA_MANO,
            )

    def test_modelo_edicion(self):
        """Verifica la creación y formato de Edición."""
        edicion = Edicion(
            isbn="9788437604947",
            formato=FormatoLibro.TAPA_BLANDA,
            editorial="Cátedra",
            precio=14.50,
            moneda="EUR",
            tienda="Casa del Libro",
            url_compra="https://www.casadellibro.com/libro/1",
            disponible=True,
        )
        self.assertEqual(edicion.isbn, "9788437604947")
        self.assertEqual(edicion.formato, FormatoLibro.TAPA_BLANDA)
        self.assertEqual(edicion.precio, 14.50)
        self.assertEqual(edicion.tienda, "Casa del Libro")

    def test_modelo_filtro_scraping(self):
        """Verifica la validación de filtros de búsqueda."""
        filtro = FiltroScraping(
            termino_busqueda="quijote",
            precio_minimo=5.0,
            precio_maximo=20.0,
            resultados_por_pagina=15,
        )
        self.assertEqual(filtro.termino_busqueda, "quijote")
        self.assertEqual(filtro.precio_minimo, 5.0)
        self.assertEqual(filtro.precio_maximo, 20.0)
        self.assertEqual(filtro.resultados_por_pagina, 15)


class TestFiltroAutoresIndependientes(unittest.TestCase):
    """Pruebas del algoritmo de scoring de autores independientes."""

    def test_calculo_puntuacion_autor_independiente(self):
        """Un libro autopublicado con pocas reseñas debe tener alta puntuación."""
        filtro = FiltroAutoresIndependientes()
        libro = Libro(
            titulo="Poemas del Alma",
            autores=[Autor(nombre="Poeta Independiente")],
            url_compra="https://openlibrary.org/search?q=poemas",
            estado=EstadoLibro.NUEVO,
            editorial="Autopublicado",
            calificacion=4.8,
        )
        libro_ed = LibroConEdiciones(
            libro=libro,
            ediciones=[
                Edicion(
                    formato=FormatoLibro.EBOOK,
                    precio=2.99,
                    tienda="Open Library",
                    url_compra="https://openlibrary.org/search?q=poemas",
                    disponible=True,
                )
            ],
            numero_resenas=8,
        )
        puntuacion = filtro.calcular_puntuacion(libro_ed)
        self.assertGreaterEqual(puntuacion, 70.0)
        puntuados = filtro.filtrar_y_puntuar([libro_ed], puntuacion_minima=50.0)
        self.assertEqual(len(puntuados), 1)
        self.assertTrue(puntuados[0].es_autor_independiente)

    def test_calculo_puntuacion_autor_establecido(self):
        """Un bestseller de gran editorial con miles de reseñas debe tener baja puntuación."""
        filtro = FiltroAutoresIndependientes()
        libro = Libro(
            titulo="Bestseller Internacional",
            autores=[Autor(nombre="Autor Famoso")],
            url_compra="https://www.casadellibro.com/libro-famoso",
            estado=EstadoLibro.NUEVO,
            editorial="Planeta",
            calificacion=4.2,
        )
        libro_ed = LibroConEdiciones(
            libro=libro,
            ediciones=[
                Edicion(
                    formato=FormatoLibro.TAPA_DURA,
                    precio=22.90,
                    tienda="Casa del Libro",
                    url_compra="https://www.casadellibro.com/libro-famoso",
                    disponible=True,
                ),
                Edicion(
                    formato=FormatoLibro.TAPA_BLANDA,
                    precio=14.90,
                    tienda="Casa del Libro",
                    url_compra="https://www.casadellibro.com/libro-famoso",
                    disponible=True,
                ),
            ],
            numero_resenas=4500,
        )
        puntuacion = filtro.calcular_puntuacion(libro_ed)
        self.assertLess(puntuacion, 50.0)
        self.assertFalse(libro_ed.es_autor_independiente)


class TestServicioScraping(unittest.IsolatedAsyncioTestCase):
    """Pruebas del servicio orquestador de scraping."""

    async def test_busqueda_completa(self):
        """Verifica que la búsqueda retorna libros válidos con URLs y estados definidos."""
        servicio = ServicioScraping()
        filtro = FiltroScraping(termino_busqueda="quijote", resultados_por_pagina=10)
        resultado = await servicio.buscar(filtro)

        self.assertIsInstance(resultado, ResultadoBusqueda)
        self.assertGreater(resultado.total_encontrados, 0)
        for libro_ed in resultado.libros:
            self.assertTrue(libro_ed.libro.url_compra.startswith(("http://", "https://")))
            self.assertIn(libro_ed.libro.estado, (EstadoLibro.NUEVO, EstadoLibro.SEGUNDA_MANO))

    async def test_busqueda_ofertas(self):
        """Verifica que la búsqueda de ofertas respeta el precio máximo."""
        servicio = ServicioScraping()
        resultado = await servicio.buscar_ofertas(precio_maximo=10.0, limite=20)
        self.assertIsInstance(resultado, ResultadoBusqueda)
        self.assertGreater(resultado.total_encontrados, 0)
        for libro_ed in resultado.libros:
            for ed in libro_ed.ediciones:
                if ed.precio is not None:
                    self.assertLessEqual(ed.precio, 10.0)

    async def test_filtrado_silencioso(self):
        """Verifica que los libros sin URL válida no se incluyen en los resultados."""
        servicio = ServicioScraping()
        libro_valido = Libro(
            titulo="Libro Válido",
            autores=[Autor(nombre="Anónimo")],
            url_compra="https://ejemplo.com/valido",
            estado=EstadoLibro.NUEVO,
        )
        self.assertTrue(servicio._tiene_url_compra_valida(libro_valido))

        libro_invalido = Libro(
            titulo="Libro Inválido",
            autores=[Autor(nombre="Anónimo")],
            url_compra="http://invalido.com",
            estado=EstadoLibro.NUEVO,
        )
        libro_invalido.url_compra = ""
        self.assertFalse(servicio._tiene_url_compra_valida(libro_invalido))


class TestEndpointsApi(unittest.IsolatedAsyncioTestCase):
    """Pruebas de integración sobre la API HTTP de FastAPI."""

    async def test_endpoint_salud(self):
        """Verifica el endpoint de estado de salud."""
        transport = httpx.ASGITransport(app=aplicacion_prueba)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as cliente:
            respuesta = await cliente.get("/salud")
            self.assertEqual(respuesta.status_code, 200)
            datos = respuesta.json()
            self.assertEqual(datos["estado"], "saludable")

    async def test_endpoint_fuentes(self):
        """Verifica la lista de fuentes disponibles."""
        transport = httpx.ASGITransport(app=aplicacion_prueba)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as cliente:
            respuesta = await cliente.get("/api/scraping/fuentes")
            self.assertEqual(respuesta.status_code, 200)
            datos = respuesta.json()
            fuentes = datos["fuentes"] if isinstance(datos, dict) and "fuentes" in datos else datos
            self.assertIsInstance(fuentes, list)
            self.assertGreaterEqual(len(fuentes), 5)

    async def test_endpoint_buscar_libros(self):
        """Verifica el endpoint principal de búsqueda."""
        transport = httpx.ASGITransport(app=aplicacion_prueba)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as cliente:
            payload = {"termino_busqueda": "quijote", "resultados_por_pagina": 5}
            respuesta = await cliente.post("/api/scraping/buscar", json=payload)
            self.assertEqual(respuesta.status_code, 200)
            datos = respuesta.json()
            self.assertGreater(datos["total_encontrados"], 0)
            self.assertIn("libros", datos)
            for item in datos["libros"]:
                libro = item["libro"]
                self.assertTrue(libro["url_compra"].startswith(("http://", "https://")))
                self.assertIn(libro["estado"], ("Nuevo", "De segunda mano"))


if __name__ == "__main__":
    unittest.main()
