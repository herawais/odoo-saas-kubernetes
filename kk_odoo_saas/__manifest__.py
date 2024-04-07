# -*- coding: utf-8 -*-
{
    'name': "CT Odoo SaaS",

    'summary': """
        Out of the Box SaaS Module based on Kubernetes""",

    'description': """
        Out of the Box SaaS Module based on Kubernetes
                    """,

    'author': "Muhammad Awais",
    'website': "https://codetuple.io",
    'category': 'Uncategorized',
    'version': '2.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'smile_log', 'website_sale', 'product',
                'portal', 'auth_signup_verify_email', 'sale_subscription',
                'queue_job'],

    'external_dependencies': {
        'python': [
            'kubernetes',
        ],
    },
    # always loaded
    'data': [
        "security/security.xml",
        'security/ir.model.access.csv',
        'wizards/saas_app_delete.xml',
        'wizards/update_docker_image.xml',
        'views/app_views.xml',
        'views/config_views.xml',
        'views/assets.xml',
        'views/saas_app_website.xml',
        'views/templates.xml',
        'views/sale_subscription.xml',
        'views/logs_viewer.xml',
        'views/res_config_settings_views.xml',
        'views/saas_package_views.xml',
        'data/data.xml',
        'data/email_templates.xml',
    ],
    'qweb': [
        'static/src/xml/base.xml',
             ],
    "application": True,

}
