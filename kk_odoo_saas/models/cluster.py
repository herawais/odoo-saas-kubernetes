# -*- coding: utf-8 -*-

from odoo import models, fields


class SaasK8sClusterNS(models.Model):
    _name = 'kk_odoo_saas.app.cluster.ns'
    _description = 'SaaS Cluster NameSpace'

    name = fields.Char()
    status = fields.Char()
    age = fields.Char()
    all_json = fields.Text('Complete json')


class SaasK8sClusterPod(models.Model):
    _name = 'kk_odoo_saas.app.cluster.pod'
    _description = 'SaaS Cluster Pod'

    name = fields.Char()
    ns = fields.Char()
    ready = fields.Char()
    status = fields.Char()
    restarts = fields.Char()
    age = fields.Char()
    all_json = fields.Text('Complete json')


class SaasK8sClusterDeployment(models.Model):
    _name = 'kk_odoo_saas.app.cluster.deployment'
    _description = 'SaaS Cluster Deployment'

    name = fields.Char()
    ns = fields.Char()
    ready = fields.Char()
    age = fields.Char()
    all_json = fields.Text('Complete json')


class SaasK8sClusterIngress(models.Model):
    _name = 'kk_odoo_saas.app.cluster.ingress'
    _description = 'SaaS Cluster Ingress'

    name = fields.Char()
    ns = fields.Char()
    hosts = fields.Char()
    ing_class = fields.Char()
    addresses = fields.Char()
    ports = fields.Char()
    age = fields.Char()
    all_json = fields.Text('Complete json')


class SaasK8sClusterService(models.Model):
    _name = 'kk_odoo_saas.app.cluster.service'
    _description = 'SaaS Cluster Service'

    name = fields.Char()
    type_ = fields.Char()
    cluster_ip = fields.Char()
    external_ip = fields.Char()
    ports = fields.Char()
    age = fields.Char()
    all_json = fields.Text('Complete json')


class SaasK8sClusterPV(models.Model):
    _name = 'kk_odoo_saas.app.cluster.pv'
    _description = 'SaaS Cluster PV'

    name = fields.Char()
    capacity = fields.Char()
    access_modes = fields.Char()
    reclaim_policy = fields.Char()
    status = fields.Char()
    claim = fields.Char()
    storage_class = fields.Char()
    reason = fields.Char()
    age = fields.Char()
    all_json = fields.Text('Complete json')
