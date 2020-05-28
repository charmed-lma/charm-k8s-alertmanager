import sys
import unittest
from unittest.mock import (
    call,
    create_autospec,
    MagicMock,
    patch
)
from uuid import uuid4

sys.path.append('lib')
from ops.framework import (
    EventBase,
)
from ops.model import (
    ActiveStatus,
    MaintenanceStatus,
)
from ops.testing import (
    Harness,
)

sys.path.append('src')
from adapters import (
    framework,
)
import charm
import domain


class CharmTest(unittest.TestCase):

    @patch('charm.k8s', spec_set=True, autospec=True)
    @patch('charm.build_juju_unit_status', spec_set=True, autospec=True)
    def test__init__starts_up_without_a_hitch(
        self,
        mock_build_juju_unit_status_func,
        mock_k8s_mod,
    ):
        # Setup
        harness = Harness(charm.Charm)
        harness.begin()


class OnConfigChangedHandlerTest(unittest.TestCase):

    # We are mocking the time module here so that we don't actually wait
    # 1 second per loop during test exectution.
    @patch('charm.build_juju_unit_status', spec_set=True, autospec=True)
    @patch('charm.k8s', spec_set=True, autospec=True)
    @patch('charm.time', spec_set=True, autospec=True)
    @patch('charm.build_juju_pod_spec', spec_set=True, autospec=True)
    @patch('charm.set_juju_pod_spec', spec_set=True, autospec=True)
    def test__it_blocks_until_pod_is_ready(
            self,
            mock_pod_spec,
            mock_juju_pod_spec,
            mock_time,
            mock_k8s_mod,
            mock_build_juju_unit_status_func):
        # Setup
        mock_fw_adapter_cls = \
            create_autospec(framework.FrameworkAdapter, spec_set=True)
        mock_fw_adapter = mock_fw_adapter_cls.return_value

        mock_juju_unit_states = [
            MaintenanceStatus(str(uuid4())),
            MaintenanceStatus(str(uuid4())),
            ActiveStatus(str(uuid4())),
        ]
        mock_build_juju_unit_status_func.side_effect = mock_juju_unit_states

        mock_event_cls = create_autospec(EventBase, spec_set=True)
        mock_event = mock_event_cls.return_value

        # Exercise
        charm.on_config_changed_handler(mock_event, mock_fw_adapter)

        # Assert
        assert mock_fw_adapter.set_unit_status.call_count == \
            len(mock_juju_unit_states)
        assert mock_fw_adapter.set_unit_status.call_args_list == [
            call(status) for status in mock_juju_unit_states
        ]


class OnNewPromRelHandlerTest(unittest.TestCase):

    @patch('charm.PrometheusAlertingConfig', spec_set=True, autospec=True)
    def test__it_sets_the_relation_data_correctly(
            self,
            mock_prometheus_alerting_config_cls):
        # Setup
        mock_alerting_conf = mock_prometheus_alerting_config_cls.return_value
        mock_fw_adapter_cls = \
            create_autospec(framework.FrameworkAdapter,
                            spec_set=True)
        mock_fw_adapter = mock_fw_adapter_cls.return_value
        mock_fw_adapter.am_i_leader.return_value = True
        mock_fw_adapter.get_model_name.return_value = str(uuid4())
        mock_fw_adapter.get_app_name.return_value = str(uuid4())

        mock_relation1 = MagicMock()
        mock_data_bag = MagicMock()
        mock_relation1.data = \
            {mock_fw_adapter.get_unit.return_value: mock_data_bag}

        relations = MagicMock()
        relations.__iter__.return_value = [
            mock_relation1,
        ]
        mock_fw_adapter.get_relations.return_value = relations

        mock_event_cls = create_autospec(EventBase, spec_set=True)
        mock_event = mock_event_cls.return_value

        mock_rel_name = str(uuid4())

        # Exercise
        charm.on_new_prom_rel_handler(mock_event,
                                      mock_fw_adapter,
                                      mock_rel_name)

        # Assert
        assert mock_data_bag.update.call_count == 1
        assert mock_data_bag.update.call_args == \
            call({'alerting_config': mock_alerting_conf.to_json.return_value})


class OnStartHandlerTest(unittest.TestCase):

    @patch('charm.build_juju_pod_spec', spec_set=True, autospec=True)
    def test__it_updates_the_juju_pod_spec(self,
                                           mock_build_juju_pod_spec_func):
        # Setup
        mock_fw_adapter_cls = \
            create_autospec(framework.FrameworkAdapter,
                            spec_set=True)
        mock_fw = mock_fw_adapter_cls.return_value
        mock_fw.am_i_leader.return_value = True

        mock_event_cls = create_autospec(EventBase, spec_set=True)
        mock_event = mock_event_cls.return_value

        mock_juju_pod_spec = create_autospec(domain.AlertManagerJujuPodSpec)
        mock_build_juju_pod_spec_func.return_value = mock_juju_pod_spec

        # Exercise
        charm.on_start_handler(mock_event, mock_fw)

        # Assert
        assert mock_build_juju_pod_spec_func.call_count == 1
        assert mock_build_juju_pod_spec_func.call_args == \
            call(app_name=mock_fw.get_app_name.return_value,
                 charm_config=mock_fw.get_config.return_value,
                 image_meta=mock_fw.get_image_meta.return_value)

        assert mock_fw.set_pod_spec.call_count == 1
        assert mock_fw.set_pod_spec.call_args == \
            call(mock_juju_pod_spec.to_dict())

        assert mock_fw.set_unit_status.call_count == 1
        args, kwargs = mock_fw.set_unit_status.call_args_list[0]
        assert type(args[0]) == MaintenanceStatus
