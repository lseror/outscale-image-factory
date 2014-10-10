#!/usr/bin/env python3
"""
Build VM disk image from a Turnkey recipe.
"""
import logging
import optparse
import sys

from outscale_image_factory.build_ami import build_ami, clean, setup_environment

USAGE = '''
build_ami.py -v --device=/dev/sdz --turnkey-app=core
build_ami.py -v --clean --turnkey-app=core
'''

# Defaults
TURNKEY_APPS_GIT = 'https://github.com/turnkeylinux-apps'
PATCH_DIR = '/usr/local/share/tklpatch'
FAB_PATH = '/turnkey/fab'
MNT_DIR = '/mnt'
WORK_DIR = '/tmp'
PATCH_LIST = ['headless', 'outscale']


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
                          opt.fab_dir)
    if not opt.build_only:
        clean(opt.turnkey_app, opt.fab_dir)

    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
