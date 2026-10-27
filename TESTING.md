# Guía de Pruebas y Validación Funcional

Esta guía describe paso a paso cómo arrancar el clúster y validar los 4 requisitos funcionales exigidos en la práctica.

---

## 0. Despliegue del Clúster desde Cero

Para levantar todo el clúster de forma automática y reproducible, ejecuta en la raíz del proyecto:

```bash
vagrant up
```

Vagrant creará las 3 máquinas virtuales (`master`, `worker1`, `worker2`), instalará Docker y aprovisionará los contenedores de HDFS y Spark mediante Ansible sin ninguna intervención manual.

Para verificar que todo está levantado correctamente, ejecuta:

```bash
vagrant status
```

---

## Requisito 1: Verificación de las Interfaces Web

Abre tu navegador habitual en el host y comprueba el acceso a las siguientes URLs:

| Servicio | URL | Qué verificar |
| :--- | :--- | :--- |
| **HDFS NameNode UI** | [http://192.168.56.10:9870](http://192.168.56.10:9870) | Ir a la pestaña **Datanodes** y comprobar que aparecen **2 Live Nodes** (`worker1` y `worker2`). |
| **Spark Master UI** | [http://192.168.56.10:8080](http://192.168.56.10:8080) | En la tabla **Workers**, comprobar que aparecen **2 workers** registrados y en estado `ALIVE`. |
| **Spark Worker 1** | [http://192.168.56.11:8081](http://192.168.56.11:8081) | Estado de Worker 1 (Master: `spark://master:7077`). |
| **Spark Worker 2** | [http://192.168.56.12:8082](http://192.168.56.12:8082) | Estado de Worker 2 (Master: `spark://master:7077`). |

---

## Requisito 2: Subida a HDFS con Factor de Replicación 2

Podemos realizar la prueba de 2 formas: via web en [http://192.168.56.10:9870](http://192.168.56.10:9870) o vía línea de comandos. Para agilizar la prueba, aquí se expone específicamente la segunda opción.

Accede por SSH al nodo master:

```bash
vagrant ssh master
```

### 1. Crear el directorio de entrada en HDFS y subir el fichero
```bash
# Crear directorio /input en HDFS
docker exec -it namenode hdfs dfs -mkdir -p /input

# Subir el fichero de prueba montado en /data
docker exec -it namenode hdfs dfs -put /data/el_quijote.txt /input/el_quijote.txt
```

### 2. Comprobar el factor de replicación
```bash
docker exec -it namenode hdfs dfs -ls /input
```
*Salida esperada:*
```text
Found 1 items
-rw-r--r--   2 root supergroup       2456 ... /input/el_quijote.txt
```
*(Nota el número **`2`** en la segunda columna, que confirma la replicación fijada).*

### 3. Verificar que los bloques están en ambos DataNodes
```bash
docker exec -it namenode hdfs fsck /input/el_quijote.txt -files -blocks -locations
```
*Salida esperada:*
En la salida del comando se indicará que el bloque se encuentra alojado simultáneamente en `192.168.56.11` (`worker1`) y `192.168.56.12` (`worker2`).

---

## Requisito 3: Ejecución de Trabajo Spark Distribuido

Dentro del nodo master (`vagrant ssh master`), lanzamos el trabajo PySpark mediante `spark-submit`:

```bash
docker exec -it spark-master /spark/bin/spark-submit \
  --master spark://master:7077 \
  --deploy-mode client \
  --num-executors 2 \
  --executor-cores 1 \
  --executor-memory 512M \
  /jobs/wordcount.py
```

### Verificaciones del trabajo:

1. **Reparto de trabajo real entre workers**:
   - Abre la interfaz de Spark Master en [http://192.168.56.10:8080](http://192.168.56.10:8080).
   - En la sección **Completed Applications**, haz clic en `ASBD-Distributed-WordCount`.
   - Podrás observar que se asignaron **Executors en ambos workers** (`worker1` y `worker2`) y que ambos procesaron particiones de datos.

2. **Verificar que el resultado se almacenó en HDFS**:
   ```bash
   # Listar el directorio de salida en HDFS
   docker exec -it namenode hdfs dfs -ls /output/wordcount_result

   # Ver las primeras palabras contadas
   docker exec -it namenode hdfs dfs -cat /output/wordcount_result/part-00000 | head -n 20
   ```

---

## Requisito 4: Tolerancia a Fallos (Worker Caído)

Demostraremos que al caer un nodo worker, los datos siguen estando disponibles en HDFS gracias a la replicación 2.

### 1. Detener el servicio en worker2
Desde otra terminal en tu máquina anfitriona:
```bash
vagrant ssh worker2 -c "docker stop datanode spark-worker"
```
*(O alternativamente: `vagrant halt worker2`)*.

### 2. Verificar la disponibilidad de los datos en HDFS
Desde el nodo master (`vagrant ssh master`), leemos los datos originales y los resultados del trabajo Spark:

```bash
# Leer el fichero original de entrada
docker exec -it namenode hdfs dfs -cat /input/el_quijote.txt | head -n 10

# Leer el resultado del trabajo Spark
docker exec -it namenode hdfs dfs -cat /output/wordcount_result/part-00000 | head -n 10
```

Los datos se leen perfectamente sin errores de E/S porque existe una réplica íntegra en `worker1`.

### 3. Comprobar el informe de salud de HDFS
```bash
docker exec -it namenode hdfs dfsadmin -report
```
Mostrará que hay 1 nodo vivo (`worker1`) y 1 nodo caído/no disponible, pero el sistema mantiene el 100% de los datos accesibles.

### 4. Restaurar el worker detenido
```bash
vagrant ssh worker2 -c "docker start datanode spark-worker"
```
*(O `vagrant up worker2` si se apagó la máquina virtual)*.

En pocos segundos, el DataNode y el Spark Worker volverán a sincronizarse automáticamente con el master.
