# How to bootstrap the Turnkey Linux factory

 This document explains how to create a Turnkey Linux factory from scratch on the Outscale cloud.

 1. Create a Linux VM named `bootstrap` with two volumes. This example uses a Debian Squeeze VM with the second volume mounted on `/dev/sdb`. *The size of `/dev/sdb` must be at least 20GB*.

 2. On the `bootstrap` VM install the the dependencies:
 ```shell
apt-get update
apt-get install qemu-utils unzip parted lvm2 git
 ```
 
 3. Download the [Turnkey factory appliance](http://www.turnkeylinux.org/tkldev) and unpack it:
 ```shell
 wget http://downloads.sourceforge.net/project/turnkeylinux/vmdk/turnkey-tkldev-13.0-wheezy-amd64-vmdk.zip

 unzip turnkey-tkldev-13.0-wheezy-amd64-vmdk.zip
 cd turnkey-tkldev-13.0-wheezy-amd64/
 ```

 4. Convert it to a raw image with `qemu-img` and copy it to `/dev/sdb`:
 ```shell
 qemu-img convert -O raw turnkey-tkldev-13.0-wheezy-amd64.vmdk turnkey-tkldev-13.0-wheezy-amd64.raw

 cp turnkey-tkldev-13.0-wheezy-amd64.raw /dev/sdb
 sync
 ```

 5. Activate the LVM volume:
 ```shell
 partprobe /dev/sdb
 vgscan
 vgchange -ay turnkey
 sleep 3
 ```
 
 6. Mount the factory on `/mnt`:
  ```shell
 mount /dev/mapper/turnkey-root /mnt
 mount /dev/sdb1 /mnt/boot
 mount --bind /dev /mnt/dev
 mount --bind /proc /mnt/proc
 mount --bind /sys /mnt/sys
```

 7. Download the factory tools:
 ```shell
 git clone https://github.com/nodalink/outscale-image-factory.git /mnt/turnkey/outscale
 ```
	 
 8. Apply the patches by hand:
 ```
 rsync -av /mnt/turnkey/outscale/tklpatch/headless/overlay/ /mnt/turnkey/
 rsync -av /mnt/turnkey/outscale/tklpatch/outscale/overlay/ /mnt/turnkey/

 chroot /mnt/turnkey /turnkey/outscale/tklpatch/outscale/conf
 ```

 8. Update grub config:
 ```shell
 chroot /mnt/turnkey update-grub
 ```

 10. Sync and unmount:
 ```shell
 sync
 umount /mnt/boot
 umount /mnt/dev
 umount /mnt/proc
 umount /mnt/sys
 umount /mnt
 ```

 11. The factory on `/dev/sdb` should now be ready to boot.
 
