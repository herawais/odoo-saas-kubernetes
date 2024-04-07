from kubernetes import client, config
from odoo.exceptions import ValidationError
import logging
from odoo.addons.smile_log.tools import SmileDBLogger


def create_ingress(app_name, self=False):
    _logger = logging.getLogger(__name__)
    if self:
        _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

    # create_ingress
    if not self.domain_name and self.sub_domain_name:
        return ValidationError('Either Domain name or Subdomain name is not Valid')
    else:
        host = self.sub_domain_name + self.domain_name

    networking_v1_api = client.NetworkingV1Api()
    rules = [client.V1IngressRule(
        host=host,
        http=client.V1HTTPIngressRuleValue(
            paths=[
                client.V1HTTPIngressPath(
                    path='/',
                    path_type='ImplementationSpecific',
                    backend=client.V1IngressBackend(
                        service=client.V1IngressServiceBackend(
                            port=client.V1ServiceBackendPort(
                                number=80,
                            ),
                            name=app_name + '-odoo-service', )
                    )
                ),

                client.V1HTTPIngressPath(
                    path='/longpolling/',
                    path_type='ImplementationSpecific',
                    backend=client.V1IngressBackend(
                        service=client.V1IngressServiceBackend(
                            port=client.V1ServiceBackendPort(
                                number=8072,
                            ),
                            name=app_name + '-odoo-service', )
                    )

                )

            ]
        )
    )]
    tls_hosts = [host]

    if self and self.custom_domain_ids:
        for custom_domain in self.custom_domain_ids:
            rules.append(client.V1IngressRule(
                host=custom_domain.name,
                http=client.V1HTTPIngressRuleValue(
                    paths=[
                        client.V1HTTPIngressPath(
                            path='/',
                            path_type='ImplementationSpecific',
                            backend=client.V1IngressBackend(
                                service=client.V1IngressServiceBackend(
                                    port=client.V1ServiceBackendPort(
                                        number=80,
                                    ),
                                    name=app_name + '-odoo-service', )
                            )
                        ),

                        client.V1HTTPIngressPath(
                            path='/longpolling/',
                            path_type='ImplementationSpecific',
                            backend=client.V1IngressBackend(
                                service=client.V1IngressServiceBackend(
                                    port=client.V1ServiceBackendPort(
                                        number=8072,
                                    ),
                                    name=app_name + '-odoo-service', )
                            )

                        )

                    ]

                )

            )
            )
            tls_hosts.append(custom_domain.name)

    body = client.V1Ingress(
        kind='Ingress',
        metadata=client.V1ObjectMeta(name=app_name + '-ingress',
                                     labels={"app": app_name},
                                     annotations={'kubernetes.io/ingress.class': 'nginx',
                                                  'cert-manager.io/cluster-issuer': 'letsencrypt-prod'

                                                  }),
        spec=client.V1IngressSpec(
            rules=rules,
            tls=[client.V1IngressTLS(
                hosts=tls_hosts,
                secret_name=self.app_name + 'tls',
            )]
        )

    )
    try:
        networking_v1_api.create_namespaced_ingress(
            namespace='default',
            body=body
        )
    except client.exceptions.ApiException as e:
        _logger.error(str(e))


def delete_odoo_ingress(app_name, namespace="default", self=False):
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

    networking_v1_api = client.NetworkingV1Api()
    ing_name = app_name + '-ingress'

    try:
        ing = networking_v1_api.delete_namespaced_ingress(name=ing_name, namespace=namespace)
        _logger.info(str(ing))

    except client.exceptions.ApiException as e:
        _logger.error(str(e))


def update_odoo_ingress(app_name, namespace="default", self=False):
    _logger = SmileDBLogger(self._cr.dbname, self._name, self.id, self._uid)

    networking_v1_api = client.NetworkingV1Api()

    ing_name = app_name + '-ingress'

    if not self.domain_name and self.sub_domain_name:
        return ValidationError('Either Domain name or Subdomain name is not Valid')
    else:
        host = self.sub_domain_name + self.domain_name

    rules = [client.V1IngressRule(
        host=host,
        http=client.V1HTTPIngressRuleValue(
            paths=[
                client.V1HTTPIngressPath(
                    path='/',
                    path_type='ImplementationSpecific',
                    backend=client.V1IngressBackend(
                        service=client.V1IngressServiceBackend(
                            port=client.V1ServiceBackendPort(
                                number=80,
                            ),
                            name=app_name + '-odoo-service', )
                    )
                ),

                client.V1HTTPIngressPath(
                    path='/longpolling/',
                    path_type='ImplementationSpecific',
                    backend=client.V1IngressBackend(
                        service=client.V1IngressServiceBackend(
                            port=client.V1ServiceBackendPort(
                                number=8072,
                            ),
                            name=app_name + '-odoo-service', )
                    )

                )

            ]
        )
    )]
    tls_hosts = [host]

    if self and self.custom_domain_ids:
        for custom_domain in self.custom_domain_ids:
            rules.append(client.V1IngressRule(
                host=custom_domain.name,
                http=client.V1HTTPIngressRuleValue(
                    paths=[
                        client.V1HTTPIngressPath(
                            path='/',
                            path_type='ImplementationSpecific',
                            backend=client.V1IngressBackend(
                                service=client.V1IngressServiceBackend(
                                    port=client.V1ServiceBackendPort(
                                        number=80,
                                    ),
                                    name=app_name + '-odoo-service', )
                            )
                        ),

                        client.V1HTTPIngressPath(
                            path='/longpolling/',
                            path_type='ImplementationSpecific',
                            backend=client.V1IngressBackend(
                                service=client.V1IngressServiceBackend(
                                    port=client.V1ServiceBackendPort(
                                        number=8072,
                                    ),
                                    name=app_name + '-odoo-service', )
                            )

                        )

                    ]
                )
            )
            )
            tls_hosts.append(custom_domain.name)

    body = client.V1Ingress(
        kind='Ingress',
        metadata=client.V1ObjectMeta(name=app_name + '-ingress',
                                     labels={"app": app_name},
                                     annotations={'kubernetes.io/ingress.class': 'nginx',
                                                  }),
        spec=client.V1IngressSpec(
            rules=rules,
            tls=[client.V1IngressTLS(
                hosts=tls_hosts,
                secret_name=self.app_name + 'tls'
            )]
        )

    )

    try:
        ing = networking_v1_api.patch_namespaced_ingress(name=ing_name, namespace=namespace, body=body)
        _logger.info(str(ing))
    except client.exceptions.ApiException as e:
        _logger.error(str(e))
