#!/usr/bin/python
"""
Create a VM image from a build volume.

Written in Python 2 to integrate with Buildbot and Boto.
"""
import time
import optparse
import logging
import sys
import json

import boto.ec2
import boto.exception


USAGE = '''
{0} -v --attach INSTANCE_ID
{0} -v --create IMAGE_NAME --volume-id VOLUME_ID
{0} -v --destroy VOLUME_ID
'''.format(sys.argv[0])

# Status strings
AVAILABLE = 'available'
STOPPED = 'stopped'
RUNNING = 'running'

# Snaphost status strings
SNAPSHOT_PENDING = 'pending'
SNAPSHOT_ERROR = 'error'
SNAPSHOT_COMPLETED = 'completed'

# Defaults
REGION = 'eu-west-1'
BUILD_VOLUME_SIZE_GIB = 10
BUILD_VOLUME_LOCATION = 'eu-west-1a'
ROOT_DEV = '/dev/sda1'
IMAGE_ARCH = 'x86_64'


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


def attach_new_volume(conn, instance_id, volume_size_gib, volume_location,
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
        logging.info('Creating build volume')
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


def create_image(conn, image_name, volume_id,
                 image_arch=IMAGE_ARCH,
                 image_description=None, tags=None,
                 root_dev=ROOT_DEV):
    """
    Create a new machine image from a build volume.

    Return (image_id, error) tuple.


    Unsupported parameters by Outscale's register_image():
    image_location, kernel_id, ramdisk_id.
    """

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


def main():
    """CLI for Testing."""

    parser = optparse.OptionParser(usage=USAGE)
    # attach
    parser.add_option(
        '--attach-new-volume',
        metavar='INSTANCE_ID',
        default=None)
    parser.add_option(
        '--volume-size', metavar='GiB', default=BUILD_VOLUME_SIZE_GIB)
    parser.add_option('--volume-location', default=BUILD_VOLUME_LOCATION)
    # create
    parser.add_option('--create-image', metavar='IMAGE_NAME', default=None)
    parser.add_option('--volume-id', default=None)
    parser.add_option('--image-description', default=None)
    parser.add_option('--image-arch', default=IMAGE_ARCH)
    parser.add_option('--region', default=REGION)
    # destroy
    parser.add_option('--destroy-volume', metavar='VOLUME_ID', default=None)
    # general
    parser.add_option('--tags', metavar='JSON', default='{}')
    parser.add_option(
        '-v',
        '--verbose',
        action='count',
        default=0,
        help='use twice for debug output')

    opt, _ = parser.parse_args()
    if not (opt.attach_new_volume or opt.create_image or opt.destroy_volume) \
            or (opt.create_image and not opt.volume_id):
        parser.print_help()
        sys.exit(1)

    loglevel = boto_loglevel = logging.WARNING
    if opt.verbose > 0:
        loglevel = boto_loglevel = logging.INFO
    if opt.verbose > 1:
        loglevel = logging.DEBUG
    if opt.verbose > 2:
        boto_loglevel = loglevel
    logging.basicConfig(format='%(levelname)s:%(message)s', level=loglevel)
    logging.getLogger('boto').setLevel(boto_loglevel)

    conn = boto.ec2.connect_to_region(opt.region)

    if opt.attach_new_volume:
        instance_id = opt.attach_new_volume
        volume_id, device, error = attach_new_volume(
            conn,
            instance_id,
            opt.volume_size,
            opt.volume_location,
            json.loads(opt.tags))
        if not error:
            sys.stdout.write('VOLUME_ID={}\nDEVICE={}\n'
                             .format(volume_id, device))

    if opt.create_image:
        image_name = opt.create_image
        detach_volume(conn, opt.volume_id)
        image_id, error = create_image(
            conn,
            image_name,
            opt.volume_id,
            image_description=opt.image_description,
            image_arch=opt.image_arch,
            tags=json.loads(opt.tags))
        if not error:
            sys.stdout.write('IMAGE_ID={}\n'.format(image_id))

    if opt.destroy_volume:
        destroy_volume(conn, opt.destroy_volume)


if __name__ == '__main__':
    main()
