# Creating a Debian GNU/Linux or Ubuntu image on the Outscale cloud

 1. Create a Linux instance. This examples uses a CentOS 6.5 instance. Attach a new volume named `/dev/sdb` to the instance.

 2. Download the [image creation script](https://github.com/nodalink/outscale-image-factory/blob/master/scripts/create-debian-ami.sh) and make it executable:
```
wget https://raw.githubusercontent.com/nodalink/outscale-image-factory/master/scripts/create-debian-ami.sh
 chmod +x ./create-debian-ami.sh
```
 3. **Download the Debian or Ubuntu archive signing keys and copy them to your Linux instance**. You have several options to accomplish this step:
      1. Download the Debian archive signing key from [ftp-master.debian.org](https://ftp-master.debian.org/keys.html). At the time of this writing the Debian archive signing key is named `2012/wheezy`.
	  2. Download the Ubuntu archive signing key from some random source. This is probably a bad idea.
      3. **Recommended option**: get the keys from an existing Debian or Ubuntu installation and copy them to your CentOS instance: 
```
apt-get install debian-archive-keyring ubuntu-archive-keyring
scp /usr/share/keyrings/{debian-archive-keyring.gpg,ubuntu-archive-keyring.gpg} centos:
```
 
 4. Run the image creation script.

	The following example creates a **Debian wheezy** image:
```
./create-debian-ami.sh \
    /dev/sdb \
    ./debian-archive-keyring.gpg \
    amd64 \
    wheezy \
    http://ftp.fr.debian.org/debian
```

	The following example creates an **Ubuntu trusty** image:
```
./create-debian-ami.sh \
    /dev/sdb \
    ./ubuntu-archive-keyring.gpg \
    amd64 \
    trusty \
    http://ubuntu-archive.mirrors.free.org/ubuntu/
```

 5. On a fresh CentOS instance, the script will most likely complain about missing dependencies. Install the missing dependencies:
```
yum install -y centos-release-SCL
yum install -y git parted python33
```

 6. Run the script again (*repeat step 4*) and grab some coffee.
	 
 7. Once the build process finishes, detach the `/dev/sdb` volume and convert it to a machine image.
