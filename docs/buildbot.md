# Building and Installing a Buildbot

## Global Overview

Creating a Buildbot from scratch can be done by following these steps:

1. Bootstrap a TKLDev image

2. Build an image of a Buildbot master

3. Build an image of a Buildbot slave

4. Instantiate a master

5. Instantiate slaves

## Bootstrap

1. Follow the [bootstrap howto](#docs/bootstrap).

2. Create a instance of the TKLDev image you just created.

## Build Buildbot AMIs

1. Connect to the TKLDev instance.

2. Build an image for the Buildbot master by following the [Build a TKL app howto](#docs/build). When it is time to call `build_ami`, use "outscale-factory-master" as the app name and pass it the `--turnkey-apps-git https://github.com/nodalink` argument (otherwise `build_ami` will look for the "outscale-factory-master" repository in the turnkeylinux-apps account on Github).

3. In the same way, create an image for the Buildbot slave, this time using "outscale-factory-slave" as the app name.

## Instantiate Images

### Instantiating the Master

1. Create an instance using the previously created "app-outscale-factory-master" instance.

2. Connect to it with ssh.

3. Edit `/var/lib/buildbot/.boto`, and add the "Credentials" group, like so:

    ```
    [Credentials]
    aws_access_key_id = <name>
    aws_secret_access_key = <secret>
    ```

    `<name>` and `<secret>` come from the Outscale account profile. They are listed as "Access Keys" in the "Security" section.

4. The Buildbot configuration requires an authenticated user to trigger builds. Add a user with:

    ```
    htpasswd -d /etc/outscale-factory-master/htpasswd <username>
    ```

    (The `-d` switch tells `htpasswd` to use CRYPT encryption, the only supported encryption in Buildbot 0.8.6p1)

5. Restart Buildbot with `invoke-rc.d buildmaster restart` (so that the changes to Boto credentials are taken into account)

The web interface should be available on port 8010.

### Instantiating a Slave

1. Connect to the master with ssh.

2. Edit `/etc/outscale-factory-master/user.json` and make sure there is an entry in the `plain_slaves` list for the new slave

3. Restart Buildbot with `invoke-rc.d buildmaster restart`.

4. Create an instance using the previously created "app-outscale-factory-slave" image.

5. Connect to it with ssh.

6. Edit `/etc/outscale-factory-slave/slave.json`
    - Set `ec2_slave` to false (It defaults to true so that the image can be used to build ec2 slaves as well, which must work without any manual intervention)
    - Define `buildmaster_host` to the IP address of the Buildbot Master machine
    - Define `slavename` and `passwd` as defined on the master in step 2.

7. Restart the slave with `invoke-rc.d buildslave restart`. The slave should be marked  connected in the list of build slaves on Buildbot Master web interface.

### Troubleshooting

Buildbot logs output to a file named `twistd.log`. On the master it is located in `/srv/outscale-buildbot-master`. On slaves it is in `/srv/outscale-builbot-slave`.
