from odoo import fields, models


class SaaSAppDelete(models.TransientModel):
    _name = "kk_odoo_saas.app.delete.wizard"
    _description = "Wizard to Destroy a SaaS App/Instance"

    delete_database = fields.Boolean('Delete Database?', default=False)
    delete_pv = fields.Boolean('Delete Attachments and Web Data?', default=False)
    delete_svc = fields.Boolean('Delete Services and Ingress Rules?', default=True)
    delete_ing = fields.Boolean('Delete Ingress Rules?', default=True)
    delete_deployment = fields.Boolean('Delete Container / Pod(s) ?', default=True)


    def _default_app_id(self):
        res = False
        context = self.env.context
        if context.get("active_model") == "kk_odoo_saas.app" and context.get("active_id"):
            res = context["active_id"]
        return res

    app_id = fields.Many2one(
        comodel_name="kk_odoo_saas.app", string="SaaS App", default=lambda r: r._default_app_id()
    )

    def delete_saas_instance(self):
        if self.app_id:
            self.app_id.delete_app_from_wizard(delete_db=self.delete_database, delete_pv=self.delete_pv,
                                               delete_svc=self.delete_svc, delete_ing=self.delete_ing,
                                               delete_deployment=self.delete_deployment)
        return {"type": "ir.actions.act_window_close"}
