#!/usr/bin/env python3
"""
Build VM disk image from a Turnkey recipe.
"""
import os
import logging
import shutil
import tempfile

from outscale_image_factory.helper import check_cmd, cd
from outscale_image_factory.install import install_rootfs

# Defaults
TURNKEY_APPS_GIT = 'https://github.com/turnkeylinux-apps'
PATCH_DIR = '/usr/local/share/tklpatch'
FAB_PATH = '/turnkey/fab'
FAB_APT_PROXY = 'http://127.0.0.1:8124'
FAB_HTTP_PROXY = 'http://127.0.0.1:8124'
PATCH_LIST = ['headless', 'outscale']
UMASK = 0o022


def setup_environment(fab_dir):
    logging.info('Setting up environment')
    os.umask(UMASK)
    os.environ.setdefault('FAB_PATH', fab_dir)
    os.environ.setdefault('FAB_APT_PROXY', FAB_APT_PROXY)
    os.environ.setdefault('FAB_HTTP_PROXY', FAB_HTTP_PROXY)


def _clone_or_update(repo, products_dir, app):
    app_dir = '{}/{}'.format(products_dir, app)
    if os.path.exists(app_dir):
        logging.info('Updating {}'.format(app))
        ok, err = cd(app_dir)
        if ok:
            ok, err = check_cmd('git pull')
    else:
        logging.info('Cloning {}'.format(app))
        cd(products_dir)
        ok, err = check_cmd('git clone {}'.format(repo))
    return ok, err


def tkl_install_iso(dev, product_iso, patch_dir, patch_list):
    product_iso = os.path.abspath(product_iso)
    work_dir = tempfile.mkdtemp(suffix='-outscale-work')
    cd(work_dir)
    try:
        logging.info('Extracting iso in {}'.format(work_dir))
        ok, err = check_cmd('tklpatch-extract-iso {}'.format(product_iso))
        if ok:
            logging.info('Applying patches')
            rootfs_dir = '{}/product.rootfs'.format(work_dir)
            for patch in patch_list:
                ok, err = check_cmd(
                    'tklpatch-apply {} {}/{}'.format(rootfs_dir, patch_dir, patch))
                if not ok:
                    break
        if ok:
            ok, err = install_rootfs(dev, rootfs_dir)
    finally:
        logging.info('Deleting {}'.format(work_dir))
        shutil.rmtree(work_dir)
    return ok, err


def cmd_tkl_install_iso(args):
    if os.path.exists(args.appliance_or_iso):
        iso = args.appliance_or_iso
    else:
        iso = os.path.join(args.fab_dir, 'products', args.appliance_or_iso,
                           'build/product.iso')
    ok, _ = tkl_install_iso(args.device,
                            iso,
                            args.patch_dir,
                            PATCH_LIST + args.add_tklpatch)
    return ok


def parser_tkl_install_iso(parser):
    parser.description = 'Install a system from an ISO file to a device'
    parser.add_argument('appliance_or_iso', metavar='APPLIANCE_OR_ISO')
    parser.add_argument('-d', '--device')
    parser.add_argument('-p', '--patch-dir', default=PATCH_DIR)
    parser.add_argument('-f', '--fab-dir', default=FAB_PATH)
    parser.add_argument('-t', '--add-tklpatch', action='append', default=[])


def tkl_build(app, git, fab_dir):
    """Build the TKL appliance.

    app: turnkey app to build
    git: git repository containing turnkey apps
    fab_dir: turnkey build directory
    """
    core_repo = '{}/core.git'.format(TURNKEY_APPS_GIT)
    repo = '{}/{}'.format(git, app)
    products_dir = '{}/products'.format(fab_dir)
    app_dir = '{}/{}'.format(products_dir, app)

    ok, err = _clone_or_update(core_repo, products_dir, 'core')
    if ok:
        ok, err = _clone_or_update(repo, products_dir, app)
    if ok:
        logging.info('Building product {}'.format(app))
        ok, err = cd(app_dir)
    if ok:
        ok, err = check_cmd('make')
    return ok, err


def cmd_tkl_build(args):
    setup_environment(args.fab_dir)
    ok, _ = tkl_build(args.app,
                      args.turnkey_apps_git,
                      args.fab_dir)
    return ok


def parser_tkl_build(parser):
    parser.description = 'Build a TKL appliance'
    parser.add_argument('app')
    parser.add_argument('-f', '--fab-dir', default=FAB_PATH)
    parser.add_argument('-g', '--turnkey-apps-git', default=TURNKEY_APPS_GIT)


def tkl_clean(app, fab_dir):
    """Clean everything."""
    app_dir = os.path.join(fab_dir, 'products', app)

    logging.info('Cleaning up')
    cd(app_dir)
    check_cmd('deck -D build/root.tmp')
    check_cmd('make clean')


def cmd_tkl_clean(args):
    setup_environment(args.fab_dir)
    tkl_clean(args.app, args.fab_dir)
    return True


def parser_tkl_clean(parser):
    parser.description = 'Clean TKL build dirs'
    parser.add_argument('app')
    parser.add_argument('-f', '--fab-dir', default=FAB_PATH)
