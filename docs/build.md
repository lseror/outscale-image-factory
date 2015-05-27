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
    apt-get update
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

By default the commands use the `eu-west-1` region and `eu-west-1a` zone. You can pass `--region` and `--volume-location` to override these values.

1. Create a 10 GiB volume and attach it to the instance. On success `omi-factory` will print the `VOLUME_ID` and `DEVICE` shell variables to `stdout`:

    ```
    eval $(omi-factory create-volume 10)
    ```

2. Build the appliance .iso file:

    ```
    APP=tkldev
    omi-factory tkl-build $APP
    ```

    or if you want to get the appliance from a different repository:

    ```
    omi-factory tkl-build --turnkey-apps-git https://github.com/foo $APP
    ```

    This will pull the appliance definition from `https://github.com/foo/$APP` instead of `https://github.com/turnkeylinux-apps`.


3. Install the .iso to the volume:

    ```
    omi-factory tkl-install-iso --device $DEVICE $APP
    ```

4. Create the machine image from the volume:

    ```
    omi-factory create-image app-$APP --volume-id $VOLUME_ID
    ```

5. Cleanup:

    ```
    omi-factory tkl-clean $APP
    omi-factory destroy-volume $VOLUME_ID
    ```
