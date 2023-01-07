from prometheus_client import start_http_server, Gauge
import os
from dotenv import load_dotenv
import logging

INVALID_LABEL_STR = "-"

logger = logging.getLogger(__name__)

try:
    load_dotenv()
except Exception as e:
    logger.fatal("Could not load .env file")
    raise e


class CustomExporter:
    def __init__(self) -> None:
        self.metric_dict = {}

    def create_gauge(self, metric_name: str, metric_desc: str, metric_labels: list = []):
        if self.metric_dict.get(metric_name) is None:
            try:
                if metric_labels:
                    self.metric_dict[metric_name] = Gauge(
                        metric_name, metric_desc, metric_labels)
                else:
                    self.metric_dict[metric_name] = Gauge(
                        metric_name, metric_desc)
                logger.info("[GAUGE] [{}] created".format(metric_name))
            except KeyboardInterrupt as e:
                raise e
            except Exception as e:
                logger.fatal(
                    "[GAUGE] [{}] failed to create".format(metric_name))
                raise e

    def set_gauge(self, metric_name: str, metric_value: float, metric_labels: dict = {}):
        try:
            if metric_labels:
                self.metric_dict[metric_name].labels(
                    **metric_labels).set(metric_value)
            else:
                self.metric_dict[metric_name].set(metric_value)
            labels = ', '.join(f'{key}: "{value}"' for key,
                               value in metric_labels.items())
            logger.debug("[GAUGE] [{}{{{}}}] {}".format(
                metric_name, labels, metric_value))
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            logger.error(
                "[GAUGE] [{}] failed to update: {}".format(metric_name, e))

    def start(self):
        try:
            exporter_port = int(os.environ.get("DB2DEXPO_PORT", "9877"))
            start_http_server(exporter_port)
            logger.info(
                "Db2DExpo server started at port {}".format(exporter_port))
        except Exception as e:
            logger.fatal(
                "Failed to start Db2DExpo server at port {}".format(exporter_port))
            raise e
