#!/usr/bin/env python2
"""
Create a VM image from a build volume.
"""
from __future__ import division, absolute_import, print_function, unicode_literals

import time
import logging
import json
import sys
import urllib2

import boto.ec2
import boto.exception

from outscale_image_factory import config


# Status strings
AVAILABLE = 'available'
STOPPED = 'stopped'
RUNNING = 'running'

# Snaphost status strings
SNAPSHOT_PENDING = 'pending'
SNAPSHOT_ERROR = 'error'
SNAPSHOT_COMPLETED = 'completed'


class _OIFError(Exception):

    """
    Base type for exceptions in this module.

    Exceptions are used in internal interfaces to
    integrate with boto error handling.
    """


class _TimeoutError(_OIFError):
    pass


class _FindError(_OIFError):
    pass


class _DeviceAllocationError(_OIFError):
    pass


def _wait_for(obj, target_state, poll_sec=1.5, wait_sec=600):
    """
    Wait for object to change state.

    Raise _TimeoutError on failure.
    """
    def _state(x):
        return x.state if hasattr(x, 'state') else x.status

    def _logstate(x):
        logging.debug('{} state={}'.format(x.id, repr(_state(x))))

    clock = 0
    logging.info('Waiting for ' + obj.id)
    _logstate(obj)
    while _state(obj) != target_state and clock < wait_sec:
        _logstate(obj)
        time.sleep(poll_sec)
        clock += poll_sec
        obj.update()
    if _state(obj) != target_state:
        raise _TimeoutError('timeout while waiting for ' + repr(obj.id))


def _find_volume(conn, volume_id=None, instance_id=None):
    """
    Return list of volume objects.

    Raise _FindError on failure.
    """
    filters = {}
    if volume_id:
        filters['volume-id'] = volume_id
    if instance_id:
        filters['attachment.instance-id'] = instance_id
    volume_list = conn.get_all_volumes(filters=filters)
    if not volume_list:
        raise _FindError(
            'No such volume volume_id={} instance_id={}'.format(volume_id, instance_id))
    return volume_list


def _allocate_device(conn, instance_id, device_name_blacklist=set(),
                     prefix='/dev/sd', start='b', stop='z'):
    """
    Return first free device name on instance.

    Start search at /dev/sdb and end at /dev/sdz by default.

    If all device names are allocated, raise _DeviceAllocationError.
    """
    try:
        volumes = _find_volume(conn, instance_id=instance_id)
    except _OIFError as volume_error:
        logging.warn(repr(volume_error))
        volumes = []

    used = set(vol.attach_data.device for vol in volumes)
    used.update(device_name_blacklist)
    suffix = ord(start)
    dev = prefix + chr(suffix)
    while dev in used and suffix < ord(stop):
        suffix += 1
        dev = prefix + chr(suffix)
    if dev in used:
        raise _DeviceAllocationError('No free device names')
    return dev


def _tag(conn, object_id, tags_dict):
    """
    Helper function for tagging objects.
    """
    if tags_dict:
        logging.info('Tagging {} : {}'.format(object_id, repr(tags_dict)))
        conn.create_tags(object_id, tags_dict)


def _get_instance_id():
    fp = urllib2.urlopen('http://169.254.169.254/latest/meta-data/instance-id')
    return fp.read()


def create_volume(conn, instance_id, volume_size_gib, volume_location,
                  volume_tags=None):
    """
    Create a new volume and attach it to a buildslave.

    Return on error or when the volume is attached.

    Return (volume_id,device,error) tuple.
    """

    volume_id = None
    device = None
    error = None

    try:
        logging.info('Creating volume')
        volume = conn.create_volume(volume_size_gib, volume_location)
        volume_id = volume.id
        _wait_for(volume, AVAILABLE)
        _tag(conn, volume_id, volume_tags)

        logging.info('Allocating device name')
        device = _allocate_device(conn, instance_id)

        logging.info('Attaching volume to ' + repr((instance_id, device)))
        volume.attach(instance_id, device)
        _wait_for(volume, AVAILABLE)

    except (_OIFError,
            boto.exception.BotoClientError,
            boto.exception.BotoServerError) as error:
        pass

    if error is not None:
        logging.error(
            'Could not attach new volume to {}: {}'.format(instance_id, repr(error)))

    if error is not None and volume_id is not None:
        try:
            destroy_volume(conn, volume_id)
            volume_id = None
        except Exception as cleanup_error:
            logging.error(
                'Could not cleanup {} after failure: {}'.format(volume_id,
                                                                repr(cleanup_error)))

    return volume_id, device, error


def cmd_create_volume(args):
    tags = json.loads(args.tags)
    conn = boto.ec2.connect_to_region(args.region)
    if args.instance_id:
        instance_id = args.instance_id
    else:
        instance_id = _get_instance_id()
        logging.info('Instance id is {}'.format(instance_id))
    volume_id, device, error = create_volume(conn,
                                             instance_id,
                                             args.volume_size,
                                             args.volume_location,
                                             tags)

    if error is None:
        sys.stdout.write('VOLUME_ID={}\nDEVICE={}\n' .format(volume_id, device))
    return error is None


def parser_create_volume(parser):
    dct = config.load()
    parser.description = 'Create and attach a new volume'
    parser.add_argument('--instance-id')
    parser.add_argument('--volume-location', default=dct['volume-location'])
    parser.add_argument('--region', default=dct['region'])
    parser.add_argument('--tags', metavar='JSON', default='{}')
    parser.add_argument('volume_size', metavar='VOLUME_SIZE',
                        type=int, help='Volume size in GiB')


def detach_volume(conn, volume_id):
    """
    Detach volume from buildslave.

    Return on error or when the volume becomes available.

    Return (ok,error) tuple.
    """
    error_prefix = 'Cannot detach build volume {}: '.format(volume_id)
    ok = False
    error = None

    try:
        volume = _find_volume(conn, volume_id=volume_id)[0]
        if volume.status != AVAILABLE:
            logging.info('Detaching build volume ' + volume_id)
            volume.detach()
            _wait_for(volume, AVAILABLE)
            ok = True
        else:
            logging.error(
                '{}: volume appears to be already detached'.format(error_prefix))
            ok = False

    except (_OIFError,
            boto.exception.BotoClientError,
            boto.exception.BotoServerError) as error:
        ok = False

    if error:
        logging.error(
            '{}: detach operation failed: {}'.format(error_prefix, repr(error)))

    return ok, error


def create_image(conn, image_name, volume_id, image_arch=None,
                 image_description=None, tags=None, root_dev=None):
    """
    Create a new machine image from a build volume.

    Return (image_id, error) tuple.


    Unsupported parameters by Outscale's register_image():
    image_location, kernel_id, ramdisk_id.
    """

    dct = config.load()
    if image_arch is None:
        image_arch = dct['image-arch']
    if root_dev is None:
        root_dev = dct['root-dev']

    image_id = None
    error = None
    snapshot_id = None

    try:
        volume = _find_volume(conn, volume_id=volume_id)[0]

        logging.info('Creating snapshot from volume ' + volume_id)
        snapshot = volume.create_snapshot('Backing image {} created from volume {}'
                                          .format(repr(image_name), volume_id))
        _wait_for(snapshot, SNAPSHOT_COMPLETED)
        snapshot_id = snapshot.id
        _tag(conn, snapshot_id, tags)

        logging.info(
            'Creating block device map : {} = {}'.format(root_dev, volume_id))

        bdm = boto.ec2.blockdevicemapping.BlockDeviceMapping(conn)
        ebs = boto.ec2.blockdevicemapping.EBSBlockDeviceType()
        # ebs.delete_on_termination = True
        ebs.snapshot_id = snapshot_id
        bdm[root_dev] = ebs

        logging.info('Creating image from snapshot ' + snapshot_id)

        image_id = conn.register_image(
            name=image_name,
            description=image_description,
            architecture=image_arch,
            root_device_name=root_dev,
            block_device_map=bdm,
            snapshot_id=snapshot_id,
            delete_root_volume_on_termination=True)

        _tag(conn, image_id, tags)

    except (_OIFError,
            boto.exception.BotoClientError,
            boto.exception.BotoServerError) as error:
        pass

    if error:
        logging.error('Could not create image {} from volume {} and snapshot {}: {}'.format(
            image_name, repr(volume_id), repr(snapshot_id), repr(error)))

    return image_id, error


def cmd_create_image(args):
    tags = json.loads(args.tags)
    conn = boto.ec2.connect_to_region(args.region)
    ok, _ = detach_volume(conn, args.volume_id)
    if not ok:
        return False
    image_id, error = create_image(conn, args.image_name, args.volume_id,
                                   args.image_arch,
                                   args.image_description,
                                   tags)
    return error is None


def parser_create_image(parser):
    dct = config.load()

    parser.description = 'Create an AMI from an existing volume'
    parser.add_argument('image_name', metavar='IMAGE_NAME', default=None)
    parser.add_argument('--volume-id', default=None)
    parser.add_argument('--image-description', default=None)
    parser.add_argument('--image-arch', default=dct['image-arch'])
    parser.add_argument('--region', default=dct['region'])
    parser.add_argument('--tags', metavar='JSON', default='{}')


def destroy_volume(conn, volume_id):
    """
    Destroy build volume.

    Return (ok, error) tuple.
    """

    ok = False
    error = None

    try:
        volume = _find_volume(conn, volume_id=volume_id)[0]
        if volume.status != AVAILABLE:
            logging.info(
                'Detaching volume {} before destroying'.format(volume_id))
            volume.detach()
            _wait_for(volume, AVAILABLE)

        logging.info('Destroying volume ' + repr(volume_id))
        volume.delete()
        ok = True

    except (_OIFError,
            boto.exception.BotoClientError,
            boto.exception.BotoServerError) as error:
        ok = False

    if error:
        logging.error('Could not destroy volume: {}'.format(error))

    return ok, error


def cmd_destroy_volume(args):
    conn = boto.ec2.connect_to_region(args.region)
    ok, _ = destroy_volume(conn, args.volume_id)
    return ok


def parser_destroy_volume(parser):
    dct = config.load()

    parser.description = 'Destroy an existing volume'
    parser.add_argument('volume_id', metavar='VOLUME_ID')
    parser.add_argument('--region', default=dct['region'])
