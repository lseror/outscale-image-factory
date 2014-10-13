# Creating a Debian GNU/Linux or Ubuntu image on the Outscale cloud

1. **Create a Linux instance.** This example uses **CentOS 6.5**.

2. **Attach a new volume** named `/dev/sdb` to the instance.

3. **Download the [image creation script](https://github.com/nodalink/outscale-image-factory/blob/master/scripts/create-debian-ami.sh)** and make it executable:

    ```
    wget https://raw.githubusercontent.com/nodalink/outscale-image-factory/master/scripts/create-debian-ami.sh
    chmod +x ./create-debian-ami.sh
    ```

4. **Download the Debian or Ubuntu archive signing keys** and copy them to the instance:
    1. **For Debian** the keys are available from [ftp-master.debian.org](https://ftp-master.debian.org/keys.html).
    2. **For Ubuntu** the keys are available from the source package:

        ```
        TGZ=ubuntu-keyring_2012.05.19.tar.gz
        wget http://archive.ubuntu.com/ubuntu/pool/main/u/ubuntu-keyring/$TGZ
        tar xvzf $TGZ
        ```

    3. **Another option** is to get the keys from an existing Debian or Ubuntu installation and to copy them to the instance:

        ```
        apt-get install debian-archive-keyring ubuntu-archive-keyring
        scp /usr/share/keyrings/{debian-archive-keyring.gpg,ubuntu-archive-keyring.gpg} \
        <centos_instance>:
        ```

5. **Install missing dependencies**. On **CentOS 6.5** install `git`, `parted` and `python33`. To install Python 3.3, install the [SCL](http://wiki.centos.org/AdditionalResources/Repositories/SCL) release file first:

    ```
    yum install -y git parted
    yum install -y centos-release-SCL
    yum install -y python33
    ```

6. **Run the image creation script**.

    1. For **Debian wheezy**:

        ```
        ./create-debian-ami.sh \
        /dev/sdb \
        ./debian-archive-keyring.gpg \
        amd64 \
        wheezy \
        http://ftp.fr.debian.org/debian
        ```

    2. For **Ubuntu trusty**:

        ```
        ./create-debian-ami.sh \
        /dev/sdb \
        ./ubuntu-keyring-2012.05.19/keyrings/ubuntu-archive-keyring.gpg \
        amd64 \
        trusty \
        http://ubuntu-archive.mirrors.free.org/ubuntu/
        ```

7. **Detach** the `/dev/sdb` volume.

8. **Create an OMI** from the volume.
