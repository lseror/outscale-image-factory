#!/usr/bin/env python2
"""
Create a sources.list file for Debian or Ubuntu.
"""
from __future__ import division, absolute_import, print_function, unicode_literals

import sys

DEBIAN_RELEASES = set([
    'etch',
    'jessie',
    'lenny',
    'oldstable',
    'potato',
    'sarge',
    'sid',
    'squeeze',
    'stable',
    'testing',
    'unstable',
    'wheezy',
    'woody',
])

UBUNTU_RELEASES = set([
    'breezy',
    'dapper',
    'edgy',
    'feisty',
    'gutsy',
    'hardy',
    'hoary',
    'intrepid',
    'jaunty',
    'karmic',
    'lucid',
    'maverick',
    'natty',
    'oneiric',
    'precise',
    'quantal',
    'raring',
    'saucy',
    'trusty',
    'utopic',
    'warty',
])

NONE, DEBIAN, UBUNTU = range(3)


def create_sources_list(filename, mirror, codename):
    """
    Create sources.list
    """
    distro = None
    repos = None
    security_mirror = None
    if codename in DEBIAN_RELEASES:
        distro = DEBIAN
        repos = 'main contrib non-free'
        if codename not in ['sid', 'unstable']:
            security_mirror = 'http://security.debian.org'
    if codename in UBUNTU_RELEASES:
        distro = UBUNTU
        repos = 'main restricted universe multiverse'
        security_mirror = mirror
    if not distro:
        raise Exception('Unknown distribution codename: ' + codename)
    with open(filename, 'w') as f:
        f.write(' '.join(('deb', mirror, codename, repos)))
        f.write('\n')
        if security_mirror:
            if distro == DEBIAN:
                f.write(' '.join(('deb', security_mirror, codename + '/updates', repos)))
            if distro == UBUNTU:
                f.write(' '.join(('deb', security_mirror, codename + '-security', repos)))
            f.write('\n')

def main():
    """
    Main function.
    """
    if len(sys.argv) != 4:
        sys.stderr.write('Usage: {} filename mirror_url distro_codename\n'.format(sys.argv[0]))
        sys.exit(1)
    create_sources_list(sys.argv[1], sys.argv[2], sys.argv[3])

if __name__ == '__main__':
    main()
