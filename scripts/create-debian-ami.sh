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

# Urls
GIT_TOOLS='https://github.com/nodalink/outscale-image-factory.git'

DEBOOTSTRAP_VERSION="1.0.48+deb7u2"
DEBOOTSTRAP_URL="http://ftp.debian.org/debian/pool/main/d/debootstrap/debootstrap_${DEBOOTSTRAP_VERSION}.tar.gz"

MAKEDEV_VERSION=2.3.1
MAKEDEV_URL="http://ftp.debian.org/debian/pool/main/m/makedev/makedev_${MAKEDEV_VERSION}.orig.tar.gz"

# Dirs & paths
BASEDIR=$(pwd)
SRCDIR=${BASEDIR}/src
BUILDDIR=${BASEDIR}/build
mkdir -p $SRCDIR $BUILDDIR

ROOTFS=${BUILDDIR}/${DISTRO}
DEBOOTSTRAP_DIR=$SRCDIR/debootstrap-${DEBOOTSTRAP_VERSION}
MAKEDEV=$SRCDIR/makedev-${MAKEDEV_VERSION}.orig/MAKEDEV
PYTHONPATH=$SRCDIR/outscale-image-factory
OVERLAY=$SRCDIR/outscale-image-factory/tklpatch/outscale/overlay
export DEBOOTSTRAP_DIR PYTHONPATH

# Chroot setup
DEBIAN_KERNEL="linux-image-$ARCH"
UBUNTU_KERNEL="linux-image-generic"
LANG=C.UTF-8
DEBIAN_FRONTEND=noninteractive
export LANG DEBIAN_FRONTEND

PACKAGES="openssh-server wget grub-pc"

git_clone()
{
    local repo=$1
    local dir=$2
    test -e $dir || git clone $repo $dir
}

step()
{
    echo "=== $*"
}

get_python2_version()
{
    python2 <<EOF
import sys
print("%d.%d" % sys.version_info[:2])
EOF
}

setup_centos_python()
{
    local version=$1
    local python_root=/opt/rh/python${version}/root
    if [ ! -d $python_root ] ; then
        return
    fi
    step "Setting up paths for CentOS"
    PATH=$python_root/usr/bin:$PATH
    LD_LIBRARY_PATH=""
    LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$python_root/usr/lib
    LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$python_root/usr/lib64
    export PATH LD_LIBRARY_PATH
}

missing_dependency()
{
    echo "Missing dependency: $1"
    echo "For CentOS see: http://wiki.centos.org/AdditionalResources/Repositories/SCL"
    exit 1
}

step "Checking for root"
if [ "$(whoami)" != "root" ]
then
    echo "Please run this script as root."
    exit 1
fi

step "Checking for $DEVICE"
if [ ! -e "$DEVICE" ]
then
    echo "Please attach a 10GB volume."
    exit 1
fi

step "Checking Python2 version"
if [ "$(get_python2_version)" != "2.7" ] ; then
    setup_centos_python 27
    if [ "$(get_python2_version)" != "2.7" ] ; then
        missing_dependency "python 2.7"
    fi
fi

step "Checking other dependencies"
for bin in wget git make rsync gpg parted
do
    if ! which $bin >/dev/null
    then
        missing_dependency "$bin"
    fi
done

step "Getting remote code"
curl $MAKEDEV_URL | tar -C $SRCDIR -xz
if [ ! -e $MAKEDEV ]
then
    echo "makedev tarball does not contain the MAKEDEV script"
    exit 1
fi
chmod +x $MAKEDEV

curl $DEBOOTSTRAP_URL | tar -C $SRCDIR -xz
git_clone $GIT_TOOLS $SRCDIR/outscale-image-factory

step "Building debootstrap"
make -C $DEBOOTSTRAP_DIR devices.tar.gz MAKEDEV=$MAKEDEV

if [ ! -d $ROOTFS ] ; then
    step "Running debootstrap"
    $DEBOOTSTRAP_DIR/debootstrap \
        --verbose --keyring=$KEYRING --arch=$ARCH \
        $DISTRO $ROOTFS $MIRROR
fi

step "Creating sources.list"
python2 -m outscale_image_factory.create_sources_list  \
    $ROOTFS/etc/apt/sources.list $MIRROR $DISTRO

step "Repopulating /dev"
# If we don't recreate the content of /dev, /dev/urandom does not exist and
# installation of openssh-server fails
mount -t proc none $ROOTFS/proc
mount -t sysfs none $ROOTFS/sys
chroot $ROOTFS apt-get update
chroot $ROOTFS apt-get install makedev
chroot $ROOTFS /sbin/MAKEDEV

step "Installing packages"
# This policy-rc.d file prevents daemons from starting on install/upgrade
# See https://people.debian.org/~hmh/invokerc.d-policyrc.d-specification.txt
POLICY_HELPER=$ROOTFS/usr/sbin/policy-rc.d
echo 'exit 101' > $POLICY_HELPER
chmod +x $POLICY_HELPER

if [ -n "$(chroot $ROOTFS apt-cache search --names-only ^$DEBIAN_KERNEL$)" ]
then
    KERNEL_PACKAGE=$DEBIAN_KERNEL
else
    KERNEL_PACKAGE=$UBUNTU_KERNEL
fi

chroot $ROOTFS apt-get install -y $KERNEL_PACKAGE $PACKAGES
chroot $ROOTFS apt-get dist-upgrade -y

rm $POLICY_HELPER
umount $ROOTFS/proc
umount $ROOTFS/sys

step "Copying overlay"
rsync -rlpDv $OVERLAY/ $ROOTFS/

step "Creating dummy files"
touch $ROOTFS/usr/lib/inithooks/firstboot.d/30turnkey-init-fence
cat <<EOF >$ROOTFS/etc/default/inithooks
INITHOOKS_CONF=/etc/inithooks.conf
EOF

step "Adding hooks to /etc/rc.local"
cat <<EOF >$ROOTFS/etc/rc.local
#!/bin/sh
FIRSTBOOT=/usr/lib/inithooks/firstboot.d/99outscale
EVERYBOOT=/usr/lib/inithooks/everyboot.d/99outscale
test -x \$FIRSTBOOT && \$FIRSTBOOT
chmod +x \$EVERYBOOT
\$EVERYBOOT
EOF

step "Disabling root account"
chroot $ROOTFS passwd -d root
chroot $ROOTFS passwd -l root

step "Cleaning up rootfs"
chroot $ROOTFS apt-get clean
chroot $ROOTFS find /var/log -type f -exec rm {} +

step "Copying rootfs to device"
python2 -m outscale_image_factory.main \
    install-rootfs --device=$DEVICE $ROOTFS
