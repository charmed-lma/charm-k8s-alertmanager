from base64 import b64decode
import copy
import json
import logging
import yaml

from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
)

logger = logging.getLogger(__name__)


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

    def __init__(self, config_dict):
        self._config_dict = config_dict

    # Algorithm adapted from https://stackoverflow.com/a/7205107
    def _merge(self, a, b, path=None):
        "merges b into a"
        if path is None:
            path = []
        for key in b:
            if key in a:
                if isinstance(a[key], dict) and isinstance(b[key], dict):
                    self._merge(a[key], b[key], path + [str(key)])
                elif a[key] == b[key]:
                    pass  # same leaf value
                else:
                    # b always takes precedence
                    a[key] = b[key]
            else:
                a[key] = b[key]
        return a

    def update(self, other_dict):
        self._config_dict = self._merge(self._config_dict, other_dict)

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

def build_alertmanager_config(base64_config_yaml, base64_secrets_yaml):

    if base64_config_yaml:
        logger.debug("Decoding base64_config_yaml")
        config_yaml = b64decode(base64_config_yaml)

        logger.debug("Loading config_yaml to dict")
        config_dict = yaml.safe_load(config_yaml)
    else:
        default_config_path = 'templates/alertmanager-config-default.yml'
        logger.warning("Could not find alertmanager-config string. "
                       "Loading default config from {} instead. This instance"
                       "is NOT RECOMMENDED for production use".format(
                           default_config_path
                       ))
        with open(default_config_path) as default_config_yaml:
            config_dict = yaml.safe_load(default_config_yaml)

    alertmanager_config = AlertManagerConfigFile(config_dict)

    if base64_secrets_yaml:
        logger.debug("Decoding base64_secrets_yaml")
        secrets_yaml = b64decode(base64_secrets_yaml)

        logger.debug("Loading secrets_yaml to dict")
        secrets_dict = yaml.safe_load(secrets_yaml)

        logger.debug("Updating AlertManager configuration with secrets")
        alertmanager_config.update(secrets_dict)
    else:
        logger.info("alertmanager-secrets not provided. Ignoring")

    return alertmanager_config


def build_juju_pod_spec(app_name,
                        charm_config,
                        image_meta,
                        alertmanager_config):

    # There is never ever a need to customize the advertised port of a
    # containerized Prometheus instance so we are removing that config
    # option and making it statically default to its typical 9090
    advertised_port = 9093

    # TODO: Add logic here to decide whether to use V1 or V2 JujuPodSpec
    #       based on Juju version. NOTE: Only Juju 2.7 up supports V2.
    spec = AlertManagerJujuPodSpec(
        app_name=app_name,
        image_path=image_meta.image_path,
        repo_username=image_meta.repo_username,
        repo_password=image_meta.repo_password,
        advertised_port=advertised_port,
        alertmanager_config=alertmanager_config)

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
