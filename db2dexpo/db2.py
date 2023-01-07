import ibm_db
import logging
import sys

logger = logging.getLogger(__name__)

APPLICATION_NAME = "DB2DEXPO"


class Db2Connection:
    def connect(self):
        options = {
            ibm_db.SQL_ATTR_INFO_PROGRAMNAME: APPLICATION_NAME,
            ibm_db.SQL_ATTR_INFO_WRKSTNNAME: APPLICATION_NAME,
            ibm_db.SQL_ATTR_INFO_ACCTSTR: APPLICATION_NAME,
            ibm_db.SQL_ATTR_INFO_APPLNAME: APPLICATION_NAME
        }
        try:
            if not self.conn:
                conn = ibm_db.pconnect(self.connection_string, "", "", options)
                logger.info("[{}] connected".format(
                    self.connection_string_print))
                self.conn = conn
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            logger.error("[{}] {}".format(self.connection_string_print, e))
            self.conn = None

    def __init__(self, db_name: str, db_hostname: str, db_port: str, db_user: str, db_passwd: str):
        self.connection_string = "DATABASE={};HOSTNAME={};PORT={};PROTOCOL=TCPIP;UID={};PWD={};".format(
            db_name, db_hostname, db_port, db_user, db_passwd)
        self.connection_string_print = "{}:{}/{}".format(
            db_hostname, db_port, db_name)
        self.conn = None

    def execute(self, query: str, name: str):
        try:
            if not self.conn:
                return []
            result = ibm_db.exec_immediate(self.conn, query)

            logger.debug("[{}] [{}] executed".format(
                self.connection_string_print, name))

            rows = []
            row = list(ibm_db.fetch_tuple(result))
            while(row):
                rows.append(row)
                row = ibm_db.fetch_tuple(result)

            return rows
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            logger.warning("[{}] [{}] failed to execute".format(
                self.connection_string_print, name))
            return [[]]
