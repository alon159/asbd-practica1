# -*- coding: utf-8 -*-
"""
Trabajo PySpark: WordCount Distribuido sobre HDFS
Asignatura: ASBD - Practica 1
"""

import sys
from pyspark.sql import SparkSession

def main():
    # Inicializar la sesion de Spark
    spark = SparkSession.builder \
        .appName("ASBD-Distributed-WordCount") \
        .config("spark.hadoop.dfs.replication", "2") \
        .getOrCreate()

    sc = spark.sparkContext

    input_path = "hdfs://master:9000/input/el_quijote.txt"
    output_path = "hdfs://master:9000/output/wordcount_result"

    print("=" * 60)
    print(f"[*] Iniciando WordCount en clúster Spark...")
    print(f"[*] Fichero de entrada (HDFS): {input_path}")
    print(f"[*] Directorio de salida (HDFS): {output_path}")
    print("=" * 60)

    # Leemos el archivo desde HDFS forzando 4 particiones para distribuir
    # las tareas equitativamente entre los workers del cluster
    lines = sc.textFile(input_path, minPartitions=4)

    # Transformaciones RDD (MapReduce clásico)
    # 1. Separar lineas en palabras
    # 2. Normalizar a minusculas y limpiar puntuacion
    # 3. Filtrar palabras vacias
    # 4. Mapear palabra -> (palabra, 1)
    # 5. Reducir por clave sumando ocurrencias
    counts = lines.flatMap(lambda line: line.split()) \
                  .map(lambda word: word.lower().strip(".,;:?!'\"()[]-")) \
                  .filter(lambda word: len(word) > 0) \
                  .map(lambda word: (word, 1)) \
                  .reduceByKey(lambda a, b: a + b)

    # Guardar el resultado en HDFS
    counts.saveAsTextFile(output_path)

    print("=" * 60)
    print(f"[*] Trabajo finalizado con exito. Resultados guardados en {output_path}")
    print("=" * 60)

    spark.stop()

if __name__ == "__main__":
    main()
