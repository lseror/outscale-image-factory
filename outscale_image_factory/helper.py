"""
Helper functions used by the Outscale factory tools.
"""
import logging
import subprocess
import os


def check_cmd(cmd, data='', dryrun=False):
    """Run command, log everything, return a (bool,dict) tuple with command
    success and debug data."""
    logging.info('Running {}'.format(repr(cmd)))
    if dryrun:
        stderr = stdout = b''
        ret = 0
    else:
        popen = subprocess.Popen(cmd.split(' '), stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if data:
            stdout, stderr = popen.communicate(bytes(data, 'ascii'))
        else:
            stdout, stderr = popen.communicate()
        ret = popen.wait()
    error = dict(
        cmd=cmd,
        stdin=data,
        stdout=stdout.decode('utf-8', 'ignore'),
        stderr=stderr.decode('utf-8', 'ignore'),
        ret=ret
    )
    ok = (ret == 0)
    errstr = '''
CMD={cmd}
RET={ret}
STDIN=
{stdin}
STDOUT=
{stdout}
STDERR=
{stderr}
'''.format(**error)
    if ok:
        logging.debug(errstr)
    else:
        logging.error(errstr)
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
