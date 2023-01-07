# Db2DExpo

> Dynamic Prometheus exporter for Db2 in Python

Db2DExpo is Prometheus exporter for Db2, fully configurable (both which metrics to export and which databases to connect) via YAML files.

Write your own SQL queries, run them against one or more databases and create gauge metrics for them. This way, you can create metrics for both Db2 level monitoring (e.g. Bufferpool performance, hit ratio, database size, etc.) and your own database applications.

For each query you can define multiple gauge metrics, one for each column from the SQL result set. It's also possible to create dynamic labels for the metrics (for instance, setting a label with bufferpool names).

Each query for each database is run asynchronously. Time interval between runs is configurable in the YAML.

All the database connections are persistent. If during execution any database connection is dropped, the application will keep retrying connection (interval also configurable via variable).

Check the example [config.yaml](config.example.yaml) for all configurations.

## Running locally

You need to have Python version 3.10.8 and pip installed.

Clone this repo:

```shell
git clone https://github.com/arapozojr/db2dexpo.git
cd db2dexpo/
```

Install all required packages using pip:

```shell
pip3 install -r requirements.txt
```

Create .env file with at least the user and password that will be used for database connections:

```shell
cat << EOF > .env
DB2DEXPO_USER=
DB2DEXPO_PASSWD=
DB2DEXPO_CONNECTIONS_FILE=config.yaml
DB2DEXPO_QUERIES_FILE=config.yaml
DB2DEXPO_LOG_LEVEL=INFO
DB2DEXPO_RETRY_CONN_INTERVAL=60
EOF
```

Check [the example config YAML](config.example.yaml) on how to handle multiple databases with different access. Use this example YAML to also make your own config.yaml file, with your queries and gauge metrics.

Run the application:

```shell
python3 app.py
```

Set DB2DEXPO_LOG_LEVEL to DEBUG to show query executions and metric updates.

Example output of application startup:

```text
2023-01-07 10:24:16,858 - db2dexpo.prometheus - INFO - [GAUGE] [db2_applications_count] created
2023-01-07 10:24:16,859 - db2dexpo.prometheus - INFO - [GAUGE] [db2_lockwaits_count] created
2023-01-07 10:24:16,859 - db2dexpo.prometheus - INFO - [GAUGE] [db2_lockwaits_maxwait_seconds] created
2023-01-07 10:24:16,859 - db2dexpo.prometheus - INFO - [GAUGE] [db2_employees_created] created
2023-01-07 10:24:16,860 - db2dexpo.prometheus - INFO - Db2DExpo server started at port 9877
2023-01-07 10:24:17,232 - db2dexpo.db2 - INFO - [127.0.0.1:50000/sample] connected
```

You can then open [http://localhost:9877/](http://localhost:9877/) and see the exported metrics.

Ctrl+c will stop the application.

## Running in Docker

Clone this repo:

```shell
git clone https://github.com/arapozojr/db2dexpo.git
cd db2dexpo/
```

Create .env file with at least the user and password that will be used for database connections:

```shell
cat << EOF > .env
DB2DEXPO_USER=
DB2DEXPO_PASSWD=
DB2DEXPO_CONNECTIONS_FILE=config.yaml
DB2DEXPO_QUERIES_FILE=config.yaml
DB2DEXPO_LOG_LEVEL=INFO
DB2DEXPO_RETRY_CONN_INTERVAL=60
EOF
```

Check [the example config YAML](config.example.yaml) on how to handle multiple databases with different access. Use this example YAML to also make your own config.yaml file, with your queries and gauge metrics.

Build Docker image:

```shell
docker build -t db2prompy .
```

Run a container:

```shell
docker run --name db2dexpo -it --env-file .env db2dexpo
```

See the exported metrics:

```shell
docker exec -it db2dexpo curl 127.0.0.1:9877
```

Example output:

```text
...
# HELP db2_applications_count Amount of applications connected and their states
# TYPE db2_applications_count gauge
db2_applications_count{appname="myapp",appstate="UOWWAIT",db2instance="db2inst1",dbhost="127.0.0.1",dbname="sample",dbport="50000",dbenv="test"} 5.0
db2_applications_count{appname="myapp",appstate="UOWEXEC",db2instance="db2inst1",dbhost="127.0.0.1",dbname="sample",dbport="50000",dbenv="test"} 2.0
db2_applications_count{appname="db2bp",appstate="UOWEXEC",db2instance="db2inst1",dbhost="127.0.0.1",dbname="sample",dbport="50000",dbenv="test"} 1.0
# HELP db2_lockwaits_count Amount of lockwaits
# TYPE db2_lockwaits_count gauge
db2_lockwaits_count{db2instance="db2inst1",dbhost="127.0.0.1",dbname="sample",dbport="50000",dbenv="test"} 0.0
# HELP db2_lockwaits_maxwait_seconds Maximum number of seconds apps are waiting to get lock
# TYPE db2_lockwaits_maxwait_seconds gauge
db2_lockwaits_maxwait_seconds{db2instance="db2inst1",dbhost="127.0.0.1",dbname="sample",dbport="50000",dbenv="test"} 0.0
# HELP db2_employees_created Number of employees
# TYPE db2_employees_created gauge
db2_employees_created{db2instance="db2inst1",dbhost="127.0.0.1",dbname="sample",dbport="50000",dbenv="test",persontype="employee"} 1442.0
```
