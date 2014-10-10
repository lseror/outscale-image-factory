#!/usr/bin/python
"""
Create a VM image from a build volume.

Written in Python 2 to integrate with Buildbot and Boto.
"""
import optparse
import logging
import sys
import json

import boto.ec2
import boto.exception

from outscale_image_factory.create_ami import attach_new_volume, \
    detach_volume, create_image, destroy_volume

USAGE = '''
{0} -v --attach INSTANCE_ID
{0} -v --create IMAGE_NAME --volume-id VOLUME_ID
{0} -v --destroy VOLUME_ID
'''.format(sys.argv[0])

# Defaults
REGION = 'eu-west-1'
BUILD_VOLUME_SIZE_GIB = 10
BUILD_VOLUME_LOCATION = 'eu-west-1a'
IMAGE_ARCH = 'x86_64'


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
