import os
import sys
from db2dexpo.db2 import Db2Connection
from db2dexpo.prometheus import CustomExporter, INVALID_LABEL_STR
import yaml
import logging
from dotenv import load_dotenv
import asyncio
import re


def db2_instance_connections(config_connections: list):
    db2_connections = {}
    for c in config_connections:
        db_user_var = c.get("db_user_var") if c.get(
            "db_user_var") else "DB2DEXPO_USER"
        db_passwd_var = c.get(
            "db_passwd_var") if c.get("db_passwd_var") else "DB2DEXPO_PASSWD"

        conn = {
            "db_name": c.get("db_name"),
            "db_hostname": c.get("db_host"),
            "db_port": c.get("db_port"),
            "db_user": os.environ.get(db_user_var),
            "db_passwd": os.environ.get(db_passwd_var)
        }

        if not conn["db_name"]:
            logging.fatal(
                "Missing db_name field for connections. Check the connections YAML file.")
            sys.exit(1)

        if not conn["db_hostname"]:
            logging.fatal(
                "Missing db_host field for connections. Check the connections YAML file.")
            sys.exit(1)

        if not conn["db_port"]:
            logging.fatal(
                "Missing db_port field for connections. Check the connections YAML file.")
            sys.exit(1)

        if not conn["db_user"]:
            logging.fatal("Shell variable {} not set.".format(db_user_var))
            sys.exit(1)

        if not conn["db_passwd"]:
            logging.fatal("Shell variable {} not set.".format(db_passwd_var))
            sys.exit(1)

        conn_hash = "{}:{}/{}".format(c["db_host"], c["db_port"], c["db_name"])
        db2_connections[conn_hash] = Db2Connection(**conn)
    return db2_connections


async def db2_keep_connection(db2_conn: Db2Connection, retry_time: int = 60):
    while True:
        db2_conn.connect()
        await asyncio.sleep(retry_time)


async def query_set(config_connection: dict, db2_conn: Db2Connection, config_query: dict, max_conn_labels: list, exporter: CustomExporter):

    default_time_interval = int(os.environ.get(
        "DB2DEXPO_DEFAULT_TIME_INTERVAL", 15))
    if "time_interval" in config_query:
        time_interval = config_query["time_interval"]
    else:
        time_interval = default_time_interval

    while True:
        if db2_conn:
            c_labels = {
                "dbhost": config_connection["db_host"],
                "dbport": config_connection["db_port"],
                "dbname": config_connection["db_name"],
            }
            if "extra_labels" in config_connection:
                c_labels = c_labels | config_connection["extra_labels"]
            c_labels = {i: INVALID_LABEL_STR for i in list(
                max_conn_labels)} | c_labels

            res = db2_conn.execute(
                config_query["query"], config_query["name"])
            g_counter = 0
            for g in config_query["gauges"]:
                if "extra_labels" in g:
                    g_labels = g["extra_labels"]
                else:
                    g_labels = {}

                if "col" in g:
                    col = int(g["col"]) - 1
                else:
                    col = g_counter

                has_special_labels = False
                for v in g_labels.values():
                    if re.match(r'^\$\d+$', v):
                        has_special_labels = True
                        break

                if not has_special_labels:
                    if res:
                        row = res[0]
                        labels = g_labels | c_labels
                        if row and len(row) >= col:
                            exporter.set_gauge(g["name"], row[col], labels)

                else:
                    for row in res:
                        g_labels_aux = g_labels.copy()
                        for k, v in g_labels_aux.items():
                            g_label_index = re.search('^\$(\d+)$', v)
                            if g_label_index:
                                g_label_index = max(
                                    int(g_label_index.group(1))-1, 0)
                                if row and len(row) >= g_label_index:
                                    g_labels_aux[k] = row[g_label_index]
                                else:
                                    g_labels_aux[k] = INVALID_LABEL_STR
                        labels = g_labels_aux | c_labels
                        if row and len(row) >= col:
                            exporter.set_gauge(g["name"], row[col], labels)

                g_counter = g_counter + 1
        await asyncio.sleep(time_interval)


#########################################
# Load YAML config files
#########################################


def load_config_yaml(file_str: str, dict_key: str):
    try:
        with open(file_str, "r") as f:
            file_dict = yaml.safe_load(f)
            if not (type(file_dict) is dict):
                logging.fatal(
                    "Could not parse '{}' as dict".format(file_str))
                sys.exit(1)
            wanted = file_dict.get(dict_key)
            if not (type(wanted) is list):
                logging.fatal(
                    "Could not parse '{}' in file {} as a list".format(dict_key, file_str))
                sys.exit(1)
            return wanted
    except yaml.YAMLError as e:
        logging.fatal("File {} is not a real YAML".format(file_str))
        sys.exit(1)
    except FileNotFoundError:
        logging.fatal("File {} not found".format(file_str))
        sys.exit(1)
    except Exception as e:
        logging.fatal("Could not open file {}".format(file_str))
        sys.exit(1)

#########################################
# Get set of all connection labels
#########################################


def get_labels_list(config_connections: dict):
    max_conn_labels = set()
    for c in config_connections:
        if "extra_labels" in c:
            c_labels = c["extra_labels"]
        else:
            c_labels = set()
        max_conn_labels = max_conn_labels | set(c_labels)
    max_conn_labels.add("dbhost")
    max_conn_labels.add("dbport")
    max_conn_labels.add("dbname")
    return max_conn_labels

#########################################
# Start Prometheus Exporter
# and init metrics
#########################################


def start_prometheus_exporter(config_queries: dict, max_conn_labels: list):
    try:
        custom_exporter = CustomExporter()
        for q in config_queries:
            if "gauges" not in q:
                raise Exception("{} is missing gauges key".format(q))
            for g in q["gauges"]:
                if "extra_labels" in g:
                    labels = g["extra_labels"].keys()
                else:
                    labels = []

                labels = list(max_conn_labels | set(labels))
                name = g.get("name")
                if not name:
                    raise Exception("There are gauge metric missing name")
                desc = g.get("desc") if g.get("desc") else ""
                custom_exporter.create_gauge(name, desc, labels)
        custom_exporter.start()
        return custom_exporter
    except Exception as e:
        logging.fatal("Could not start/init Prometheus Exporter server")
        raise e

#########################################
# Loop: execute query, update metric
#########################################


async def main(config_connections: dict, db2_connections: dict, config_queries: dict, exporter: CustomExporter, max_conn_labels: list):
    executions = []
    try:
        for c in config_connections:

            conn_hash = "{}:{}/{}".format(c["db_host"],
                                          c["db_port"], c["db_name"])
            db2_conn = db2_connections[conn_hash]

            retry_connect_interval = int(os.environ.get(
                "DB2DEXPO_RETRY_CONN_INTERVAL", 60))
            executions.append(
                db2_keep_connection(db2_conn, retry_connect_interval)
            )

            if "tags" not in c:
                tags = set()
            else:
                tags = set(c.get("tags"))

            for q in config_queries:
                if "query" not in q:
                    raise Exception("{} is missing query key".format(q))

                if "runs_on" not in q:
                    runs_on = set()
                else:
                    runs_on = set(q.get("runs_on"))

                if (not tags) or (not runs_on) or (tags & runs_on):
                    executions.append(
                        query_set(c, db2_conn, q, max_conn_labels, exporter))

        await asyncio.gather(*executions)
    except KeyboardInterrupt:
        return None

if __name__ == '__main__':
    try:

        # Loading .env file and setting logger
        try:
            load_dotenv()
        except Exception as e:
            logging.fatal("Could not load .env file")
            raise e

        log_level = logging.getLevelName(
            os.environ.get("DB2DEXPO_LOG_LEVEL", logging.INFO))
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        logging.basicConfig(level=log_level, format=log_format)

        # Checking if variables are valid
        current_variable = ""
        try:
            current_variable = "DB2DEXPO_RETRY_CONN_INTERVAL"
            if int(os.environ.get(current_variable, 60)) < 1:
                raise
            current_variable = "DB2DEXPO_DEFAULT_TIME_INTERVAL"
            if int(os.environ.get(current_variable, 15)) < 1:
                raise
        except Exception:
            logging.fatal("Invalid value for {}".format(current_variable))
            sys.exit(2)

        # Load YAML files
        connections_file = os.environ.get(
            "DB2DEXPO_CONNECTIONS_FILE", "config.yaml")
        queries_file = os.environ.get(
            "DB2DEXPO_QUERIES_FILE", "config.yaml")
        config_connections = load_config_yaml(connections_file, "connections")
        config_queries = load_config_yaml(queries_file, "queries")

        # Get list of maximum of labels that will be used
        max_conn_labels = get_labels_list(config_connections)

        # Instance all db2 connections
        db2_connections = db2_instance_connections(config_connections)

        # Start prometheus exporter and register metrics
        exporter = start_prometheus_exporter(config_queries, max_conn_labels)

        # Start infinite loop to keep Db2 connections and update Prometheus metrics
        main_params = {
            "config_connections": config_connections,
            "db2_connections": db2_connections,
            "config_queries": config_queries,
            "exporter": exporter,
            "max_conn_labels": max_conn_labels
        }
        asyncio.run(main(**main_params))

    except KeyboardInterrupt:
        logging.warning("Db2DExpo stopped")
        sys.exit(5)
