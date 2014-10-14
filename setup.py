from setuptools import setup
import sys


if sys.version_info[0] != 2 or sys.version_info[1] < 7:
    raise Exception('This package requires Python 2.7')

req = [
    'boto',
    'PyGithub>=1.25',
    ]

scripts = [
    'omi-factory=outscale_image_factory.main:main',
    'cleanup=outscale_image_factory.cleanup:main',
    'find_package_references=outscale_image_factory.find_package_references:main',
    'tklgit=outscale_image_factory.tklgit:main',
    'create_fstab=outscale_image_factory.create_fstab:main',
    'create_sources_list=outscale_image_factory.create_sources_list:main',
    ]

setup(
    name='outscale_image_factory',
    version='0.1',
    description='Tools used to generate images for the Outscale cloud',
    url='http://github.com/nodalink/outscale-image-factory',
    author='Vincent Crevot',
    author_email=None,
    license='BSD',
    packages=['outscale_image_factory'],
    zip_safe=False,
    entry_points=dict(console_scripts=scripts),
    install_requires=req,
)
