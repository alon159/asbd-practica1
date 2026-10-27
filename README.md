# Clúster Big Data virtualizado con HDFS y Spark

Diseño y despliegue de un clúster Big Data distribuido con **HDFS** y **Spark** (modo standalone), usando tres capas de virtualización y automatización:

| Capa | Herramienta | Responsabilidad |
| --- | --- | --- |
| Infraestructura | **Vagrant** | Tres máquinas virtuales Ubuntu y red privada |
| Configuración | **Ansible** | Hosts, Docker y contenedores de HDFS/Spark |
| Servicios | **Docker** | NameNode, DataNodes, Spark Master y Spark Workers |

El criterio de éxito no es solo que el clúster arranque: hay que demostrar que el trabajo se reparte entre los dos workers y que la replicación de HDFS mantiene los datos disponibles si cae un nodo.

## Arquitectura

Tres VMs en red privada (`192.168.56.0/24`), imagen `ubuntu/jammy64`:

| Nodo | IP | HDFS | Spark | RAM |
| --- | --- | --- | --- | --- |
| `master` | `192.168.56.10` | NameNode | Spark Master | 1536 MB |
| `worker1` | `192.168.56.11` | DataNode | Spark Worker | 1280 MB |
| `worker2` | `192.168.56.12` | DataNode | Spark Worker | 1280 MB |

- **HDFS**: `fs.defaultFS = hdfs://master:9000`, factor de replicación **2**, permisos desactivados para las pruebas.
- **Spark standalone**: master en `spark://master:7077`; cada worker se registra con 1 core y 1 GB de memoria.
- Los servicios se ejecutan en contenedores (`network_mode: host`) con imágenes [bde2020](https://hub.docker.com/u/bde2020):
  - `bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8`
  - `bde2020/hadoop-datanode:2.0.0-hadoop3.2.1-java8`
  - `bde2020/spark-master:3.0.0-hadoop3.2`
  - `bde2020/spark-worker:3.0.0-hadoop3.2`

```text
Host
 └── Vagrant / VirtualBox
      ├── master   (192.168.56.10)  →  namenode + spark-master
      ├── worker1  (192.168.56.11)  →  datanode + spark-worker
      └── worker2  (192.168.56.12)  →  datanode + spark-worker
```

## Requisitos del host

- [VirtualBox](https://www.virtualbox.org/)
- [Vagrant](https://www.vagrantup.com/)
- Al menos ~4 GB de RAM libres para las tres VMs (~4 GB asignados en total)

No hace falta instalar Ansible ni Docker en el host: Vagrant usa el provisioner `ansible_local` dentro de cada VM.

## Despliegue

Desde la raíz del repositorio:

```bash
vagrant up
```

Ese comando crea las tres VMs, instala Docker y aplica `ansible/site.yml` (roles `common`, `docker`, `master` y `worker`). El clúster queda listo sin pasos manuales.

Comandos útiles:

```bash
vagrant status
vagrant ssh master
vagrant halt
vagrant destroy -f   # derribo completo para volver a desplegar desde cero
```

## Interfaces web

| Servicio | URL |
| --- | --- |
| HDFS NameNode | http://192.168.56.10:9870 |
| Spark Master | http://192.168.56.10:8080 |
| Spark Worker 1 | http://192.168.56.11:8081 |
| Spark Worker 2 | http://192.168.56.12:8081 |

En NameNode (pestaña **Datanodes**) deben verse **2 Live Nodes**. En Spark Master, **2 workers ALIVE**.

También hay reenvío de puertos al host (`9870`, `8080`, `4040`, `8081`/`8082`, `9864`/`9865`) por si se prefiere acceder por `localhost`.

## Estructura del repositorio

```text
.
├── Vagrantfile              # 3 VMs, red privada, ansible_local
├── ansible/
│   ├── inventory.ini        # master / workers y node_ip
│   ├── site.yml             # playbook: common + docker + master/worker
│   └── roles/
│       ├── common/          # /etc/hosts y utilidades de red
│       ├── docker/          # Docker Engine y python3-docker
│       ├── master/          # contenedores namenode y spark-master
│       └── worker/          # contenedores datanode y spark-worker
├── data/el_quijote.txt      # dataset de prueba (montado en el NameNode)
├── jobs/wordcount.py        # WordCount PySpark sobre HDFS
├── TESTING.md               # validación de los 4 requisitos funcionales
└── practica1.md             # enunciado de la práctica
```

El directorio del proyecto se comparte en las VMs como `/vagrant`. El NameNode monta `/vagrant/data` en `/data` y Spark Master monta `/vagrant/jobs` en `/jobs`.

## Pruebas funcionales

La guía detallada está en [`TESTING.md`](TESTING.md). Resumen:

1. **UIs**: NameNode con 2 DataNodes vivos; Spark Master con 2 workers.
2. **HDFS**: subir `el_quijote.txt` y comprobar replicación 2 (`hdfs dfs -ls` y `hdfs fsck`).
3. **Spark**: `spark-submit` de `jobs/wordcount.py` con 2 executors; el resultado se escribe en `hdfs://master:9000/output/wordcount_result` y la UI muestra executors en ambos workers.
4. **Fallo de un worker**: detener DataNode/Spark Worker en `worker2`; los datos siguen leyéndose desde `worker1`.

Ejemplo de subida y trabajo Spark (desde `vagrant ssh master`):

```bash
docker exec -it namenode hdfs dfs -mkdir -p /input
docker exec -it namenode hdfs dfs -put /data/el_quijote.txt /input/el_quijote.txt

docker exec -it spark-master /spark/bin/spark-submit \
  --master spark://master:7077 \
  --deploy-mode client \
  --num-executors 2 \
  --executor-cores 1 \
  --executor-memory 512M \
  /jobs/wordcount.py
```
