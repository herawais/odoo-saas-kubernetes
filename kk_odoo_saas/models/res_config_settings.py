from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    show_packages = fields.Boolean(
        "Show packages", config_parameter="kk_odoo_saas.show_packages"
    )
    show_apps = fields.Boolean("Show apps", config_parameter="kk_odoo_saas.show_apps")
    show_buy_now_button = fields.Boolean(
        "Show 'Buy now' button", config_parameter="kk_odoo_saas.show_buy_now_button"
    )
    show_try_trial_button = fields.Boolean(
        "Show 'Try trial' button", config_parameter="kk_odoo_saas.show_try_trial_button"
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        select_type = self.env["ir.config_parameter"].sudo()
        packages = select_type.get_param("kk_odoo_saas.show_packages")
        apps = select_type.get_param("kk_odoo_saas.show_apps")
        buy_now_button = select_type.get_param("kk_odoo_saas.show_buy_now_button")
        try_trial_button = select_type.get_param("kk_odoo_saas.show_try_trial_button")
        # fmt: off
        res.update({
            "show_packages": packages,
            "show_apps": apps,
            "show_buy_now_button": buy_now_button,
            "show_try_trial_button": try_trial_button,
        })
        # fmt: on
        return res
