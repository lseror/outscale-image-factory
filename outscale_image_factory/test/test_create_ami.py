"""
Unit tests for create_ami.
"""
import unittest
import boto
from outscale_image_factory import create_ami

DUMMY_INSTANCE_ID = 'DUMMY_INSTANCE_ID'

DEVICE_NAMES = set([
    '/dev/sdb',
    '/dev/sdc',
    '/dev/sdd',
    '/dev/sde',
    '/dev/sdf',
    '/dev/sdg',
    '/dev/sdh',
    '/dev/sdi',
    '/dev/sdj',
    '/dev/sdk',
    '/dev/sdl',
    '/dev/sdm',
    '/dev/sdn',
    '/dev/sdo',
    '/dev/sdp',
    '/dev/sdq',
    '/dev/sdr',
    '/dev/sds',
    '/dev/sdt',
    '/dev/sdu',
    '/dev/sdv',
    '/dev/sdw',
    '/dev/sdx',
    '/dev/sdy',
    '/dev/sdz',
])

assert len(DEVICE_NAMES) == 25


class TestCreateAmi(unittest.TestCase):

    def setUp(self):
        self.connection = boto.ec2.connect_to_region(create_ami.REGION)

    def test_allocate_device(self,
                             device_set=DEVICE_NAMES,
                             maxdev=len(DEVICE_NAMES),
                             instance_id=DUMMY_INSTANCE_ID):
        """
        Check that the generated sequence of devices is valid.
        """
        i = 0
        allocated = set()
        while i < maxdev:
            dev = create_ami._allocate_device(
                self.connection,
                instance_id,
                device_name_blacklist=allocated)
            allocated.add(dev)
            i += 1
        self.assertEqual(allocated, device_set)

    def test_allocate_device_failure(self):
        """
        Check that the function raises an exception when all devices are allocated.
        """
        exception = None
        try:
            self.test_allocate_device(maxdev=len(DEVICE_NAMES) + 1)
        except create_ami._OIFError as exception:
            pass
        self.assertIsNotNone(exception)
        self.assertTrue(isinstance(exception, Exception))


if __name__ == '__main__':
    unittest.main()
