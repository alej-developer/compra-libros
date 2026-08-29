# Sistema de Web Scraping y Comparación de Libros

Plataforma integral para la búsqueda, comparación de precios y descubrimiento de literatura tanto en librerías tradicionales como en plataformas digitales y mercados de segunda mano. El sistema es completamente funcional, incluye enlaces directos y seguros para la adquisición de ejemplares, prioriza el hallazgo de ofertas y visibiliza autores emergentes e independientes mediante algoritmos de evaluación de sellos editoriales y recepción crítica.

---

## Tabla de Contenidos

1. [Descripción del Proyecto](#descripción-del-proyecto)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Estructura del Repositorio](#estructura-del-repositorio)
4. [Requisitos Previos](#requisitos-previos)
5. [Instalación y Configuración](#instalación-y-configuración)
6. [Guía de Ejecución](#guía-de-ejecución)
7. [Endpoints de la API](#endpoints-de-la-api)
8. [Enfoque de Privacidad y Scraping Ético](#enfoque-de-privacidad-y-scraping-ético)
9. [Licencia y Consideraciones Legales](#licencia-y-consideraciones-legales)

---

## Descripción del Proyecto

Este proyecto centraliza la búsqueda de obras literarias a través de múltiples canales comerciales y de coleccionismo, ofreciendo una experiencia visual sobria y eficiente. Entre sus capacidades destacan:

- **Extracción multicanal integral**: Recolección estructurada de datos desde librerías tradicionales (Casa del Libro, Fnac), plataformas digitales (Amazon Kindle, Google Books) y portales especializados en libros descatalogados, antiguos y de ocasión (Iberlibro, Todocoleccion, Uniliber).
- **Soporte de libros nuevos y de segunda mano**: Identificación explícita de la condición física del ejemplar mediante el atributo de estado ("Nuevo" o "De segunda mano"), permitiendo descubrir opciones económicas y ejemplares de coleccionista.
- **Enlaces directos y seguros ("Ver ejemplar")**: Cada resultado incluye la URL absoluta y verificada hacia la tienda o vendedor correspondiente, abriéndose en pestaña independiente mediante `target="_blank"` y atributos de protección `rel="noopener noreferrer"`, sin intermediarios ni rastreo de clics.
- **Detección de ofertas y oportunidades**: Localización sistemática de ejemplares con descuentos significativos, ofertas especiales o distribución sin costo.
- **Algoritmo de visibilidad para autores emergentes**: Ponderación analítica de volumen de reseñas, clasificación de sellos editoriales independientes y patrones de autopublicación para destacar creadores poco difundidos.
- **Interfaz de usuario minimalista**: Diseño funcional inspirado en la tranquilidad de un estudio de lectura hogareño (tonos madera, pergamino y grises cálidos), optimizado para consulta rápida y comparación limpia sin elementos invasivos.

---

## Arquitectura del Sistema

La aplicación sigue los principios de la Programación Orientada a Objetos (POO), desacoplando la lógica de negocio, los mecanismos de extracción web y la capa de presentación.

### Componentes Principales

```
+-----------------------------------------------------------------------+
|                              FRONTEND                                 |
|          HTML5 Semántico + CSS3 Personalizado + JavaScript            |
|       (Consumo Asíncrono REST / Diseño Responsivo / Sin Rastreo)      |
+-----------------------------------------------------------------------+
                                   |
                             Peticiones HTTP
                                   |
                                   v
+-----------------------------------------------------------------------+
|                           API REST (FastAPI)                          |
|                     Middleware CORS + Validación                      |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                    SERVICIO DE ORQUESTACIÓN (POO)                     |
|           Coordina búsquedas concurrentes y unifica resultados        |
+-----------------------------------------------------------------------+
            |                          |                         |
            v                          v                         v
+-----------------------+  +------------------------+  +-----------------------+
| ScraperLibreriaFisica |  |ScraperPlataformaDigital|  |  ScraperSegundaMano   |
| (Casa del Libro, etc) |  | (Kindle, Google Books) |  |(Iberlibro, Uniliber..)|
+-----------------------+  +------------------------+  +-----------------------+
            |                          |                         |
            +--------------------------+-------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------+
|                   UTILIDADES DE SCRAPING ÉTICO                        |
|   - Rotación de User-Agents       - Tiempos de espera aleatorios      |
|   - Cabecera Do Not Track (DNT)   - Gestión de límites de tasa (429)  |
|   - Resolución de URLs absolutas  - Descarte silencioso sin enlace    |
+-----------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------+
|                FILTRO DE AUTORES INDEPENDIENTES                       |
|   Cálculo ponderado de puntuación de independencia (0 a 100)          |
+-----------------------------------------------------------------------+
```

### Modelos de Datos (Pydantic)

- **Autor**: Entidad que almacena nombre, nacionalidad, semblanza biográfica y enlace de referencia.
- **Libro**: Modelo central que integra título, colección de autores, identificadores normalizados (ISBN-10 / ISBN-13), editorial, categorías temáticas, idioma, calificación media, enlace de origen (`url_fuente`), enlace obligatorio y validado de compra (`url_compra`) y estado físico (`estado`: "Nuevo" o "De segunda mano").
- **Edición**: Registro de variantes comerciales (tapa dura, tapa blanda, libro de bolsillo, edición Kindle, audiolibro), precio unitario, divisa, disponibilidad en inventario y enlace de adquisición.
- **FiltroScraping**: Parametrización exhaustiva de búsqueda (términos clave, rangos de precio, idioma, sellos específicos, ordenación y paginación).
- **ResultadoBusqueda**: Contenedor consolidado con métricas de tiempo de respuesta, fuentes consultadas, evaluación de independencia autoral y registros de ejecución.

---

## Estructura del Repositorio

```
.
|-- .gitignore                  # Exclusión estricta de credenciales, entornos y temporales
|-- README.md                   # Documentación técnica principal
|-- backend/
|   |-- .env.ejemplo            # Plantilla para variables de entorno locales
|   |-- pyproject.toml          # Definición de dependencias y herramientas de desarrollo
|   `-- app/
|       |-- __init__.py
|       |-- configuracion.py    # Gestión centralizada con Pydantic Settings
|       |-- principal.py        # Punto de entrada de FastAPI y configuración de middlewares
|       |-- modelos/            # Clases y esquemas de datos estructurados
|       |   |-- __init__.py
|       |   |-- autor.py
|       |   |-- edicion.py
|       |   |-- filtro_scraping.py
|       |   |-- libro.py        # Modelo Libro con url_compra y estado
|       |   `-- resultado_busqueda.py
|       |-- rutas/              # Controladores y definición de endpoints REST
|       |   |-- __init__.py
|       |   `-- rutas_scraping.py
|       |-- scraping/           # Motor de extracción y algoritmos analíticos
|       |   |-- __init__.py
|       |   |-- base.py         # Clase abstracta ScraperBase con soporte de URLs absolutas
|       |   |-- filtro_autores.py # Evaluador ponderado de autores independientes
|       |   |-- scraper_libreria_fisica.py   # Scraper de librerías tradicionales
|       |   |-- scraper_plataforma_digital.py # Scraper de plataformas digitales
|       |   |-- scraper_segunda_mano.py      # Scraper especializado de segunda mano
|       |   `-- utilidades.py   # Rotador de agentes de usuario y cliente HTTP seguro
|       `-- servicios/          # Capa de orquestación y lógica del negocio
|           |-- __init__.py
|           `-- servicio_scraping.py
`-- frontend/
    |-- index.html              # Interfaz de usuario estructurada
    |-- css/
    |   `-- estilos.css         # Diseño editorial con paleta neutra y distintivos de estado
    `-- js/
        |-- api.js              # Capa de comunicación asíncrona con la API
        `-- app.js              # Controlador del DOM, renderizado de tarjetas y enlaces
```

---

## Requisitos Previos

- **Python**: Versión 3.11 o superior.
- **Navegador web moderno**: Google Chrome, Mozilla Firefox, Microsoft Edge o Safari con soporte para JavaScript ES6+.
- **Git**: Para el control de versiones y clonación del repositorio.

---

## Instalación y Configuración

### 1. Clonar el Repositorio

```bash
git clone https://github.com/alej-developer/compra-libros.git
cd compra-libros
```

### 2. Preparar el Entorno del Backend

Acceda al directorio del backend y configure el entorno virtual:

```bash
cd backend
python -m venv venv
```

Active el entorno virtual según su sistema operativo:

- **Windows (PowerShell)**:
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Windows (CMD)**:
  ```cmd
  .\venv\Scripts\activate.bat
  ```
- **Linux / macOS**:
  ```bash
  source venv/bin/activate
  ```

### 3. Instalar Dependencias

Con el entorno virtual activo, ejecute:

```bash
pip install -e .
```

O instale directamente las librerías requeridas:

```bash
pip install fastapi uvicorn[standard] pydantic pydantic-settings httpx beautifulsoup4 lxml
```

### 4. Variables de Entorno (Opcional)

Si desea personalizar puertos, orígenes de CORS o tiempos de espera, copie el archivo de ejemplo:

```bash
cp .env.ejemplo .env
```

---

## Guía de Ejecución

### Ejecución del Servidor Backend

Desde el directorio `backend` y con el entorno virtual activo:

```bash
uvicorn app.principal:app --reload --host 127.0.0.1 --port 8000
```

El servidor quedará disponible en `http://127.0.0.1:8000`.

- **Documentación interactiva Swagger UI**: `http://127.0.0.1:8000/docs`
- **Documentación interactiva ReDoc**: `http://127.0.0.1:8000/redoc`

### Ejecución del Cliente Frontend

El frontend está compuesto por archivos estáticos que no requieren compiladores adicionales. Puede abrirse directamente o servirse mediante un servidor web local:

**Opción A: Servidor HTTP simple con Python (Recomendada)**

Abra una nueva terminal, navegue a la carpeta del frontend y ejecute:

```bash
cd frontend
python -m http.server 3000
```

Abra su navegador en: `http://localhost:3000`

**Opción B: Apertura directa**

Abra el archivo `frontend/index.html` en su navegador web preferido.

---

## Endpoints de la API

| Método | Ruta | Descripción | Parámetros / Cuerpo |
|---|---|---|---|
| `GET` | `/` | Comprobación de bienvenida y estado del servicio | Ninguno |
| `GET` | `/salud` | Verificación de estado operativo (health check) | Ninguno |
| `GET` | `/api/scraping/fuentes` | Catálogo de fuentes registradas (librerías físicas, digitales y segunda mano) | Ninguno |
| `POST` | `/api/scraping/buscar` | Búsqueda distribuida y unificada de libros con enlaces y estado | Cuerpo JSON con esquema `FiltroScraping` |
| `GET` | `/api/scraping/ofertas` | Consulta de libros en promoción o bajo costo | `precio_maximo` (float), `limite` (int) |
| `POST` | `/api/scraping/autores-independientes` | Búsqueda priorizando obras autopublicadas | Cuerpo JSON `FiltroScraping` y `puntuacion_minima` |

---

## Enfoque de Privacidad y Scraping Ético

El proyecto ha sido concebido bajo estrictos estándares de privacidad y respeto a las infraestructuras de terceros:

1. **Privacidad Absoluta de los Usuarios**:
   - **Cero analítica y cero rastreo de clics**: Ni el backend ni el frontend implementan telemetría, cookies, identificadores de sesión, balizas web ni interceptores de clics en los enlaces de compra. Los enlaces dirigen directamente a la fuente externa sin redirecciones intermedias de seguimiento.
   - **Navegación segura con `rel="noopener noreferrer"`**: Todos los enlaces externos se abren en pestañas aisladas impidiendo que el sitio de destino acceda al objeto `window.opener` o reciba cabeceras `Referer` que revelen el origen de navegación del usuario.
   - **Cero almacenamiento de datos personales**: La plataforma no solicita, no registra ni persiste identificadores de los usuarios finales, historiales de búsqueda ni direcciones IP.

2. **Scraping Responsable y Ético**:
   - **Cadencia controlada (Pacing)**: Se aplican pausas aleatorias entre solicitudes (1.0 a 4.0 segundos con variabilidad estocástica adicional) y demoras prolongadas entre paginaciones sucesivas para prevenir la sobrecarga de los servidores consultados.
   - **Rotación no invasiva de User-Agents**: Se emplean cadenas de agentes de usuario correspondientes a navegadores estándar para garantizar compatibilidad sin ocultar propósitos ilegítimos.
   - **Cabecera Do Not Track (DNT)**: Todas las solicitudes HTTP salientes incluyen la directiva `DNT: 1`.
   - **Gestión de límites de tasa**: El sistema interpreta de manera automática respuestas con código HTTP 429 (Too Many Requests) o 503, suspendiendo temporalmente las consultas y aplicando retroceso exponencial.
   - **Descarte silencioso de datos incompletos**: Si durante la extracción un ejemplar carece de enlace válido de adquisición, es descartado silenciosamente sin interrumpir el flujo del usuario ni degradar la experiencia de búsqueda.
   - **Consultas a información pública**: La extracción se limita exclusivamente a datos bibliográficos y comerciales de acceso público general.

---

## Licencia y Consideraciones Legales

Este software se proporciona con fines educativos, de investigación y organización personal. Los usuarios son responsables de garantizar que su uso cumpla con los términos de servicio de las plataformas consultadas y con las regulaciones de propiedad intelectual aplicables en sus respectivas jurisdicciones.
