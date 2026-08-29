# Sistema de Web Scraping y Comparacion de Libros

Plataforma integral para la busqueda, comparacion de precios y descubrimiento de literatura tanto en librerias tradicionales como en plataformas digitales y mercados de segunda mano. El sistema es completamente funcional, incluye enlaces directos y seguros para la adquisicion de ejemplares, prioriza el hallazgo de ofertas y visibiliza autores emergentes e independientes mediante algoritmos de evaluacion de sellos editoriales y recepcion critica.

---

## Tabla de Contenidos

1. [Descripcion del Proyecto](#descripcion-del-proyecto)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Estructura del Repositorio](#estructura-del-repositorio)
4. [Requisitos Previos](#requisitos-previos)
5. [Instalacion y Configuracion](#instalacion-y-configuracion)
6. [Guia de Ejecucion](#guia-de-ejecucion)
7. [Endpoints de la API](#endpoints-de-la-api)
8. [Enfoque de Privacidad y Scraping Etico](#enfoque-de-privacidad-y-scraping-etico)
9. [Licencia y Consideraciones Legales](#licencia-y-consideraciones-legales)

---

## Descripcion del Proyecto

Este proyecto centraliza la busqueda de obras literarias a traves de multiples canales comerciales y de coleccionismo, ofreciendo una experiencia visual sobria y eficiente. Entre sus capacidades destacan:

- **Extraccion multicanal integral**: Recoleccion estructurada de datos desde librerias tradicionales (Casa del Libro, Fnac), plataformas digitales (Amazon Kindle, Google Books) y portales especializados en libros descatalogados, antiguos y de ocasion (Iberlibro, Todocoleccion, Uniliber).
- **Soporte de libros nuevos y de segunda mano**: Identificacion explicita de la condicion fisica del ejemplar mediante el atributo de estado ("Nuevo" o "De segunda mano"), permitiendo descubrir opciones economicas y ejemplares de coleccionista.
- **Enlaces directos y seguros ("Ver ejemplar")**: Cada resultado incluye la URL absoluta y verificada hacia la tienda o vendedor correspondiente, abriendose en pestana independiente mediante `target="_blank"` y atributos de proteccion `rel="noopener noreferrer"`, sin intermediarios ni rastreo de clics.
- **Deteccion de ofertas y oportunidades**: Localizacion sistematica de ejemplares con descuentos significativos, ofertas especiales o distribucion sin costo.
- **Algoritmo de visibilidad para autores emergentes**: Ponderacion analitica de volumen de resenas, clasificacion de sellos editoriales independientes y patrones de autopublicacion para destacar creadores poco difundidos.
- **Interfaz de usuario minimalista**: Diseno funcional inspirado en la tranquilidad de un estudio de lectura hogareno (tonos madera, pergamino y grises calidos), optimizado para consulta rapida y comparacion limpia sin elementos invasivos.

---

## Arquitectura del Sistema

La aplicacion sigue los principios de la Programacion Orientada a Objetos (POO), desacoplando la logica de negocio, los mecanismos de extraccion web y la capa de presentacion.

### Componentes Principales

```
+-----------------------------------------------------------------------+
|                              FRONTEND                                 |
|          HTML5 Semantico + CSS3 Personalizado + JavaScript            |
|       (Consumo Asincrono REST / Diseno Responsivo / Sin Rastreo)      |
+-----------------------------------------------------------------------+
                                   |
                             Peticiones HTTP
                                   |
                                   v
+-----------------------------------------------------------------------+
|                           API REST (FastAPI)                          |
|                     Middleware CORS + Validacion                      |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                    SERVICIO DE ORQUESTACION (POO)                     |
|           Coordina busquedas concurrentes y unifica resultados        |
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
|                   UTILIDADES DE SCRAPING ETICO                        |
|   - Rotacion de User-Agents       - Tiempos de espera aleatorios      |
|   - Cabecera Do Not Track (DNT)   - Gestion de limites de tasa (429)  |
|   - Resolucion de URLs absolutas  - Descarte silencioso sin enlace    |
+-----------------------------------------------------------------------+
                                       |
                                       v
+-----------------------------------------------------------------------+
|                FILTRO DE AUTORES INDEPENDIENTES                       |
|   Calculo ponderado de puntuacion de independencia (0 a 100)          |
+-----------------------------------------------------------------------+
```

### Modelos de Datos (Pydantic)

- **Autor**: Entidad que almacena nombre, nacionalidad, semblanza biografica y enlace de referencia.
- **Libro**: Modelo central que integra titulo, coleccion de autores, identificadores normalizados (ISBN-10 / ISBN-13), editorial, categorias tematicas, idioma, calificacion media, enlace de origen (`url_fuente`), enlace obligatorio y validado de compra (`url_compra`) y estado fisico (`estado`: "Nuevo" o "De segunda mano").
- **Edicion**: Registro de variantes comerciales (tapa dura, tapa blanda, libro de bolsillo, edicion Kindle, audiolibro), precio unitario, divisa, disponibilidad en inventario y enlace de adquisicion.
- **FiltroScraping**: Parametrizacion exhaustiva de busqueda (terminos clave, rangos de precio, idioma, sellos especificos, ordenacion y paginacion).
- **ResultadoBusqueda**: Contenedor consolidado con metricas de tiempo de respuesta, fuentes consultadas, evaluacion de independencia autoral y registros de ejecucion.

---

## Estructura del Repositorio

```
.
|-- .gitignore                  # Exclusion estricta de credenciales, entornos y temporales
|-- README.md                   # Documentacion tecnica principal
|-- backend/
|   |-- .env.ejemplo            # Plantilla para variables de entorno locales
|   |-- pyproject.toml          # Definicion de dependencias y herramientas de desarrollo
|   `-- app/
|       |-- __init__.py
|       |-- configuracion.py    # Gestion centralizada con Pydantic Settings
|       |-- principal.py        # Punto de entrada de FastAPI y configuracion de middlewares
|       |-- modelos/            # Clases y esquemas de datos estructurados
|       |   |-- __init__.py
|       |   |-- autor.py
|       |   |-- edicion.py
|       |   |-- filtro_scraping.py
|       |   |-- libro.py        # Modelo Libro con url_compra y estado
|       |   `-- resultado_busqueda.py
|       |-- rutas/              # Controladores y definicion de endpoints REST
|       |   |-- __init__.py
|       |   `-- rutas_scraping.py
|       |-- scraping/           # Motor de extraccion y algoritmos analiticos
|       |   |-- __init__.py
|       |   |-- base.py         # Clase abstracta ScraperBase con soporte de URLs absolutas
|       |   |-- filtro_autores.py # Evaluador ponderado de autores independientes
|       |   |-- scraper_libreria_fisica.py   # Scraper de librerias tradicionales
|       |   |-- scraper_plataforma_digital.py # Scraper de plataformas digitales
|       |   |-- scraper_segunda_mano.py      # Scraper especializado de segunda mano
|       |   `-- utilidades.py   # Rotador de agentes de usuario y cliente HTTP seguro
|       `-- servicios/          # Capa de orquestacion y logica del negocio
|           |-- __init__.py
|           `-- servicio_scraping.py
`-- frontend/
    |-- index.html              # Interfaz de usuario estructurada
    |-- css/
    |   `-- estilos.css         # Diseno editorial con paleta neutra y distintivos de estado
    `-- js/
        |-- api.js              # Capa de comunicacion asincrona con la API
        `-- app.js              # Controlador del DOM, renderizado de tarjetas y enlaces
```

---

## Requisitos Previos

- **Python**: Version 3.11 o superior.
- **Navegador web moderno**: Google Chrome, Mozilla Firefox, Microsoft Edge o Safari con soporte para JavaScript ES6+.
- **Git**: Para el control de versiones y clonacion del repositorio.

---

## Instalacion y Configuracion

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

Active el entorno virtual segun su sistema operativo:

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

O instale directamente las librerias requeridas:

```bash
pip install fastapi uvicorn[standard] pydantic pydantic-settings httpx beautifulsoup4 lxml
```

### 4. Variables de Entorno (Opcional)

Si desea personalizar puertos, origenes de CORS o tiempos de espera, copie el archivo de ejemplo:

```bash
cp .env.ejemplo .env
```

---

## Guia de Ejecucion

### Ejecucion del Servidor Backend

Desde el directorio `backend` y con el entorno virtual activo:

```bash
uvicorn app.principal:app --reload --host 127.0.0.1 --port 8000
```

El servidor quedara disponible en `http://127.0.0.1:8000`.

- **Documentacion interactiva Swagger UI**: `http://127.0.0.1:8000/docs`
- **Documentacion interactiva ReDoc**: `http://127.0.0.1:8000/redoc`

### Ejecucion del Cliente Frontend

El frontend esta compuesto por archivos estaticos que no requieren compiladores adicionales. Puede abrirse directamente o servirse mediante un servidor web local:

**Opcion A: Servidor HTTP simple con Python (Recomendada)**

Abra una nueva terminal, navegue a la carpeta del frontend y ejecute:

```bash
cd frontend
python -m http.server 3000
```

Abra su navegador en: `http://localhost:3000`

**Opcion B: Apertura directa**

Abra el archivo `frontend/index.html` en su navegador web preferido.

---

## Endpoints de la API

| Metodo | Ruta | Descripcion | Parametros / Cuerpo |
|---|---|---|---|
| `GET` | `/` | Comprobacion de bienvenida y estado del servicio | Ninguno |
| `GET` | `/salud` | Verificacion de estado operativo (health check) | Ninguno |
| `GET` | `/api/scraping/fuentes` | Catalogo de fuentes registradas (librerias fisicas, digitales y segunda mano) | Ninguno |
| `POST` | `/api/scraping/buscar` | Busqueda distribuida y unificada de libros con enlaces y estado | Cuerpo JSON con esquema `FiltroScraping` |
| `GET` | `/api/scraping/ofertas` | Consulta de libros en promocion o bajo costo | `precio_maximo` (float), `limite` (int) |
| `POST` | `/api/scraping/autores-independientes` | Busqueda priorizando obras autopublicadas | Cuerpo JSON `FiltroScraping` y `puntuacion_minima` |

---

## Enfoque de Privacidad y Scraping Etico

El proyecto ha sido concebido bajo estrictos estandares de privacidad y respeto a las infraestructuras de terceros:

1. **Privacidad Absoluta de los Usuarios**:
   - **Cero analitica y cero rastreo de clics**: Ni el backend ni el frontend implementan telemetria, cookies, identificadores de sesion, balizas web ni interceptores de clics en los enlaces de compra. Los enlaces dirigen directamente a la fuente externa sin redirecciones intermedias de seguimiento.
   - **Navegacion segura con `rel="noopener noreferrer"`**: Todos los enlaces externos se abren en pestanas aisladas impidiendo que el sitio de destino acceda al objeto `window.opener` o reciba cabeceras `Referer` que revelen el origen de navegacion del usuario.
   - **Cero almacenamiento de datos personales**: La plataforma no solicita, no registra ni persiste identificadores de los usuarios finales, historiales de busqueda ni direcciones IP.

2. **Scraping Responsable y Etico**:
   - **Cadencia controlada (Pacing)**: Se aplican pausas aleatorias entre solicitudes (1.0 a 4.0 segundos con variabilidad estocastica adicional) y demoras prolongadas entre paginaciones sucesivas para prevenir la sobrecarga de los servidores consultados.
   - **Rotacion no invasiva de User-Agents**: Se emplean cadenas de agentes de usuario correspondientes a navegadores estandar para garantizar compatibilidad sin ocultar propositos ilegitimos.
   - **Cabecera Do Not Track (DNT)**: Todas las solicitudes HTTP salientes incluyen la directiva `DNT: 1`.
   - **Gestion de limites de tasa**: El sistema interpreta de manera automatica respuestas con codigo HTTP 429 (Too Many Requests) o 503, suspendiendo temporalmente las consultas y aplicando retroceso exponencial.
   - **Descarte silencioso de datos incompletos**: Si durante la extraccion un ejemplar carece de enlace valido de adquisicion, es descartado silenciosamente sin interrumpir el flujo del usuario ni degradar la experiencia de busqueda.
   - **Consultas a informacion publica**: La extraccion se limita exclusivamente a datos bibliograficos y comerciales de acceso publico general.

---

## Licencia y Consideraciones Legales

Este software se proporciona con fines educativos, de investigacion y organizacion personal. Los usuarios son responsables de garantizar que su uso cumpla con los terminos de servicio de las plataformas consultadas y con las regulaciones de propiedad intelectual aplicables en sus respectivas jurisdicciones.
