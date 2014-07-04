# Bootstraping a Turnkey Linux factory on the Outscale cloud

 1. Create a Linux instance. This example uses a Debian Squeeze instance. Attach a `20GB` volume named `/dev/sdb` to the instance.

 2. Open a shell on the instance and install the dependencies:
 ```
apt-get update
apt-get install qemu-utils unzip parted lvm2 git rsync wget
 ```
 
 3. Download the [tkldev appliance VMDK](http://www.turnkeylinux.org/tkldev) and unpack it:
 ```
ZIPFILE=turnkey-tkldev-13.0-wheezy-amd64-vmdk.zip
wget http://downloads.sourceforge.net/project/turnkeylinux/vmdk/$ZIPFILE
 unzip $ZIPFILE
 cd turnkey-tkldev-13.0-wheezy-amd64/
 ```

 4. Convert the VMDK to a raw image with `qemu-img` and copy it to `/dev/sdb`:
 ```
 qemu-img convert -O raw \
	 turnkey-tkldev-13.0-wheezy-amd64.vmdk \
	 turnkey-tkldev-13.0-wheezy-amd64.raw
 cp turnkey-tkldev-13.0-wheezy-amd64.raw /dev/sdb
 sync
 ```

 5. Activate the LVM volume:
 ```
 partprobe /dev/sdb
 vgscan
 vgchange -ay turnkey
 sleep 3
 ```
 
 6. Mount the filesystems under `/mnt`:
  ```
 mount /dev/mapper/turnkey-root /mnt
 mount /dev/sdb1 /mnt/boot
 mount --bind /dev /mnt/dev
 mount --bind /proc /mnt/proc
 mount --bind /sys /mnt/sys
```

 7. Clone the factory tools under `/mnt/usr/src`:
 ```
 cd /mnt/usr/src
 git clone https://github.com/nodalink/outscale-image-factory.git
 ```
	 
 8. Apply the Turnkey Linux patches by hand:
 ```
 CHROOT=/mnt
 TOOLS=/usr/src/outscale-image-factory
 rsync -av $CHROOT/$TOOLS/tklpatch/headless/overlay/ $CHROOT/
 rsync -av $CHROOT/$TOOLS/tklpatch/outscale/overlay/ $CHROOT/
 chroot $CHROOT $TOOLS/tklpatch/outscale/conf
 ```

 8. Update the grub config:
 ```
 chroot /mnt update-grub
 ```

 10. Cleanup:
 ```
 sync
 umount /mnt/boot
 umount /mnt/dev
 umount /mnt/proc
 umount /mnt/sys
 umount /mnt
 ```

 11. Detach the `/dev/sdb` volume, attach it as the root filesystem on an instance (`/dev/sda1`) and boot the factory.
