import copy
import json
import logging
import yaml

import sys
sys.path.append('lib')

from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
)

logger = logging.getLogger()


# DOMAIN MODELS

class AlertManagerJujuPodSpec:

    def __init__(self,
                 app_name,
                 image_path,
                 repo_username,
                 repo_password,
                 advertised_port,
                 alertmanager_config):

        self._spec = {
            'containers': [{
                'name': app_name,
                'imageDetails': {
                    'imagePath': image_path,
                    'username': repo_username,
                    'password': repo_password
                },
                'ports': [{
                    'containerPort': advertised_port,
                    'protocol': 'TCP'
                }],
                'readinessProbe': {
                    'httpGet': {
                        'path': '/-/ready',
                        'port': advertised_port
                    },
                    'initialDelaySeconds': 10,
                    'timeoutSeconds': 30
                },
                'livenessProbe': {
                    'httpGet': {
                        'path': '/-/healthy',
                        'port': advertised_port
                    },
                    'initialDelaySeconds': 30,
                    'timeoutSeconds': 30
                },
                'files': [{
                    'name': 'config',
                    'mountPath': '/etc/alertmanager',
                    'files': {
                        'alertmanager.yml': alertmanager_config.yaml_dump()
                    }
                }]
            }]
        }

    def to_dict(self):
        final = copy.deepcopy(self._spec)
        return final


class AlertManagerConfigFile:
    '''
    https://prometheus.io/docs/alerting/configuration/
    '''

    def __init__(self):
        with open('templates/alertmanager.yml') as am_yaml:
            self._config_dict = yaml.safe_load(am_yaml)

    def yaml_dump(self):
        return yaml.dump(self._config_dict)


class PrometheusAlertingConfig:
    '''
    See the alerting section of:
    https://prometheus.io/docs/prometheus/latest/configuration/configuration
    '''

    def __init__(self, namespace, label_selector):
        self.config_dict = {
            'alertmanagers': [
                {
                    'kubernetes_sd_configs': [
                        {
                            'role': 'pod',
                            'namespaces': {
                                'names': [
                                    namespace
                                ]
                            },
                            'selectors': [
                                {
                                    'role': 'pod',
                                    'label': label_selector
                                }
                            ]
                        }
                    ]
                }
            ]
        }

    def __repr__(self):
        return self.to_json()

    def to_json(self):
        return json.dumps(self.config_dict)


# DOMAIN SERVICES

# More stateless functions. This group is purely business logic that take
# simple values or data structures and produce new values from them.

def build_juju_pod_spec(app_name,
                        charm_config,
                        image_meta):

    # There is never ever a need to customize the advertised port of a
    # containerized Prometheus instance so we are removing that config
    # option and making it statically default to its typical 9090
    advertised_port = 9093

    config = build_alertmanager_config()

    spec = AlertManagerJujuPodSpec(
        app_name=app_name,
        image_path=image_meta.image_path,
        repo_username=image_meta.repo_username,
        repo_password=image_meta.repo_password,
        advertised_port=advertised_port,
        alertmanager_config=config)

    return spec


def build_juju_unit_status(pod_status):
    if pod_status.is_unknown:
        unit_status = MaintenanceStatus("Waiting for pod to appear")
    elif not pod_status.is_running:
        unit_status = MaintenanceStatus("Pod is starting")
    elif pod_status.is_running and not pod_status.is_ready:
        unit_status = MaintenanceStatus("Pod is getting ready")
    elif pod_status.is_running and pod_status.is_ready:
        unit_status = ActiveStatus()

    return unit_status


def build_alertmanager_config():
    return AlertManagerConfigFile()
