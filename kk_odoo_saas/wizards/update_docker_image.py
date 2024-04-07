from odoo import fields, models, api
import logging
_logger = logging.getLogger(__name__)

class ContainerArgument(models.TransientModel):
    _name = 'saas.app.container.argument'
    _description = "Show the Container Arguments while Updating Docker Image"
    name = fields.Char("Argument Name")
    value = fields.Char("Argument Value")
    update_wizard_id = fields.Many2one('kk_odoo_saas.app.update.dkr.img.wizard')


class ContainerEnvVar(models.TransientModel):
    _name = 'saas.app.container.env.var'
    _description = "Show Container's Env Vars while Updating Docker Image"
    name = fields.Char("Variable Name")
    value = fields.Char("Variable Value")
    value_from = fields.Char("Value From")
    update_wizard_id = fields.Many2one('kk_odoo_saas.app.update.dkr.img.wizard')


class SaaSAppUpdateDockerImage(models.TransientModel):
    _name = "kk_odoo_saas.app.update.dkr.img.wizard"
    _description = "Wizard to Update Docker Image of a SaaS App/Instance"

    def _default_app_id(self):
        res = False
        context = self.env.context
        if context.get("active_model") == "kk_odoo_saas.app" and context.get("active_id"):
            res = context["active_id"]
        return res

    @api.model
    def default_get(self, default_fields):
        deployment_yaml = False
        container_arguments = False
        context = self.env.context
        evs = []

        if context.get("active_model") == "kk_odoo_saas.app" and context.get("active_id"):
            app_id = context["active_id"]
            if app_id:
                app_obj = self.env['kk_odoo_saas.app'].browse(app_id)
                if app_obj:
                    deployment = app_obj.get_odoo_deployment()
                    if deployment:
                        deployment_yaml = str(deployment)
                        container_arguments = deployment.spec.template.spec.containers[0].args
                        container_env_vars = deployment.spec.template.spec.containers[0].env
                        for cev in container_env_vars:
                            evs.append({'name': cev.name, 'value': cev.value, 'value_from': False})

        cas = ['--database=pos', '--without-demo=True']
        container_argument_ids = []
        container_env_var_ids = []

        for i in range(len(cas)):
            key, val = cas[i].split('=')
            if key == '--database':
                if val == app_obj.client_db_name:
                    pass
                else:
                    pass
                    # logic when database name is conflict
            else:
                container_argument_ids.append((0, 0, {'name': key, 'value': val}))

        for i in range(len(evs)):
            container_env_var_ids.append((0, 0, evs[i]))

        contextual_self = self.with_context(default_deployment_yaml=deployment_yaml,
                                            default_container_arguments=container_arguments or '[]',
                                            default_container_argument_ids=container_argument_ids,
                                            default_container_env_var_ids=container_env_var_ids,
                                            )
        return super(SaaSAppUpdateDockerImage, contextual_self).default_get(default_fields)

    app_id = fields.Many2one(
        comodel_name="kk_odoo_saas.app", string="SaaS App", default=lambda r: r._default_app_id()
    )
    deployment_yaml = fields.Text('Yaml of kubernetes Deployment')
    container_arguments = fields.Char()

    container_argument_ids = fields.One2many('saas.app.container.argument', 'update_wizard_id')
    container_env_var_ids = fields.One2many('saas.app.container.env.var', 'update_wizard_id')

    # container_db = fields.Char('Database name from Container')
    # app_db = fields.Char('Database name from App')
    is_cft_db = fields.Char("Is Database name Conflicting")

    def update_docker_image(self):
        if self.app_id:
            envs = []
            for env_var in self.container_env_var_ids:
                envs.append({'name': env_var.name, 'value': env_var.value})
            _logger.info(envs)

            self.app_id.update_docker_image(container_arguments=self.container_arguments, env_vars=envs)
        return {"type": "ir.actions.act_window_close"}
