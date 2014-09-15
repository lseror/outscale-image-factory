#!/usr/bin/env python3
"""
Build VM disk image from a Turnkey recipe.
"""
import os
import logging
import optparse
import sys
import shutil

from outscale_image_factory.helper import check_cmd, cd
from outscale_image_factory.build_ami_from_rootfs import build_ami_from_rootfs

USAGE = '''
build_ami.py -v --device=/dev/sdz --turnkey-app=core
build_ami.py -v --clean --turnkey-app=core
'''

# Defaults
TURNKEY_APPS_GIT = 'https://github.com/turnkeylinux-apps'
PATCH_DIR = '/usr/local/share/tklpatch'
FAB_PATH = '/turnkey/fab'
FAB_APT_PROXY = 'http://127.0.0.1:8124'
FAB_HTTP_PROXY = 'http://127.0.0.1:8124'
MNT_DIR = '/mnt'
WORK_DIR = '/tmp'
PATCH_LIST = ['headless', 'outscale']
UMASK = 0o022


def setup_environment(fab_dir):
    logging.info('Setting up environment')
    os.umask(UMASK)
    os.environ.setdefault('FAB_PATH', fab_dir)
    os.environ.setdefault('FAB_APT_PROXY', FAB_APT_PROXY)
    os.environ.setdefault('FAB_HTTP_PROXY', FAB_HTTP_PROXY)


def build_ami(dev, app, git, patch_dir,
              patch_list, fab_dir, work_dir, mnt_dir):
    """Build the image.

    dev: target block device
    app: turnkey app to build
    git: git repository containing turnkey apps
    patch_dir: directory holding the patches applied by tklpatch
    patch_list: list of patches applied by tklpatch
    fab_dir: turnkey build directory
    work_dir: directory used to extract the rootfs and apply patches
    mnt_dir: directory used to mount the target filesystem
    """
    repo = '{}/{}'.format(git, app)
    products_dir = '{}/products'.format(fab_dir)
    app_dir = '{}/{}'.format(products_dir, app)
    core_app_dir = '{}/core'.format(products_dir)
    core_repo = '{}/core.git'.format(TURNKEY_APPS_GIT)
    product_iso = '{}/build/product.iso'.format(app_dir)
    rootfs_dir = '{}/product.rootfs'.format(work_dir)

    try:
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        os.makedirs(work_dir)
        if not os.path.exists(mnt_dir):
            os.makedirs(mnt_dir)
        ok = True
    except Exception as err:
        ok = False

    if ok:
        ok, err = cd(products_dir)
    if ok and not os.path.exists(core_app_dir):
        logging.info('Cloning {}'.format(core_repo))
        ok, err = check_cmd('git clone {}'.format(core_repo))
    if ok and not os.path.exists(app_dir):
        logging.info('Cloning {}'.format(repo))
        ok, err = check_cmd('git clone {}'.format(repo))
    if ok:
        logging.info('Building product {}'.format(app))
        ok, err = cd(app_dir)
    if ok:
        ok, err = check_cmd('make')
    if ok:
        logging.info('Patching product ')
        ok, err = cd(work_dir)
    if ok:
        ok, err = check_cmd('tklpatch-extract-iso {}'.format(product_iso))
    if ok:
        for patch in patch_list:
            ok, err = check_cmd(
                'tklpatch-apply {} {}/{}'.format(rootfs_dir, patch_dir, patch))
            if not ok:
                break
    if ok:
        ok, err = build_ami_from_rootfs(dev, rootfs_dir, mnt_dir)
    return ok, err


def clean(app, fab_dir, work_dir):
    """Clean everything."""
    app_dir = os.path.join(fab_dir, 'products', app)
    rootfs_dir = '{}/product.rootfs'.format(work_dir)
    cdroot_dir = '{}/product.cdroot'.format(work_dir)

    logging.info('Cleaning up')
    check_cmd('rm -rf {} {}'.format(rootfs_dir, cdroot_dir))
    cd(app_dir)
    check_cmd('deck -D build/root.tmp')
    check_cmd('make clean')


def main():
    """CLI."""
    parser = optparse.OptionParser(usage=USAGE)
    parser.add_option('-d', '--device')
    parser.add_option('-a', '--turnkey-app')
    parser.add_option('-g', '--turnkey-apps-git', default=TURNKEY_APPS_GIT)
    parser.add_option('-p', '--patch-dir', default=PATCH_DIR)
    parser.add_option('-f', '--fab-dir', default=FAB_PATH)
    parser.add_option('-m', '--mount-point', default=MNT_DIR)
    parser.add_option('-w', '--work-dir', default=WORK_DIR)
    parser.add_option('-b', '--build-only', action='store_true', default=False)
    parser.add_option('-c', '--clean-only', action='store_true', default=False)
    parser.add_option('-t', '--add-tklpatch', action='append', default=[])
    parser.add_option(
        '-v',
        '--verbose',
        action='count',
        default=0,
        help='use twice for debug output')
    opt, _ = parser.parse_args()
    if not opt.turnkey_app or not (opt.device or opt.clean_only):
        parser.print_help()
        sys.exit(1)

    loglevel = logging.WARNING
    if opt.verbose > 0:
        loglevel = logging.INFO
    if opt.verbose > 1:
        loglevel = logging.DEBUG
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=loglevel)

    setup_environment(opt.fab_dir)

    ok = True
    if not opt.clean_only:
        ok, _ = build_ami(opt.device,
                          opt.turnkey_app,
                          opt.turnkey_apps_git,
                          opt.patch_dir,
                          PATCH_LIST + opt.add_tklpatch,
                          opt.fab_dir,
                          opt.work_dir,
                          opt.mount_point)
    if not opt.build_only:
        clean(opt.turnkey_app, opt.fab_dir, opt.work_dir)

    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
