#!/usr/bin/env python2
"""
Create a VM image from a build volume.
"""
from __future__ import division, absolute_import, print_function, unicode_literals

import logging
import types
import sys

from argparse import ArgumentParser, RawDescriptionHelpFormatter

try:
    import boto
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False

from outscale_image_factory import tkl_commands
from outscale_image_factory import install
if HAS_BOTO:
    from outscale_image_factory import create_ami


def cmd_help(args):
    if args.command:
        main([args.command, '--help'])
    else:
        main(['--help'])
    return True


def parser_help(parser):
    parser.description = 'Describe a command'
    parser.add_argument('command', nargs='?', metavar='COMMAND')


def add_commands(subparsers, module_or_dict):
    lst = []
    if isinstance(module_or_dict, types.ModuleType):
        dct = module_or_dict.__dict__
    else:
        dct = module_or_dict
    for attr in dct:
        if not attr.startswith('cmd_'):
            continue
        cmd_func = dct[attr]
        func_name = attr[4:]
        init_parser_func = dct['parser_' + func_name]

        cmd_name = func_name.replace('_', '-')
        subparser = subparsers.add_parser(cmd_name)
        init_parser_func(subparser)
        subparser.set_defaults(func=cmd_func)
        lst.append((cmd_name, subparser.description))
    return lst


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest='commands',
                                       title='Available commands')

    lst = add_commands(subparsers, globals())
    if HAS_BOTO:
        lst += add_commands(subparsers, create_ami)
    lst += add_commands(subparsers, tkl_commands)
    lst += add_commands(subparsers, install)

    parser.epilog = '\n'.join(['  {:21} {}'.format(x, y) for x, y in lst])
    if not HAS_BOTO:
        parser.epilog += '\n\nNOTE: AMI commands are disabled because the ' + \
                         'Python Boto module is not installed.'
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        help='Turn on debug output')

    if len(argv) < 1:
        argv.append('--help')
    args = parser.parse_args(argv)

    # Init log
    loglevel = boto_loglevel = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=loglevel)
    logging.getLogger('boto').setLevel(boto_loglevel)

    # Run command
    ok = args.func(args)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
