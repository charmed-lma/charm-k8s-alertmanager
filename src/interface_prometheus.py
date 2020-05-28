import logging

logger = logging.getLogger()

from ops.framework import (
    EventSource,
    Object,
    ObjectEvents,
)
from ops.framework import EventBase
from adapters.framework import FrameworkAdapter


class NewPrometheusRelationEvent(EventBase):
    pass


class PrometheusEvents(ObjectEvents):
    new_prom_rel = EventSource(NewPrometheusRelationEvent)


class PrometheusInterface(Object):
    on = PrometheusEvents()

    def __init__(self, charm, relation_name):
        super().__init__(charm, relation_name)

        self.fw_adapter = FrameworkAdapter(self.framework)
        self.relation_name = relation_name

        self.fw_adapter.observe(charm.on[relation_name].relation_changed,
                                self.on_relation_changed)

    def on_relation_changed(self, event):
        logger.debug("Emitting new_prom_rel event")
        self.on.new_prom_rel.emit()
        logger.debug("Done emitting new_prom_rel_event")
