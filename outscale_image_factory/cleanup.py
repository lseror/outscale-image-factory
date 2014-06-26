#!/usr/bin/python
"""
Cleanup EC2 objects left behind by the factory.

Written in Python 2 to use Boto.
"""

import json
import sys
import optparse
import logging

import boto.ec2
import boto.exception

from outscale_image_factory.create_ami import destroy_volume


USAGE = '''
%s -v -v -t '{"key1":"value1","key2":"value2"}'
''' % sys.argv[0]


# Defaults
REGION = 'eu-west-1'


def search_and_destroy(conn, key, value, dryrun=False):
    """
    Search & destroy all EC2 volumes and instances tagged with key and value.
    """
    filters = {'tag:' + key: value}
    volume_list = []
    instance_list = []

    logging.info('Searching for volumes and instances matching {}'
                 .format(repr(filters)))
    try:
        volume_list = conn.get_all_volumes(filters=filters)
        reservations = conn.get_all_instances(filters=filters)
        instance_list = [i for r in reservations for i in r.instances]
    except (
            boto.exception.BotoClientError,
            boto.exception.BotoServerError) as search_error:
        logging.error('Error while searching: filters={} error={}'
                      .format(repr(filters), repr(search_error)))

    logging.info('Terminating instances: {}'.format(repr(instance_list)))
    for instance in instance_list:
        if dryrun:
            continue
        try:
            instance.terminate()
        except Exception as terminate_error:
            logging.error('Error while destroying {}: {}'
                          .format(instance.id, repr(terminate_error)))

    logging.info('Destroying volumes: {}'.format(repr(volume_list)))
    for volume in volume_list:
        if dryrun:
            continue
        destroy_volume(conn, volume.id)


def main():
    """
    CLI
    """
    parser = optparse.OptionParser(usage=USAGE)
    parser.add_option('-r', '--region', default=REGION)
    parser.add_option('-t', '--tags', metavar='JSON', default=None)
    parser.add_option('-n', '--dryrun', action='store_true', default=False)
    parser.add_option(
        '-v',
        '--verbose',
        action='count',
        default=0,
        help='use twice for debug output')

    opt, _ = parser.parse_args()
    if not opt.tags:
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

    conn = boto.ec2.connect_to_region(REGION)
    tags = json.loads(opt.tags)
    logging.debug(tags)
    for k in tags:
        v = tags[k]
        search_and_destroy(conn, k, v, opt.dryrun)


if __name__ == '__main__':
    main()
