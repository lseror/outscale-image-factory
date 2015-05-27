Turnkey Linux Factory for the Outscale Cloud
============================================

Image creation tools
--------------------

This package is part of a factory that generates [Turnkey
Linux](http://turnkeylinux.org) appliance images for the
[Outscale](http://www.outscale.com) cloud. Since the Outscale cloud provides an
EC2-compatible API, it should be fairly portable.

This package includes:
 * `tklpatch`: a collection of TKL patches needed to port TKL
   appliances to the Outscale cloud.
 * `outscale_image_factory`: Python package used to generate images of TLK appliances for
   the Outscale cloud.
 * `omi-factory`: A command line tool to create images, using `outscale_image_factory`.
 * `scripts`: miscellaneous shell scripts.

See the
[outscale-factory-master](http://github.com/nodalink/outscale-factory-master)
package documentation for further details.

See the
[Factory HOWTOs](http://nodalink.github.io/outscale-image-factory) for
additional info.
