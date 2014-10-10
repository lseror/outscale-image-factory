"""
Helper functions used by the Outscale factory tools.
"""
# Python 2/3 compatibility
from __future__ import division, absolute_import, print_function, unicode_literals

import logging
import subprocess
import os


def _log_output(fp, prefix, lines):
    line = fp.readline()
    if not line:
        return False
    line = line.decode('utf-8', 'ignore')
    logging.info(prefix + line.rstrip())
    lines.append(line)
    return True


def check_cmd(cmd, data='', dryrun=False):
    """Run command, log everything, return a (bool,dict) tuple with command
    success and debug data."""
    logging.info('Running {}'.format(repr(cmd)))
    if dryrun:
        stdout = b''
        ret = 0
    else:
        proc = subprocess.Popen(cmd.split(' '),
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        if data:
            proc.stdin.write(data.encode('ascii'))
        proc.stdin.close()

        # Run the command
        lines = []
        logging.info('pid: {}'.format(proc.pid))
        prefix = '({}) '.format(proc.pid)
        while proc.returncode is None:
            proc.poll()
            _log_output(proc.stdout, prefix, lines)

        # Read the rest of proc.stdout
        while _log_output(proc.stdout, prefix, lines):
            pass
        proc.stdout.close()
        stdout = ''.join(lines)

        ret = proc.returncode

    data = dict(
        cmd=cmd,
        pwd=os.getcwd(),
        stdin=data,
        stdout=stdout,
        ret=ret,
    )
    ok = (ret == 0)
    if not ok:
        logging.error('Command {} failed with error code {}'
                      .format(repr(cmd), ret))
    return ok, data


def cd(path):
    """Chdir wrapper: log, catch exceptions.
    """
    logging.info('Changing dir to {}'.format(path))
    try:
        os.chdir(path)
        ok = True
        err = None
    except Exception as exc:
        ok = False
        err = exc
    if not ok:
        logging.error(repr(err))
    return ok, err


if __name__ == "__main__":
    # Basic testing
    logging.basicConfig(level=logging.INFO)
    for args in [
            ('find /etc/acpi',),
            ('tr a-z A-Z', 'Some content'),
            ('ls /does-not-exist',),
            ]:
        print('# Running {}'.format(args))
        ok, data = check_cmd(*args)
        print()
        print('ok={}\ndata={}'.format(ok, data))
        print()
