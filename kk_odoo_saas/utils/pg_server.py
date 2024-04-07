from psycopg2 import sql, connect
import odoo
from contextlib import closing
import logging
from odoo.exceptions import AccessError, UserError
from .utils import generate_temp_password
_logger = logging.getLogger(__name__)


def drop_db(self, db_name):
    if self:
        child_conn = self.get_pg_db_connection(db=db_name)
        child_conn.set_session(autocommit=True)

        with closing(child_conn.cursor()) as cr:
            odoo.service.db._drop_conn(cr, db_name)
            try:
                cr.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(db_name)))
            except Exception as e:
                _logger.info('DROP DB: %s failed:\n%s', db_name, e)
                child_conn.close()
                raise UserError("Couldn't drop database %s: %s" % (db_name, e))
            else:
                child_conn.close()
                _logger.info('DROP DB: %s', db_name)
        return True


def delete_databases(self):
    if self and self.client_db_name:
        # dbs = get_databases(self)
        drop_db(self, self.client_db_name)


def get_admin_credentials(self):
    if self and self.client_db_name:
        # FOR admin user_id = 2
        child_conn = self.get_pg_db_connection(db=self.client_db_name)
        query = sql.SQL("SELECT login, COALESCE(password, '') FROM res_users WHERE id=2;")
        with closing(child_conn.cursor()) as cr:
            try:
                cr.execute(query)
                res = cr.fetchall()
                child_conn.close()
            except Exception:
                _logger.exception('Getting Credentials failed')
                res = False
                child_conn.close()
        return res, self.client_db_name
    return False, False
