from odoo.http import route, request, Controller
import logging
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)


class SaaSAppsLogViewer(CustomerPortal):
    @route("/saas/instance/<int:app_id>", type="http", auth="user", methods=['GET'], website=True)
    def saas_app_log_viewer(self, app_id, **values):
        saas_app = request.env["kk_odoo_saas.app"].sudo().browse(app_id)
        if request.params.get('_'):
            logs = saas_app.get_timed_pod_logs(since_seconds=5)
            return logs
        return request.render(
            "kk_odoo_saas.saas_app_log_viewer", values
        )
