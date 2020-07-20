__author__ = 'Iacopo Papalini <iacopo@domotz.com>'

import json
import logging
from collections import namedtuple
from io import BytesIO
from os.path import join

from PIL import Image

from domotz_camera_tool.client import ApiClient
from domotz_camera_tool.assets import ASSETS_DIR
from domotz_camera_tool.helpers.async_pool import gather_max_parallelism

Camera = namedtuple('Camera', 'id,name,main_ip,make,model,status,last_status_change,zone,room')
_logger = logging.getLogger(__name__)
STATUS_DOWN = 'DOWN'
STATUS_LOCKED = 'LOCKED'
STATUS_AUTHENTICATED = 'AUTHENTICATED'


class CamerasHelper:
    def __init__(self, client: ApiClient):
        self.client = client

    async def fetch_cameras(self, agent_id) -> [Camera]:
        cameras_types = await self.fetch_type_ids_with_capability('snapshot')
        devices_raw = await self.client.fetch_devices(agent_id)
        fetchers = []
        for data in devices_raw:
            _logger.debug(json.dumps(data, indent=2))
            if data.get('type', {}).get('detected_id', 0) not in cameras_types:
                continue
            fetchers.append(self.client.fetch_device_details(agent_id, data['id']))

        cameras_raw = await gather_max_parallelism(fetchers)

        cameras = []
        for data in cameras_raw:
            cameras.append(Camera(
                data['id'],
                data['display_name'],
                data['ip_addresses'][0],
                data.get('vendor'),
                data.get('model'),
                self._translate_status(data),
                data['last_status_change'],
                data.get('details', {}).get('zone', None),
                data.get('details', {}).get('room', None)
            ))
            _logger.debug("Details for camera %s:\n%s", data['id'], json.dumps(data, indent=2))
        return cameras

    @classmethod
    def _translate_status(cls, data):
        """For our goal, the status can either be AUTHENTICATED (ok), LOCKED (missing credentials) or DOWN"""
        if data['status'] == 'ONLINE':
            auth_status = data.get('authentication_status')
            if auth_status in ('NO_AUTHENTICATION', STATUS_AUTHENTICATED):
                return STATUS_AUTHENTICATED
            else:
                return STATUS_LOCKED
        else:
            return STATUS_DOWN

    async def get_snapshot(self, agent_id, device_id) -> Image:
        try:
            data = await self.client.get_bytes('agent', agent_id, 'device', device_id, 'multimedia', 'camera',
                                               'snapshot')
            image = Image.open(BytesIO(data))
            return image
        except RuntimeError as e:
            _logger.warning(e)
            _logger.info("Returning broken image for device %s", device_id)
            return Image.open(join(ASSETS_DIR, 'offline.jpg'))

    async def fetch_type_ids_with_capability(self, capability) -> [int]:
        ret = []
        all_types = await self.client.get_json('type', 'device', 'detected')
        for type_ in all_types:
            if capability in type_['capabilities']:
                ret.append(type_['id'])
        _logger.info("Types with capability %s: %s", capability, ret)
        return ret
