#!/usr/bin/env python2
from __future__ import division, absolute_import, print_function, unicode_literals

import logging
import sys

from outscale_image_factory.helper import check_cmd


def create_fstab(fstab_filename, root_device):
    """
    Create fstab with root device.
    """
    ok, data = check_cmd('/sbin/blkid -o export {}'.format(root_device))
    if ok:
        stdout = data['stdout']
        uuid = None
        fstype = None
        for line in stdout.split('\n'):
            if line.startswith('UUID'):
                uuid = line
            elif line.startswith('TYPE'):
                fstype = line.split('=')[1]
        with open(fstab_filename, 'w') as fstab:
            try:
                fstab.write('# <file system> <mount point> <type> <options> <dump> <pass>\n')
                fstab.write('{} / {} errors=remount-ro 0 1\n'.format(uuid, fstype))
            except Exception as error:
                ok = False
                logging.error(error)
    return ok


def main():
    """
    Main function.
    """
    if len(sys.argv) != 3:
        sys.stderr.write('Usage: {} fstab_filename root_device\n'.format(sys.argv[0]))
        sys.exit(1)
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
    if not create_fstab(sys.argv[1], sys.argv[2]):
        sys.exit(1)

if __name__ == '__main__':
    main()
