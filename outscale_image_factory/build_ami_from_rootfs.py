#!/usr/bin/env python3
"""
Build VM disk image from Turnkey rootfs.
"""
import os
import sys
import logging
import optparse
import tempfile
import time

from outscale_image_factory.helper import check_cmd


USAGE = '''
apt-get install python3 rsync
build_ami_from_rootfs.py -v --device=/dev/sdz --root=/turnkey/fab/product.rootfs
'''

# Partitions shoud be aligned on a multiple of 2048 sectors
# This is a 10G partition
PARTITION_TABLE = [
    (2048, 20969391, 83),
]


def _wait_for_file(name, timeout_sec=60, poll_sec=1.5):
    """
    Wait for file to appear.
    """
    clock = 0
    while not os.path.exists(name) and clock < timeout_sec:
        time.sleep(poll_sec)
        clock += poll_sec
    return os.path.exists(name)


def _sfdisk_part_table(dev, spec):
    """
    Take a list of of (start,size,id) tuples, return partition table in
    sfdisk format.
    """
    lines = ['unit: sectors', '']
    for i, (start, size, fid) in enumerate(spec):
        lines.append(
            '{}{}: start= {}, size= {}, Id={}'.format(
                dev,
                i,
                start,
                size,
                fid))
    return '\n'.join(lines) + '\n'


def build_ami_from_rootfs(dev, rootfs, dryrun=False, partno=1):
    """
    Copy rootfs to block device, install grub.

    dev: block device path
    rootfs: directory containing root filesystem.

    Return (ok, error) tuple.
    """
    logging.debug('Waiting for ' + dev)
    if not _wait_for_file(dev):
        return False, 'Timeout while waiting for ' + dev

    # Use the real device path, some commands choke on symlinks
    dev = os.path.realpath(dev)
    rootfs = rootfs.rstrip('/')
    part = dev + str(partno)
    parttable = _sfdisk_part_table(dev, PARTITION_TABLE)

    mnt = tempfile.mkdtemp('-outscale-mnt')

    script = [
        ['Partitionning {}'.format(dev),
         'sfdisk --force {}'.format(dev),
         parttable],
        ['Creating FS on {}'.format(part),
         'mkfs.ext4 {}'.format(part)],
        ['Tuning FS',
         'tune2fs -c -0 -i 0 {}'.format(part)],
        ['Mounting FS {} on {}'.format(part, mnt),
         'mount -t ext4 {} {}'.format(part, mnt)],
        ['Creating fstab',
         'python3 -m outscale_image_factory.create_fstab {}/etc/fstab {}'
         .format(rootfs, part)],
        ['Copying rootfs {} to {}'.format(rootfs, mnt),
         'rsync -a {}/ {}'.format(rootfs, mnt)],
        ['Installing grub',
         'mount --bind /dev {}/dev'.format(mnt)],
        ['',
         'mount --bind /proc {}/proc'.format(mnt)],
        ['',
         'mount --bind /sys {}/sys'.format(mnt)],
        ['',
         'chroot {} grub-install {}'.format(mnt, dev)],
        ['',
         'chroot {} update-grub'.format(mnt)],
        ['Syncing',
         'sync'],
    ]

    ok = True
    try:
        while script and ok:
            lst = script.pop(0)
            msg, cmd = lst[:2]
            data = ''
            if len(lst) == 3:
                data = lst[2]
            if msg:
                logging.info(msg)
            ok, err = check_cmd(cmd, data, dryrun)
    finally:
        logging.info('Unmounting')
        check_cmd('umount {}/dev'.format(mnt), dryrun=dryrun)
        check_cmd('umount {}/proc'.format(mnt), dryrun=dryrun)
        check_cmd('umount {}/sys'.format(mnt), dryrun=dryrun)
        check_cmd('umount {}'.format(part), dryrun=dryrun)
        logging.info('Removing {}'.format(mnt))
        os.rmdir(mnt)
    return ok, err


def main():
    """CLI."""
    parser = optparse.OptionParser(usage=USAGE)
    parser.add_option('-r', '--rootfs')
    parser.add_option('-d', '--device')
    parser.add_option(
        '-v',
        '--verbose',
        action='count',
        default=0,
        help='use twice for debug output')
    parser.add_option(
        '-n',
        '--dryrun',
        default=False,
        action='store_true',
        help='dont actually do anything')
    opt, _ = parser.parse_args()
    if not opt.rootfs or not opt.device:
        parser.print_help()
        sys.exit(1)

    loglevel = logging.WARNING
    if opt.verbose > 0:
        loglevel = logging.INFO
    if opt.verbose > 1:
        loglevel = logging.DEBUG
    logging.basicConfig(format='%(levelname)s:%(message)s', level=loglevel)

    ok, error = build_ami_from_rootfs(
        opt.device,
        opt.rootfs,
        opt.dryrun)
    if not ok:
        logging.error(repr(error))
        sys.exit(1)
    sys.exit(0)

if __name__ == '__main__':
    main()
