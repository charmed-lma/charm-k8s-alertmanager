from base64 import b64encode
import json
import sys
import unittest
from uuid import uuid4
import yaml

sys.path.append('lib')
from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
)

sys.path.append('src')
import domain
from adapters.k8s import (
    PodStatus
)
from adapters.framework import (
    ImageMeta,
)


class BuildAlertManagerConfig(unittest.TestCase):

    def test__it_creates_the_default_config_file(self):
        # Setup
        with open('templates/alertmanager-config-default.yml') as am_yaml:
            expected_config = yaml.safe_load(am_yaml)

        # Exercise
        config = domain.build_alertmanager_config("", "")

        # Assert
        assert yaml.safe_load(config.yaml_dump()) == expected_config

    def test__it_loads_a_base64_encoded_yaml_from_alertmanager_config(self):
        # Setup
        expected_config = {
            str(uuid4()): str(uuid4()),
            str(uuid4()): str(uuid4()),
            str(uuid4()): str(uuid4()),
        }
        base64_config_yaml = \
            b64encode(bytes(yaml.dump(expected_config), 'utf-8'))

        # Exercise
        config = domain.build_alertmanager_config(base64_config_yaml, "")

        # Assert
        assert yaml.safe_load(config.yaml_dump()) == expected_config

    def test__it_loads_a_base64_encoded_yaml_from_alertmanager_secrets(self):
        # Setup
        with open('templates/alertmanager-config-default.yml') as am_yaml:
            expected_config = yaml.safe_load(am_yaml)
        secrets = {
            str(uuid4()): str(uuid4()),
            str(uuid4()): str(uuid4()),
            str(uuid4()): str(uuid4()),
        }
        expected_config.update(secrets)

        base64_secrets_yaml = \
            b64encode(bytes(yaml.dump(expected_config), 'utf-8'))

        # Exercise
        config = domain.build_alertmanager_config("", base64_secrets_yaml)

        # Assert
        assert yaml.safe_load(config.yaml_dump()) == expected_config

    def test__secrets_always_take_precedence(self):
        # Setup
        common_key = str(uuid4())
        common_key_value_in_config = str(uuid4())
        common_key_value_in_secrets = str(uuid4())

        config = {
            str(uuid4()): str(uuid4()),
            str(uuid4()): str(uuid4()),
            str(uuid4()): str(uuid4()),
            common_key: common_key_value_in_config,
        }
        secrets = {
            str(uuid4()): str(uuid4()),
            str(uuid4()): str(uuid4()),
            str(uuid4()): str(uuid4()),
            common_key: common_key_value_in_secrets,
        }

        # Build a new dict without the common key
        expected_config = {k: v for k, v
                           in dict(config, **secrets).items()
                           if k != common_key}
        # Then add back the common key with the secrets value
        expected_config[common_key] = common_key_value_in_secrets

        base64_config_yaml = \
            b64encode(bytes(yaml.dump(config), 'utf-8'))

        base64_secrets_yaml = \
            b64encode(bytes(yaml.dump(secrets), 'utf-8'))

        # Exercise
        config = domain.build_alertmanager_config(base64_config_yaml,
                                                  base64_secrets_yaml)

        # Assert
        assert yaml.safe_load(config.yaml_dump()) == expected_config


class BuildJujuPodSpecTest(unittest.TestCase):

    def test__pod_spec_is_generated(self):
        # Set up
        mock_app_name = str(uuid4())

        mock_external_labels = {
            str(uuid4()): str(uuid4()),
            str(uuid4()): str(uuid4()),
            str(uuid4()): str(uuid4()),
        }

        mock_config = {
            'external-labels': json.dumps(mock_external_labels),
            'monitor-k8s': False
        }

        mock_image_meta = ImageMeta({
            'registrypath': str(uuid4()),
            'username': str(uuid4()),
            'password': str(uuid4()),
        })

        am_config = domain.AlertManagerConfigFile({str(uuid4()): str(uuid4())})

        # Exercise
        juju_pod_spec = domain.build_juju_pod_spec(
            app_name=mock_app_name,
            charm_config=mock_config,
            image_meta=mock_image_meta,
            alertmanager_config=am_config)

        # Assertions
        assert isinstance(juju_pod_spec, domain.AlertManagerJujuPodSpec)
        assert juju_pod_spec.to_dict() == {'containers': [{
            'name': mock_app_name,
            'imageDetails': {
                'imagePath': mock_image_meta.image_path,
                'username': mock_image_meta.repo_username,
                'password': mock_image_meta.repo_password
            },
            'args': [
                '--config.file=/etc/alertmanager/alertmanager.yml',
                '--storage.path=/alertmanager',
                '--cluster.listen-address=0.0.0.0:9094',
                '--cluster.peer=alertmanager-0.alertmanager-endpoints:9094'
            ],
            'ports': [
                {
                    'name': 'web',
                    'containerPort': 9093,
                    'protocol': 'TCP'
                },
                {
                    'name': 'peering-tcp',
                    'containerPort': 9094,
                    'protocol': 'TCP'
                },
                {
                    'name': 'peering-udp',
                    'containerPort': 9094,
                    'protocol': 'UDP'
                }
            ],
            'readinessProbe': {
                'httpGet': {
                    'path': '/-/ready',
                    'port': 9093
                },
                'initialDelaySeconds': 10,
                'timeoutSeconds': 30
            },
            'livenessProbe': {
                'httpGet': {
                    'path': '/-/healthy',
                    'port': 9093
                },
                'initialDelaySeconds': 30,
                'timeoutSeconds': 30
            },
            'files': [{
                'name': 'config',
                'mountPath': '/etc/alertmanager',
                'files': {
                    'alertmanager.yml': am_config.yaml_dump()
                }
            }]
        }]}


class BuildJujuUnitStatusTest(unittest.TestCase):

    def test_returns_maintenance_status_if_pod_status_cannot_be_fetched(self):
        # Setup
        pod_status = PodStatus(status_dict=None)

        # Exercise
        juju_unit_status = domain.build_juju_unit_status(pod_status)

        # Assertions
        assert type(juju_unit_status) == MaintenanceStatus
        assert juju_unit_status.message == "Waiting for pod to appear"

    def test_returns_maintenance_status_if_pod_is_not_running(self):
        # Setup
        status_dict = {
            'metadata': {
                'annotations': {
                    'juju.io/unit': uuid4()
                }
            },
            'status': {
                'phase': 'Pending',
                'conditions': [{
                    'type': 'ContainersReady',
                    'status': 'False'
                }]
            }
        }
        pod_status = PodStatus(status_dict=status_dict)

        # Exercise
        juju_unit_status = domain.build_juju_unit_status(pod_status)

        # Assertions
        assert type(juju_unit_status) == MaintenanceStatus
        assert juju_unit_status.message == "Pod is starting"

    def test_returns_maintenance_status_if_pod_is_not_ready(self):
        # Setup
        status_dict = {
            'metadata': {
                'annotations': {
                    'juju.io/unit': uuid4()
                }
            },
            'status': {
                'phase': 'Running',
                'conditions': [{
                    'type': 'ContainersReady',
                    'status': 'False'
                }]
            }
        }
        pod_status = PodStatus(status_dict=status_dict)

        # Exercise
        juju_unit_status = domain.build_juju_unit_status(pod_status)

        # Assertions
        assert type(juju_unit_status) == MaintenanceStatus
        assert juju_unit_status.message == "Pod is getting ready"

    def test_returns_active_status_if_pod_is_ready(self):
        # Setup
        status_dict = {
            'metadata': {
                'annotations': {
                    'juju.io/unit': uuid4()
                }
            },
            'status': {
                'phase': 'Running',
                'conditions': [{
                    'type': 'ContainersReady',
                    'status': 'True'
                }]
            }
        }
        pod_status = PodStatus(status_dict=status_dict)

        # Exercise
        juju_unit_status = domain.build_juju_unit_status(pod_status)

        # Assertions
        assert type(juju_unit_status) == ActiveStatus
