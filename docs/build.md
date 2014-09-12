# Building a Turnkey Linux appliance

This document explains how to build a Turnkey Linux appliance by hand, using the `tkldev` instance that we [bootstrapped earlier](#docs/bootstrap).

This example rebuilds the `tkldev` appliance with itself. Each appliance is hosted in [its own repository on github](https://github.com/turnkeylinux-apps).

## First boot setup

1. Finish the TKL setup:

    ```
    cd /usr/local/sbin
    wget https://raw.githubusercontent.com/turnkeylinux-apps/tkldev/master/overlay/usr/local/sbin/tkldev-setup
    chmod +x tkldev-setup

    ./tkldev-setup
    ```

1. Install TKLPatch:

    ```
    cd /usr/src
    git clone https://github.com/turnkeylinux/tklpatch.git
    cd tklpatch
    make install
    ```

1. Install Outscale factory tools:

    ```
    apt-get install python-setuptools python3-setuptools wget
    make -C /usr/src/outscale-image-factory install
    ```

1. Configure Boto:

    Download the endpoints definition:

    ```
    cd /root
    wget https://raw.githubusercontent.com/nodalink/outscale-factory-master/master/overlay/etc/outscale-factory-master/endpoints.json
    ```

    Create `/root/.boto` with the following content:

    ```
    [Credentials]
    aws_access_key_id = <name>
    aws_secret_access_key = <secret>

    [Boto]
    endpoints_path = /root/endpoints.json
    ```

    `<name>` and `<secret>` come from the Outscale account profile. They are listed as "Access Keys" in the "Security" section.

## Creating an image for the appliance

 1. Grab the instance ID:
 ```
 INSTANCE_ID=$(wget -O- http://169.254.169.254/latest/meta-data/instance-id)
```

 2. Attach a new volume to the instance. On success `create_ami` will print the `VOLUME_ID` and `DEVICE` shell variables to `stdout`:
 ```
 eval $(create_ami -v --attach-new-volume $INSTANCE_ID)
 ```

 3. Build the appliance and copy it to the device:
 ```
 APP=tkldev
 build_ami -v --build --mount-point=/mnt/$APP --work-dir=/root/$APP --turnkey-app=$APP --device=$DEVICE 2>&1|tee /root/$APP.log
 ```
 
 4. Create the machine image from the volume:
 ```
 create_ami -v --create-image app-$APP --volume-id $VOLUME_ID
 ```
 
 5. Cleanup:
```
 build_ami -v --clean --turnkey-app=$APP
 create_ami -v --destroy-volume $VOLUME_ID
 ```
