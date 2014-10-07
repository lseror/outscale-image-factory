#!/usr/bin/env python
# encoding: utf-8

# Python 2/3 compatibility
from __future__ import division, absolute_import, print_function, unicode_literals

import argparse
import json
import os
import re
import sys

DESCRIPTION = """\
Goes through the `conf.d` and `overlay` dirs of a Turn Key Linux appliance and
reports all potential references to external packages.

Produces a JSON output, either to stdout or to the file specified with
`--output`.
"""


REGEXES = [re.compile(x) for x in [
    '(ftp|git|https?)://[^ ]+'
]]


def find_references_in_file(appliance_dir, full_path):
    relative_path = os.path.relpath(full_path, appliance_dir)

    with open(full_path) as fp:
        for num, line in enumerate(fp.readlines()):
            for rx in REGEXES:
                for match in rx.finditer(line.strip()):
                    yield (relative_path, num + 1, match.group(0))


def find_references(appliance_dir):
    lst = []
    for name in ('conf.d', 'overlay'):
        root_path = os.path.join(appliance_dir, name)
        if not os.path.exists(root_path):
            continue
        for dir_path, dirnames, filenames in os.walk(root_path):
            for name in filenames:
                file_path = os.path.join(dir_path, name)
                lst.extend(find_references_in_file(appliance_dir, file_path))
    return lst


def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)

    parser.add_argument('appliance_dir')
    parser.add_argument('-o', '--output')

    args = parser.parse_args()

    if args.output:
        fp = open(args.output, 'w')
    else:
        fp = sys.stdout

    urls = find_references(args.appliance_dir)
    json.dump(urls, fp, indent=2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
# vi: ts=4 sw=4 et
