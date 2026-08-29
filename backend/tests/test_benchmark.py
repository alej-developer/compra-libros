"""
Suite de pruebas de Benchmark y Rendimiento.

Evalúa latencia, concurrencia (10, 20 y 30 peticiones simultáneas),
tasa de éxito, throughput (peticiones/segundo) y percentiles P95.
"""

import sys
import time
import asyncio
import statistics
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.principal import crear_aplicacion


aplicacion = crear_aplicacion()


async def ejecutar_peticion_individual(cliente: httpx.AsyncClient, termino: str) -> dict:
    """Ejecuta una petición individual de búsqueda y mide la latencia."""
    inicio = time.perf_counter()
    try:
        respuesta = await cliente.post(
            "/api/scraping/buscar",
            json={"termino_busqueda": termino, "resultados_por_pagina": 10},
            timeout=30.0,
        )
        latencia = time.perf_counter() - inicio
        exito = respuesta.status_code == 200
        total_libros = len(respuesta.json().get("libros", [])) if exito else 0
        return {
            "exito": exito,
            "codigo": respuesta.status_code,
            "latencia": latencia,
            "libros": total_libros,
        }
    except Exception as err:
        latencia = time.perf_counter() - inicio
        return {
            "exito": False,
            "codigo": 500,
            "latencia": latencia,
            "error": str(err),
            "libros": 0,
        }


async def benchmark_latencia_secuencial(transport: httpx.ASGITransport, repeticiones: int = 5):
    """Mide la latencia media en ejecuciones secuenciales."""
    print("\n" + "=" * 60)
    print(" 1. BENCHMARK DE LATENCIA SECUENCIAL")
    print("=" * 60)
    terminos = ["quijote", "cien anos de soledad", "ficciones", "rayuela", "poesia"]

    latencias = []
    async with httpx.AsyncClient(transport=transport, base_url="http://benchmark") as cliente:
        for i, termino in enumerate(terminos[:repeticiones], 1):
            res = await ejecutar_peticion_individual(cliente, termino)
            latencias.append(res["latencia"])
            print(f"  [Iteración {i}] Término: '{termino:<22}' | Latencia: {res['latencia']:.3f}s | Libros: {res['libros']}")

    media = statistics.mean(latencias)
    mediana = statistics.median(latencias)
    minimo = min(latencias)
    maximo = max(latencias)

    print("-" * 60)
    print(f"  Media:   {media:.3f}s")
    print(f"  Mediana: {mediana:.3f}s")
    print(f"  Mínimo:  {minimo:.3f}s")
    print(f"  Máximo:  {maximo:.3f}s")
    return {"media": media, "mediana": mediana, "min": minimo, "max": maximo}


async def benchmark_concurrencia(transport: httpx.ASGITransport, concurrencia: int = 10):
    """Evalúa el comportamiento y rendimiento bajo carga concurrente."""
    print("\n" + "=" * 60)
    print(f" 2. BENCHMARK DE CONCURRENCIA ({concurrencia} peticiones simultáneas)")
    print("=" * 60)

    terminos = [
        "quijote", "cortazar", "borges", "garcia marquez", "poesia",
        "filosofia", "historia", "ciencia ficcion", "ensayo", "novela",
        "teatro", "cuentos", "cronicas", "arte", "literatura"
    ]

    async with httpx.AsyncClient(transport=transport, base_url="http://benchmark") as cliente:
        inicio_total = time.perf_counter()
        tareas = [
            ejecutar_peticion_individual(cliente, terminos[i % len(terminos)])
            for i in range(concurrencia)
        ]
        resultados = await asyncio.gather(*tareas)
        tiempo_total = time.perf_counter() - inicio_total

    exitos = sum(1 for r in resultados if r["exito"])
    latencias = [r["latencia"] for r in resultados]
    tasa_exito = (exitos / concurrencia) * 100
    throughput = concurrencia / tiempo_total if tiempo_total > 0 else 0

    p95 = statistics.quantiles(latencias, n=20)[18] if len(latencias) >= 20 else max(latencias)

    print(f"  Tiempo total de lote: {tiempo_total:.3f}s")
    print(f"  Peticiones exitosas:  {exitos}/{concurrencia} ({tasa_exito:.1f}%)")
    print(f"  Throughput (RPS):     {throughput:.2f} peticiones/segundo")
    print(f"  Latencia media:       {statistics.mean(latencias):.3f}s")
    print(f"  Latencia P95:         {p95:.3f}s")
    return {
        "concurrencia": concurrencia,
        "tiempo_total": tiempo_total,
        "tasa_exito": tasa_exito,
        "throughput": throughput,
        "media": statistics.mean(latencias),
        "p95": p95,
    }


async def ejecutar_todos_los_benchmarks():
    """Ejecuta la batería completa de pruebas de rendimiento."""
    transport = httpx.ASGITransport(app=aplicacion)
    print("\n>>> INICIANDO BATERÍA DE PRUEBAS DE BENCHMARK <<<\n")
    
    # 1. Latencia secuencial
    await benchmark_latencia_secuencial(transport, repeticiones=5)
    
    # 2. Concurrencia a 10 peticiones
    await benchmark_concurrencia(transport, concurrencia=10)
    
    # 3. Concurrencia a 25 peticiones
    await benchmark_concurrencia(transport, concurrencia=25)
    
    print("\n" + "=" * 60)
    print(" >>> RESULTADOS DE BENCHMARK COMPLETADOS CON ÉXITO <<<")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(ejecutar_todos_los_benchmarks())
