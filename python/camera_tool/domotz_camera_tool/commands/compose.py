from __future__ import annotations

import argparse
import logging
from os import mkdir
from os.path import join

from PIL import Image
from jinja2 import Environment, FileSystemLoader

from domotz_camera_tool.client import ApiClient

__author__ = 'Iacopo Papalini <iacopo@domotz.com>'

from domotz_camera_tool.assets import ASSETS_DIR

from domotz_camera_tool.helpers.async_pool import gather_max_parallelism

from domotz_camera_tool.helpers.cameras import CamerasHelper, STATUS_AUTHENTICATED, STATUS_LOCKED

_logger = logging.getLogger(__name__)

DESCRIPTION = "Compose the snapshots of all the cameras of a site in a HTML Page"
COMMAND_NAME = 'compose'


def positive(value):
    try:
        value = int(value)
        if value < 1:
            raise ValueError(value)
    except ValueError:
        raise argparse.ArgumentTypeError("%s is not a positive int value" % value)
    return value


def add_command(subparsers):
    parser = subparsers.add_parser(COMMAND_NAME, help=DESCRIPTION)
    parser.add_argument('dir_name', default=None, help="Directory where to create the HTML Page")
    parser.add_argument('agent_id', default=None, help="The Id of the agent")
    parser.add_argument('-w', '--thumb_width', default=250, type=positive, help="The width of the thumbnails")
    parser.add_argument('-r', '--thumbs_per_row', default=4, type=positive, help="The number of thumbnails per row")

    parser.set_defaults(function=_compose)


async def _compose(args, client: ApiClient):
    await Compositor(args, client).compose()


class Compositor:
    def __init__(self, args, client: ApiClient):
        self.client = client
        self.agent_id = args.agent_id
        self.dir_name = args.dir_name
        self.thumb_width = args.thumb_width
        self.thumbs_per_row = args.thumbs_per_row
        self.jinja_data = {
            'thumb_width': self.thumb_width,
            'thumbs_per_row': self.thumbs_per_row,
            'images': {},
            'thumbnails': {},
        }

    async def _nop(self):
        return None

    async def compose(self):
        agent = await self.client.fetch_agent_details(self.agent_id)
        if agent['status']['value'] != 'ONLINE':
            raise RuntimeError("Agent is OFFLINE")
        helper = CamerasHelper(self.client)
        cameras = await helper.fetch_cameras(self.agent_id)
        concurrent = []
        for camera in cameras:
            if camera.status == STATUS_AUTHENTICATED:
                concurrent.append(helper.get_snapshot(self.agent_id, camera.id))
            else:
                concurrent.append(self._nop())
        images = await gather_max_parallelism(concurrent)

        mkdir(self.dir_name)
        await self._save_images_files(cameras, images)
        await self._save_thumbnails_files(cameras, images)

        self.jinja_data['cameras'] = cameras
        self.jinja_data['agent'] = agent
        self.jinja_data['title'] = "Agent '{}' Cameras".format(agent['display_name'])

        environment = Environment(loader=FileSystemLoader(ASSETS_DIR), autoescape=True)
        template = environment.get_template('compose.html.jinja2')
        with open(join(self.dir_name, 'index.html'), 'w') as _file:
            _file.write(template.render(**self.jinja_data))

    async def _save_thumbnails_files(self, cameras, images):
        offline_image = Image.open(join(ASSETS_DIR, 'offline.jpg'))
        offline_image.thumbnail(self._thumbnail_size(offline_image), Image.ANTIALIAS)
        locked_image = Image.open(join(ASSETS_DIR, 'locked.jpg'))
        locked_image.thumbnail(self._thumbnail_size(locked_image), Image.ANTIALIAS)
        thumbs_dir = join(self.dir_name, 'thumbnails')
        mkdir(thumbs_dir)
        for camera, image in zip(cameras, images):
            if image is not None:
                image.thumbnail(self._thumbnail_size(image, ), Image.ANTIALIAS)
            elif camera.status == STATUS_LOCKED:
                image = locked_image
            else:  # camera.status == STATUS_DOWN
                image = offline_image
            file_name = join(thumbs_dir, "{}.{}".format(camera.id, image.format.lower()))
            image.save(file_name)
            self.jinja_data['thumbnails'][camera.id] = file_name
            _logger.debug("Saved file %s (%s)", file_name, image.size)

    async def _save_images_files(self, cameras, images):
        images_dir = join(self.dir_name, 'images')
        mkdir(images_dir)
        for camera, image in zip(cameras, images):
            if image is None:
                continue
            file_name = join(images_dir, "{}.{}".format(camera.id, image.format.lower()))
            image.save(file_name)
            self.jinja_data['images'][camera.id] = file_name
            _logger.debug("Saved file %s (%s)", file_name, image.size)

    def _thumbnail_size(self, image):
        size = image.size
        return self.thumb_width, int(self.thumb_width / size[0] * size[1] + 0.5)
