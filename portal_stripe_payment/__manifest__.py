# -*- coding: utf-8 -*-
{
    'name': "Stripe Integration for SaaS Portal",

    'summary': """Stripe Payment Integration for SaaS Portal""",

    'author': "CodeTuple Solutions",
    'website': "https://codetuple.io",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Invoicing',
    'version': '14.0.0.0',
    "license": "OPL-1",
    # 'images': [
    #     'static/description/icon.png',
    # ],

    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'kk_odoo_saas', 'rest_api', 'sale_subscription'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/sale_subscription.xml',
        'views/account_move.xml',
        'views/res_partner.xml',
        # 'views/res_config_settings_views.xml',
    ],
    "application": True,

}
