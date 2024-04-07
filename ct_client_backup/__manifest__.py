# -*- coding: utf-8 -*-
{
    'name': "Clients Periodic Backups | SaaS",

    'summary': """
        Take Periodic Backups of Client Instances""",

    'description': """
        Take Periodic Backups of Client Instances""",

    'author': "Muhammad Awais",
    'website': "https://codetuple.io",
    'category': 'Uncategorized',
    'version': '2.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'kk_odoo_saas','queue_job'],

    # always loaded
    'data': [
        # "security/security.xml",
        'security/ir.model.access.csv',
        'wizards/backup_restore.xml',
        'views/views.xml',
        'views/app_views.xml',
        'data/backup_ignite_cron.xml',
    ],
    "application": True,

}
