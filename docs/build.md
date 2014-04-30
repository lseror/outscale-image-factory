# How to build a Turnkey Linux appliance

This document explains how to build a Turnkey Linux appliance for the Outscale cloud.

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

 1. Attach a new volume `/dev/sdb` to the factory VM. *The size of the volume should be 10GB*.
 
 2. Build the appliance:
 ```shell
 APP=tkldev
 mkdir /media/$APP
 rm -rf /tmp/$APP/product.*
 mkdir /tmp/$APP
 /turnkey/outscale/build_ami.py --verbose --mount-point=/media/$APP --work-dir=/tmp/$APP --turnkey-app=$APP --device=/dev/sdb 2>&1|tee /tmp/$APP/log
 ```

 3. Create the actual machine image from the `/dev/sdb` volume. This step is not (yet) integrated so it should be done by hand. The following example uses `awscli`:
 ```shell
 aws ec2 detach-volume --volume-id $VOLUME
 aws ec2 attach-volume --volume-id $VOLUME --instance-id $SOME_INSTANCE --device /dev/sda1
 aws ec2 create-image --instance-id $SOME_INSTANCE --name app-$APP
 aws ec2 detach-volume --volume-id $VOLUME
 ```
