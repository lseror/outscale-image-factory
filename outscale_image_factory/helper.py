"""
Helper functions used by the Outscale factory tools.
"""
import logging
import subprocess
import os


def check_cmd(cmd, data='', dryrun=False):
    """Run command, log everything, return a (bool,dict) tuple with command
    success and debug data."""
    logging.info(repr(cmd))
    if dryrun:
        ret = 0
    else:
        proc = subprocess.Popen(cmd.split(' '), stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if data:
            proc.write(bytes(data, 'ascii'))
        proc.stdin.close()
        while proc.returncode is None:
            line = proc.stdout.readline()
            if line:
                line = line.rstrip().decode(errors='replace')
                logging.info('  ' + line)
            proc.poll()
        ret = proc.returncode
    if ret != 0:
        logging.error('Command finished with error code {}'.format(ret))
    else:
        logging.info('Command finished successfully')
    error = dict(
        cmd=cmd,
        stdin=data,
        ret=ret
    )
    ok = (ret == 0)
    return ok, error


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
