# Práctica 1: Clúster Big Data Distribuido con HDFS y Spark

## 1. Introducción y Arquitectura

Esta práctica implementa un clúster Big Data distribuido de 3 nodos totalmente funcional y reproducible utilizando las 3 capas de virtualización y automatización requeridas:

1. **Vagrant**: Aprovisionamiento de infraestructura virtual en VirtualBox (3 máquinas virtuales Ubuntu 22.04 LTS conectadas en una red privada).
2. **Ansible**: Configuración del sistema base, instalación de Docker y Docker Compose, gestión de directorios, configuración de plantillas (`core-site.xml`, `hdfs-site.xml`) y orquestación del arranque de servicios.
3. **Docker**: Empaquetado y aislamiento de los servicios del clúster (**HDFS NameNode**, **HDFS DataNode**, **Spark Master** y **Spark Worker**) utilizando el modo de red `network_mode: host` para garantizar una comunicación directa y transparente entre nodos.

---

## 2. Topología de Red y Servicios

| Nodo | IP Privada | Recursos (RAM / vCPU) | Servicios Docker Desplegados | Puertos Clave |
| :--- | :--- | :--- | :--- | :--- |
| **`master`** | `192.168.56.10` | 2048 MB / 2 vCPUs | • Hadoop NameNode<br>• Spark Master | • 9000 (HDFS RPC)<br>• 9870 (HDFS WebUI)<br>• 7077 (Spark RPC)<br>• 8080 (Spark WebUI) |
| **`worker1`** | `192.168.56.11` | 1536 MB / 1 vCPU | • Hadoop DataNode<br>• Spark Worker | • 9866 (HDFS Data)<br>• 9864 (HDFS WebUI)<br>• 8081 (Spark Worker WebUI) |
| **`worker2`** | `192.168.56.12` | 1536 MB / 1 vCPU | • Hadoop DataNode<br>• Spark Worker | • 9866 (HDFS Data)<br>• 9864 (HDFS WebUI)<br>• 8081 (Spark Worker WebUI) |

### Características Técnicas Relevantes:
- **Factor de Replicación HDFS**: Configurado en `2` (`dfs.replication = 2`). Al contar con 2 DataNodes (`worker1` y `worker2`), cada bloque de datos almacenado en HDFS queda duplicado en ambos workers de forma simultánea.
- **Red de Contenedores (`network_mode: host`)**: Evita que los DataNodes y Workers anuncien ante el Master direcciones IP virtuales de Docker (`172.x.x.x`), enrutando todo el tráfico a través de la red privada `192.168.56.0/24`.
- **Prevención de Caídas OOM**: Se provisiona 1 GB de memoria Swap en cada máquina virtual para garantizar estabilidad durante la ejecución simultánea de los procesos JVM de Hadoop y Spark.

---

## 3. Despliegue Automatizado y Reproducible

El clúster se levanta y configura de manera 100% desatendida desde cero con un único comando:

```bash
vagrant up
```

### ¿Qué hace `vagrant up` automáticamente?
1. Descarga la imagen base `ubuntu/jammy64` si no está descargada en el host.
2. Arranca y configura la red privada de `master` (`192.168.56.10`), `worker1` (`192.168.56.11`) y `worker2` (`192.168.56.12`).
3. Una vez operativas las 3 máquinas virtuales, Vagrant invoca al aprovisionador oficial `ansible` desde el host ejecutando `ansible/playbooks/deploy-bigdata.yml`.
4. Ansible se encarga de toda la configuración interna:
   - Configura la resolución de nombres en `/etc/hosts` y 1 GB de memoria Swap en todos los nodos.
   - Instala Docker CE y Docker Compose en los 3 nodos.
   - Aplica el rol `bigdata` en `master` (crea directorios, formatea el NameNode de forma idempotente y arranca `hadoop-namenode` y `spark-master`).
   - Aplica el rol `bigdata` en los workers (arranca `hadoop-datanode` y `spark-worker`).
   - Realiza un test de salud y muestra el reporte de HDFS con los DataNodes activos.

---

## 4. Interfaces Web de Monitorización

Una vez finalizado el despliegue, puedes acceder desde tu navegador en el equipo anfitrión a las siguientes interfaces web:

- **Spark Master UI**: [http://192.168.56.10:8080](http://192.168.56.10:8080)
  - Muestra el estado del clúster Spark, los 2 Workers registrados (`worker1` y `worker2`), sus núcleos y memoria disponibles, así como las aplicaciones activas y completadas.
- **HDFS NameNode UI**: [http://192.168.56.10:9870](http://192.168.56.10:9870)
  - Muestra el estado del sistema de archivos distribuido, el espacio utilizado y **`Live Nodes: 2`** en la pestaña *Datanodes*.
- **Spark Worker 1 UI**: [http://192.168.56.11:8081](http://192.168.56.11:8081)
- **Spark Worker 2 UI**: [http://192.168.56.12:8081](http://192.168.56.12:8081)

---

## 5. Demostración del Criterio de Éxito: Reparto de Carga Distribuido

Para demostrar que el clúster reparte el trabajo de verdad entre los dos nodos worker y almacena los datos con factor de replicación 2:

1. Conéctate por SSH al nodo master:
   ```bash
   vagrant ssh master
   ```

2. Ejecuta el script de verificación automatizada:
   ```bash
   bash /vagrant/scripts/run_verification.sh
   ```

### ¿Qué comprueba y demuestra este script?
1. **Comprobación de DataNodes**: Ejecuta `hdfs dfsadmin -report` mostrando que ambos nodos (`192.168.56.11` y `192.168.56.12`) están en estado `Normal` y activos.
2. **Almacenamiento y Replicación HDFS**: Sube el fichero `sample_data.txt` a `/input/sample_data.txt` y ejecuta `hdfs fsck ... -files -blocks -locations`, mostrando:
   - Factor de replicación: `replica 2`
   - Bloques alojados simultáneamente en `192.168.56.11` y `192.168.56.12`.
3. **Reparto de Trabajo en Spark**: Lanza mediante `spark-submit` el script PySpark `scripts/distributed_test.py`. El script divide el procesamiento en 4 particiones e inspecciona el host físico que resuelve cada una:
   ```text
   [PASO 1] Auditando qué Worker ejecuta cada partición:
     * Partición #0 ejecutada en: Host 'worker1' (IP: 192.168.56.11)
     * Partición #1 ejecutada en: Host 'worker2' (IP: 192.168.56.12)
     * Partición #2 ejecutada en: Host 'worker1' (IP: 192.168.56.11)
     * Partición #3 ejecutada en: Host 'worker2' (IP: 192.168.56.12)

   ---------------------------------------------------------------------------
   RESUMEN DE NODOS PARTICIPANTES: ['worker1', 'worker2']
   [OK] ÉXITO: El trabajo se ha repartido eficazmente entre los dos workers.
   ---------------------------------------------------------------------------
   ```

---

## 6. Comandos Útiles de Mantenimiento

- **Ver estado de los contenedores en cualquier nodo**:
  ```bash
  docker ps
  ```
- **Ver logs de Spark Master**:
  ```bash
  docker logs -f spark-master
  ```
- **Ver logs de HDFS NameNode**:
  ```bash
  docker logs -f hadoop-namenode
  ```
- **Apagar las máquinas virtuales**:
  ```bash
  vagrant halt
  ```
- **Destruir el clúster completamente**:
  ```bash
  vagrant destroy -f
  ```
