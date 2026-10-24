#!/usr/bin/env bash
# run_verification.sh
# Script para verificar HDFS (Live Nodes, Replicación 2) y ejecutar el trabajo distribuido en Spark

set -e

echo "=========================================================================="
echo " 1. ESTADO DE LOS NODOS EN HDFS (DATANODES ACTIVOS)"
echo "=========================================================================="
docker exec hadoop-namenode hdfs dfsadmin -report

echo ""
echo "=========================================================================="
echo " 2. SUBIENDO FICHERO DE DATOS A HDFS (CON FACTOR DE REPLICACIÓN 2)"
echo "=========================================================================="
# Crear directorio /input en HDFS si no existe
docker exec hadoop-namenode hdfs dfs -mkdir -p /input

# Subir sample_data.txt
docker exec -i hadoop-namenode hdfs dfs -put -f - /input/sample_data.txt < /vagrant/scripts/sample_data.txt

# Forzar factor de replicación 2 explícitamente para el fichero
docker exec hadoop-namenode hdfs dfs -setrep -w 2 /input/sample_data.txt

# Listar fichero
docker exec hadoop-namenode hdfs dfs -ls /input

echo ""
echo "=========================================================================="
echo " 3. COMPROBACIÓN DE REPLICACIÓN Y LOCALIZACIÓN DE BLOQUES (FSCK)"
echo "=========================================================================="
docker exec hadoop-namenode hdfs fsck /input/sample_data.txt -files -blocks -locations

echo ""
echo "=========================================================================="
echo " 4. EJECUTANDO TRABAJO DISTRIBUIDO EN SPARK (PYSPARK SUBMIT)"
echo "=========================================================================="
docker cp /vagrant/scripts/distributed_test.py spark-master:/tmp/distributed_test.py
docker exec spark-master /opt/spark/bin/spark-submit \
  --master spark://192.168.56.10:7077 \
  --deploy-mode client \
  /tmp/distributed_test.py

echo ""
echo "=========================================================================="
echo " VERIFICACIÓN FINALIZADA CON ÉXITO"
echo " Comprueba las interfaces web del clúster en tu navegador:"
echo "   - Spark Master:     http://192.168.56.10:8080 (verás los 2 workers y el job completado)"
echo "   - HDFS NameNode:    http://192.168.56.10:9870 (verás 'Live Nodes: 2' y los bloques)"
echo "   - Spark Worker 1:   http://192.168.56.11:8081"
echo "   - Spark Worker 2:   http://192.168.56.12:8081"
echo "=========================================================================="
