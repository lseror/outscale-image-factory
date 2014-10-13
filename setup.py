from setuptools import setup
import sys

req = []
scripts = []

if sys.version_info[0] == 2:
    if sys.version_info[1] < 7:
        raise Exception('This package requires Python 2.7')
    req.append('boto')
    scripts.append('create_ami=outscale_image_factory.create_ami_old:main')
    scripts.append('cleanup=outscale_image_factory.cleanup:main')
    scripts.append('find_package_references=outscale_image_factory.find_package_references:main')
    scripts.append('omi-factory=outscale_image_factory.main:main')

if sys.version_info[0] == 3:
    if sys.version_info[1] < 2:
        raise Exception('This package requires Python 3.2 or later')
    req.append('PyGithub>=1.25')
    scripts.append('build_ami=outscale_image_factory.build_ami_old:main')
    scripts.append('tklgit=outscale_image_factory.tklgit:main')
    scripts.append('create_fstab=outscale_image_factory.create_fstab:main')
    scripts.append('create_sources_list=outscale_image_factory.create_sources_list:main')

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
