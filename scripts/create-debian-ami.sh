#!/bin/sh
#
# Create a Debian or Ubuntu image for the Outscale cloud.
#
# Copyright (c) 2014, Vincent Crevot
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
set -u 
set -e
#set -x

# Arg check
if [ "$#" != 5 ]
then
    echo "Usage:"
    echo "$0 DEVICE KEYRING \\"
    echo "      ARCH DISTRO MIRROR"
    echo ""
    echo "Examples:"
    echo "$0 /dev/sdb ./debian-archive-keyring.gpg \\"
    echo "     amd64 wheezy http://ftp.fr.debian.org/debian"
    echo ""
    echo "$0 /dev/sdb ./ubuntu-archive-keyring.gpg \\"
    echo "     amd64 trusty http://ubuntu-archive.mirrors.free.org/ubuntu/"
    exit 1
fi

# Args
DEVICE=$1
KEYRING=$2
ARCH=$3
DISTRO=$4
MIRROR=$5

# Dirs & paths
BASEDIR=$(pwd)
ROOTFS=${BASEDIR}/${DISTRO}
DEBOOTSTRAP_DIR=$BASEDIR/debootstrap
MAKEDEV=$BASEDIR/makedev/MAKEDEV
PYTHONPATH=$BASEDIR/outscale-image-factory
OVERLAY=$BASEDIR/outscale-image-factory/tklpatch/outscale/overlay
export DEBOOTSTRAP_DIR PYTHONPATH

# Gits
GIT_DEBOOTSTRAP='git://anonscm.debian.org/d-i/debootstrap.git'
#GIT_MAKEDEV='git://git.gag.com/debian/makedev'
GIT_MAKEDEV='git://50.198.211.89/debian/makedev'
GIT_TOOLS='git://github.com/nodalink/outscale-image-factory.git'

# Chroot setup
DEBIAN_KERNEL="linux-image-$ARCH"
UBUNTU_KERNEL="linux-image-generic"
LANG=C.UTF-8
DEBIAN_FRONTEND=noninteractive
export LANG DEBIAN_FRONTEND

git_clone()
{
    local repo=$1
    local dir=$2
    test -e $dir || git clone $repo $dir
}

echo "Checking for root"
if [ "$(whoami)" != "root" ]
then
    echo "Please run this script as root."
    exit 1
fi

echo "Checking for $DEVICE"
if [ ! -e "$DEVICE" ]
then
    echo "Please attach a 10GB volume."
    exit 1
fi

echo "Setting up paths for CentOS"
${LD_LIBRARY_PATH=:}
for version in 34 33 32
do
    python_root=/opt/rh/python${version}/root
    PATH=$python_root/usr/bin:$PATH
    LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$python_root/usr/lib
    LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$python_root/usr/lib64
done
export PATH LD_LIBRARY_PATH

echo "Checking for dependencies"
for bin in wget git make rsync gpg parted python3
do
    if ! which $bin >/dev/null
    then
	echo "Missing dependency: $bin"
	echo "For CentOS see: http://wiki.centos.org/AdditionalResources/Repositories/SCL"
	exit 1
    fi
done

echo "Cloning git repos"
git_clone $GIT_MAKEDEV $BASEDIR/makedev
git_clone $GIT_DEBOOTSTRAP $BASEDIR/debootstrap
git_clone $GIT_TOOLS $BASEDIR/outscale-image-factory

echo "Building debootstrap"
chmod +x $MAKEDEV
make -C $DEBOOTSTRAP_DIR devices.tar.gz MAKEDEV=$MAKEDEV

echo "Running debootstrap"
test -e $ROOTFS || $DEBOOTSTRAP_DIR/debootstrap \
    --verbose --keyring=$KEYRING --arch=$ARCH --include=openssh-server,wget \
    $DISTRO $ROOTFS $MIRROR

echo "Creating sources.list"
python3 -m outscale_image_factory.create_sources_list  \
    $ROOTFS/etc/apt/sources.list $MIRROR $DISTRO

echo "Installing packages"
mount --bind /proc $ROOTFS/proc
chroot $ROOTFS apt-get update
if [ -n "$(chroot $ROOTFS apt-cache search --names-only ^$DEBIAN_KERNEL$)" ]
then
    chroot $ROOTFS apt-get install -y $DEBIAN_KERNEL grub-pc
else
    chroot $ROOTFS apt-get install -y $UBUNTU_KERNEL grub-pc
fi
chroot $ROOTFS apt-get dist-upgrade -y
umount $ROOTFS/proc

echo "Copying overlay"
rsync -rlpDv $OVERLAY/ $ROOTFS/

echo "Creating dummy files"
touch $ROOTFS/usr/lib/inithooks/firstboot.d/30turnkey-init-fence
cat <<EOF >$ROOTFS/etc/default/inithooks
INITHOOKS_CONF=/etc/inithooks.conf
EOF

echo "Adding hooks to /etc/rc.local"
cat <<EOF >$ROOTFS/etc/rc.local
#!/bin/sh
FIRSTBOOT=/usr/lib/inithooks/firstboot.d/99outscale
EVERYBOOT=/usr/lib/inithooks/everyboot.d/99outscale
test -x \$FIRSTBOOT && \$FIRSTBOOT
chmod +x \$EVERYBOOT
\$EVERYBOOT
EOF

echo "Disabling root account"
chroot $ROOTFS passwd -d root
chroot $ROOTFS passwd -l root

echo "Cleaning up rootfs"
chroot $ROOTFS apt-get clean
chroot $ROOTFS find /var/log -type f -exec rm {} +

echo "Copying rootfs to device"
python3 -m outscale_image_factory.build_ami_from_rootfs \
    -v --device=$DEVICE --rootfs=$ROOTFS
