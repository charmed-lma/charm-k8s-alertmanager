import json
import http.client
import logging
logger = logging.getLogger()
import ssl


def get_pod_status(juju_model, juju_app, juju_unit):
    namespace = juju_model

    path = '/api/v1/namespaces/{}/pods?' \
           'labelSelector=juju-app={}'.format(namespace, juju_app)

    api_server = APIServer()
    response = api_server.get(path)
    status_dict = None

    if response.get('kind', '') == 'PodList' and response['items']:
        status_dict = next(
            (i for i in response['items']
             if i['metadata']['annotations'].get('juju.io/unit') == juju_unit),
            None
        )

    return PodStatus(status_dict)


class APIServer:
    """
    Wraps the logic needed to access the k8s API server from inside a pod.
    It does this by reading the service account token which is mounted onto
    the pod.
    """

    def get(self, path):
        return self.request('GET', path)

    def request(self, method, path):
        with open("/var/run/secrets/kubernetes.io/serviceaccount/token") \
                as token_file:
            kube_token = token_file.read()

        ssl_context = ssl.SSLContext()
        ssl_context.load_verify_locations(
            '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt')

        headers = {
            'Authorization': 'Bearer {}'.format(kube_token)
        }

        host = 'kubernetes.default.svc'
        conn = http.client.HTTPSConnection(host, context=ssl_context)
        logger.debug("{} {}/{}".format(method, host, path))
        conn.request(method=method, url=path, headers=headers)

        return json.loads(conn.getresponse().read())


class PodStatus:

    def __init__(self, status_dict):
        self._status = status_dict

    @property
    def is_ready(self):
        if not self._status:
            return False

        return next(
            (
                condition['status'] == "True" for condition
                in self._status['status']['conditions']
                if condition['type'] == 'ContainersReady'
            ),
            False
        )

    @property
    def is_running(self):
        if not self._status:
            return False

        return self._status['status']['phase'] == 'Running'

    @property
    def is_unknown(self):
        return not self._status
