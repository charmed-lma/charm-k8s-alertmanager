import logging

logger = logging.getLogger()

from ops.framework import (
    EventSource,
    Object,
    ObjectEvents,
)
from ops.framework import EventBase
from adapters.framework import FrameworkAdapter


class PrometheusAlertingConfig:

    def __init__(self, config_dict={}):
        self.config_dict = config_dict

    def __getitem__(self, key):
        return self.config_dict[key]

    def __setitem__(self, key, value):
        self.config_dict[key] = value

    def __repr__(self):
        return str(self.config_dict)

    @classmethod
    def restore(cls, snapshot):
        logger.debug("PrometheusAlertingConfig.restore")
        logger.debug("  Restoring {}".format(snapshot))

        return cls(config_dict=snapshot)

    def snapshot(self):
        logger.debug("PrometheusAlertingConfig.snapshot")
        logger.debug("  Snapshotting {}".format(self.config_dict))

        return self.config_dict


class NewPrometheusClientEvent(EventBase):

    # alerting_config here is explicitly provided to the `emit()` call inside
    # `PrometheusInterface.on_relation_changed` below. `handle` on the other
    # hand is automatically provided by `emit()`
    def __init__(self, handle, alerting_config):
        logger.debug("NewPrometheusClientEvent.__init__")
        logger.debug("  alerting_config={}".format(alerting_config))

        super().__init__(handle)
        self.alerting_config = alerting_config

    def snapshot(self):
        snapshot = self.alerting_config.snapshot()

        logger.debug("NewPrometheusClientEvent.snapshot")
        logger.debug("  Snapshotting {}".format(snapshot))

        return snapshot

    def restore(self, snapshot):
        logger.debug("NewPrometheusClientEvent.restore")
        logger.debug("  Restoring {}".format(snapshot))

        self.alerting_config = PrometheusAlertingConfig.restore(snapshot)


class PrometheusEvents(ObjectEvents):
    new_prom_client = EventSource(NewPrometheusClientEvent)


class PrometheusInterface(Object):
    on = PrometheusEvents()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)

        self.fw_adapter = FrameworkAdapter(self.framework)
        self.relation_name = relation_name

        self.fw_adapter.observe(charm.on[relation_name].relation_changed,
                                self.on_relation_changed)

    def on_relation_changed(self, event):
        alerting_config = PrometheusAlertingConfig()
        alerting_config['foo'] = 'bar'

        logger.debug('PrometheusInterface.on_relation_changed')
        logger.debug('  Sending alerting config: {}'.format(alerting_config))

        self.on.new_prom_client.emit(alerting_config)

        logger.debug('PrometheusInterface.on_relation_changed')
        logger.debug('  Got alerting config: {}'.format(alerting_config))


# def render_relation_data(self):
#     logging.debug('render-relation-data in')
#     for relation in self.model.relations[self.relation_name]:
#         relation.data[self.model.unit]['prometheus-port'] = '9090'
#     logging.debug('render-relation-data out')
