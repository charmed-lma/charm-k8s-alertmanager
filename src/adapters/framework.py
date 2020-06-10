import logging
from ops.framework import Object
from ops.model import (
    BlockedStatus,
    ModelError,
)
import os
import yaml

logger = logging.getLogger()


# MODELS

class ImageMeta(Object):

    def __init__(self, resource_dict):
        self.resource_dict = resource_dict

    @property
    def image_path(self):
        return self.resource_dict['registrypath']

    @property
    def repo_username(self):
        return self.resource_dict['username']

    @property
    def repo_password(self):
        return self.resource_dict['password']


class ResourceError(ModelError):

    def __init__(self, resource_name, message):
        super().__init__(resource_name)
        msg = "{}: {}".format('resource_name', 'message')
        self.status = BlockedStatus(msg)


# SERVICES

def _fetch_image_meta(image_name, resources_repo):
    path = resources_repo.fetch(image_name)
    if not path.exists():
        msg = 'Resource not found at {}'.format(path)
        raise ResourceError(image_name, msg)

    resource_yaml = path.read_text()

    if not resource_yaml:
        msg = 'Resource unreadable at {}'.format(path)
        raise ResourceError(image_name, msg)

    try:
        resource_dict = yaml.safe_load(resource_yaml)
    except yaml.error.YAMLError:
        msg = 'Invalid YAML at {}'.format(path)
        raise ResourceError(image_name, msg)
    else:
        return ImageMeta(resource_dict=resource_dict)


def _read_resource_file(resource_name, resources_repo):
    logger.debug("Fetch path for resource {}".format(resource_name))

    try:
        path = resources_repo.fetch(resource_name)
    except ModelError as err:
        msg = "Resource '{}' does not exist: {}".format(resource_name, err)
        logger.error(msg)
        raise ResourceError(resource_name, msg)

    if not path.exists():
        msg = "Resource not found at {}".format(path)
        logger.error(msg)
        raise ResourceError(resource_name, msg)

    logger.debug("Resource found at {}".format(path))

    file_contents = path.read_text()

    if file_contents:
        return file_contents
    else:
        msg = "Resource unreadable at {}".format(path)
        raise ResourceError(resource_name, msg)


class FrameworkAdapter:
    '''
    Abstracts out the implementation details of the underlying framework
    so that our Charm object's code is decoupled from it and simplifies
    its own implementation. This is inspired by Alistair Cockburn's
    Hexagonal Architecture.
    '''

    def __init__(self, framework):
        self._framework = framework

    def am_i_leader(self):
        return self._framework.model.unit.is_leader()

    def get_app_name(self):
        return self._framework.model.app.name

    def get_config(self, key=None):
        if key:
            return self._framework.model.config[key]
        else:
            return self._framework.model.config

    def get_image_meta(self, image_name):
        return _fetch_image_meta(image_name, self.get_resources_repo())

    def get_model_name(self):
        return os.environ["JUJU_MODEL_NAME"]

    def get_relations(self, relation_name):
        return self._framework.model.relations[relation_name]

    def read_resource_file(self, resource_name):
        return _read_resource_file(resource_name, self.get_resources_repo())

    def get_resources_repo(self):
        return self._framework.model.resources

    def get_unit(self):
        return self._framework.model.unit

    def get_unit_name(self):
        return os.environ["JUJU_UNIT_NAME"]

    def observe(self, event, handler):
        self._framework.observe(event, handler)

    def set_pod_spec(self, spec_obj):
        self._framework.model.pod.set_spec(spec_obj)

    def set_unit_status(self, state_obj):
        self._framework.model.unit.status = state_obj
