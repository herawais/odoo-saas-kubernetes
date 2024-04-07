from .service import create_odoo_service, delete_odoo_service
from .deployment import create_odoo_deployment, delete_odoo_deployment
from .pv_claim import create_odoo_pv_claim, delete_odoo_pv_claim
from .ingress import delete_odoo_ingress, update_odoo_ingress
from .utils import delete_job_task


def deploy_odoo_components(app_name, namespace, self=False):
    create_odoo_pv_claim(app_name, namespace, self=self)
    create_odoo_service(app_name, namespace, self=self)
    create_odoo_deployment(app_name, namespace, self=self)


def delete_odoo_components(app_name, namespace, self=False):
    delete_odoo_pv_claim(app_name, namespace, self=self)
    delete_odoo_service(app_name, namespace, self=self)
    delete_odoo_deployment(app_name, namespace, self=self)
    delete_odoo_ingress(app_name, namespace, self=self)
    delete_job_task(self)


def delete_odoo_components_from_options(app_name, namespace, self=False, delete_db=False,
                                            delete_pv=False, delete_svc=False,
                                            delete_ing=False, delete_deployment=False):
    if delete_pv:
        delete_odoo_pv_claim(app_name, namespace, self=self)
    if delete_svc:
        delete_odoo_service(app_name, namespace, self=self)
    if delete_deployment:
        delete_odoo_deployment(app_name, namespace, self=self)
    if delete_ing:
        delete_odoo_ingress(app_name, namespace, self=self)
    delete_job_task(self)


def update_odoo_components(app_name, namespace, self=False):
    update_odoo_ingress(app_name, namespace, self)
