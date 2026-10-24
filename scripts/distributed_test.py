#!/usr/bin/env python3
"""
distributed_test.py
Script de prueba para demostrar el procesamiento distribuido en Spark Standalone
y la lectura desde HDFS con factor de replicación 2.
"""

import socket
import sys
from pyspark.sql import SparkSession

def inspect_partition(partition_index, iterator):
    """
    Función ejecutada dentro de cada tarea en los Workers de Spark.
    Captura el nombre del host donde se ejecuta físicamente la tarea.
    """
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        ip = "unknown"

    records = list(iterator)
    count = len(records)
    # Devolver información del nodo ejecutor y las líneas procesadas
    yield (partition_index, hostname, ip, count)

def main():
    hdfs_url = "hdfs://192.168.56.10:9000/input/sample_data.txt"

    print("\n" + "="*75)
    print(" INICIANDO TEST DISTRIBUIDO EN SPARK Y HDFS")
    print("="*75)
    print(f"-> Leyendo datos desde HDFS: {hdfs_url}")

    spark = SparkSession.builder \
        .appName("DemostracionRepartoTrabajoDistribuido") \
        .getOrCreate()

    sc = spark.sparkContext
    # Forzar un nivel de paralelismo de al menos 4 particiones para asegurar
    # que ambos nodos worker reciban tareas concurrentemente
    rdd = sc.textFile(hdfs_url, minPartitions=4)

    # 1. Auditoría de distribución física de particiones entre Workers
    print("\n[PASO 1] Auditando qué Worker ejecuta cada partición:")
    partition_audit = rdd.mapPartitionsWithIndex(inspect_partition).collect()

    hosts_used = set()
    for part_idx, host, ip, count in partition_audit:
        print(f"  * Partición #{part_idx} ejecutada en: Host '{host}' (IP: {ip}) - {count} registros")
        hosts_used.add(host)

    print("\n" + "-"*75)
    print(f" RESUMEN DE NODOS PARTICIPANTES: {sorted(list(hosts_used))}")
    if len(hosts_used) >= 2:
        print(" [OK] ÉXITO: El trabajo se ha repartido eficazmente entre los dos workers.")
    else:
        print(" [AVISO] Las tareas se ejecutaron en un único nodo.")
    print("-" * 75)

    # 2. Conteo distribuido de palabras (WordCount)
    print("\n[PASO 2] Ejecutando WordCount distribuido...")
    words_rdd = rdd.flatMap(lambda line: line.lower().split()) \
                   .map(lambda word: (word.strip(".,;:!?()[]\"'"), 1)) \
                   .filter(lambda pair: len(pair[0]) > 3) \
                   .reduceByKey(lambda a, b: a + b)

    top_words = words_rdd.takeOrdered(10, key=lambda x: -x[1])
    print(" Top 10 palabras más frecuentes encontradas en el texto:")
    for word, freq in top_words:
        print(f"    - {word}: {freq}")

    total_words = words_rdd.map(lambda x: x[1]).sum()
    print(f"\n Total de palabras (longitud > 3): {total_words}")
    print("="*75)
    print(" TEST DISTRIBUIDO COMPLETADO SATISFACTORIAMENTE")
    print("="*75 + "\n")

    spark.stop()

if __name__ == "__main__":
    main()
