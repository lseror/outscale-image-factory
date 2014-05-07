# How to build a Turnkey Linux appliance

This document explains how to build a Turnkey Linux appliance by hand, using the factory that we [bootstrapped earlier](#docs/bootstrap).

## Factory setup

On a fresh factory instance two initial steps are needed:

 1. Check that the outscale-image-factory tools are installed in `/turnkey/outscale`:
 ```shell
 test -e /turnkey/outscale || git clone https://github.com/nodalink/outscale-image-factory.git /turnkey/outscale
 ```

 2. Run the setup script. The script downloads data used by all Turnkey Linux appliances in the `/turnkey/fab` directory.
 ```shell
 /turnkey/outscale/tkldev-setup.sh
 ```

## Building an appliance

This example rebuilds the `tkldev` appliance with itself. Each appliance is hosted in [its own repository on github](https://github.com/turnkeylinux-apps).

 0. Setup the environment:
 ```shell
 PATH=$PATH:/turnkey/outscale
 INSTANCE_ID=$(wget -O- http://169.254.169.254/latest/meta-data/instance-id)
```

 1. Attach a new volume to the factory. Record the result.
 ```shell
 create_ami.py -v -v --attach-new-volume $INSTANCE_ID
 DEVICE=/dev/SOMETHING
 VOLUME_ID=vol-SOMETHING
 ```

 2. Build the appliance on the volume:
 ```shell
 APP=tkldev
 build_ami.py -v -v --build --mount-point=/srv/rootfs/$APP --work-dir=/srv/patch/$APP --turnkey-app=$APP --device=$DEVICE 2>&1|tee /tmp/$APP.log
 ```

 3. Create the actual machine image and cleanup:
 ```shell
 create_ami.py -v -v --create-image app-$APP --volume-id $VOLUME_ID
 build_ami.py -v -v --clean --turnkey-app=$APP
 create_ami.py -v -v --destroy-volume $VOLUME_ID
 ```
