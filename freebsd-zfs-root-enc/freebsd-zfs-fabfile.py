"""
    FreeBSD encrypted root install on ZFS, via Fabric

    Adapted from:
       https://www.dan.me.uk/blog/2012/05/06/full-disk-encryption-with-zfs-root-for-freebsd-9-x/

    Software versions:
        Python 2.7.5
        pip 1.4.1
        Fabric 1.8.0
        Paramiko 1.12.0

    Invocation: (call it task by task if you like)
        $ fab -I -k -f freebsd-zfs-fabfile.py -u root -H {HOST} full_install

    !!! NOTE !!! I had to use the '-I' and then just hit 'enter' when prompted for env.password,
        in order to use an empty password. Seems like a bug...

    Assumes root over SSH. This is intended to be run on the live CD / image shell, but could be
    run on any FreeBSD system really. Note that I started sshd on the live filesystem with the
    following config file in /tmp:

        Subsystem       sftp    /usr/libexec/sftp-server
        PermitRootLogin yes
        StrictModes no
        PubkeyAuthentication no
        PasswordAuthentication yes
        PermitEmptyPasswords yes
        ChallengeResponseAuthentication no
        UsePAM no

    Then I created a temporary host key file in /tmp, called 'host'. Finally I invoked sshd as:

        root@:~ # /usr/sbin/sshd -f /tmp/sshd_config -h /tmp/host

    Of course, you could actually create authorized_keys file, etc, but I was doing the install
    from a trusted host on a local network. Also, I don't think you can create a lesser privileged
    user on the live filesystem?

    Obnoxiously, this technique of completely insecure root login was not easily discovered on
    Google as searching for 'passwordless ssh root login' and terms of that nature mostly
    turned up articles about how to use ssh-keygen and the like for people new to SSH.
    The key here is really in the man pages - most of the directives are self explanatory
    but 'PermitRootLogin without-password' means 'don't allow password authentication for root.'

    Go ahead, laugh it up. ;)
    
    --- zbrdge / November 2013
"""

import os
from fabric.api import run, env, execute, settings, cd
from fabric.operations import put, local
from fabric.contrib.files import append

# -------------------
# Fabric variables
# -------------------
# Use your SSH config file if you like:
env.use_ssh_config = True
env.shell = '/bin/sh -c'  # No bash by default on FreeBSD

# -------------------
# Config variables
# -------------------
dev_prefix = "ada"
# I only have one disk right now.
# Should handle multiple, but I haven't tested that:
disks       = 1
zroot_mnt   = '/boot/zfs/zroot'

# chroot utility (does fabric provide this yet?)
def chroot(cmd=''):
    run('chroot '+zroot_mnt+' %s' % (cmd))

# -------------------
# Partition Setup
# -------------------
def partition_setup():
    for i in range(disks):
        # destroy the label if it exists already
        run('gpart destroy -F ' + dev_prefix + str(i))

        # disk label
        run('gpart create -s gpt ' + dev_prefix + str(i))

        # unecrypted loader partition:
        run('gpart add -s 128 -t freebsd-boot ' + dev_prefix + str(i))

        # encrypted boot partition
        run('gpart add -s 10G -t freebsd-zfs ' + dev_prefix + str(i))

        # encrypted root partition (remaining space)
        run('gpart add -t freebsd-zfs ' + dev_prefix + str(i))

        # write stage 1 bootcode / MBR
        run('gpart bootcode -b /boot/pmbr -p /boot/gptzfsboot -i 1 ' + dev_prefix + str(i))

# -------------------
# temporary RAM disk
# -------------------
def ram_disk():
    run('mdconfig -a -t malloc -s 128m -u 2')
    run('newfs -O2 /dev/md2')
    run('mount /dev/md2 /boot/zfs')

# -------------------
# kernel mod deps
# -------------------
def kernel_mods():
    run('kldload opensolaris')
    run('kldload zfs')
    run('kldload geom_eli')

# -------------------
# loader partition
# -------------------
def loader_partition():
    # a.k.a: the unencrypted boot partition, mirrored

    disk_names = '/dev/'+dev_prefix+'0p2'
    if disks > 1:
        for i in range(disks-1):
            disk_names += ' /dev/'+dev_prefix+str(i+1)+'p2'
        run('zpool create -f -m /boot/zfs/bootdir bootdir mirror '+disk_names)
    else:
        run('zpool create -f -m /boot/zfs/bootdir bootdir '+disk_names)

    run('zpool set bootfs=bootdir bootdir')

# -------------------
# generate disk key,
# save it locally
# -------------------
def key_gen():
    local('dd if=/dev/random of=encryption.key bs=4096 count=1')
    put('encryption.key', '/boot/zfs/bootdir/encryption.key')

# -------------------
# geli init/attach
# -------------------
def geli_init():
    print('[!] INITIALIZING ENCRYPTED DISKS')
    for i in range(disks):
        run('geli init -b -B /boot/zfs/bootdir/' + dev_prefix+str(i) +
            'p3.eli -e AES-XTS -K /boot/zfs/bootdir/encryption.key -l 256 -s 4096 /dev/' +
            dev_prefix+str(i) + 'p3')
        run('geli attach -k /boot/zfs/bootdir/encryption.key /dev/' + dev_prefix+str(i) + 'p3')

# -------------------
# build root fs
# -------------------
def build_root():
    disk_names = '/dev/'+dev_prefix+'0p3.eli'
    if disks > 1:
        for i in range(disks-1):
            disk_names += ' /dev/'+dev_prefix+str(i+1)+'p3.eli'
        run('zpool create -f zroot raidz1 '+disk_names)
    else:
        run('zpool create -f zroot '+disk_names)

    # -------------------
    # copied and pasted from the excellent blog post above.
    # see the article and man pages for more info.
    # -------------------
    run('zfs set mountpoint='+zroot_mnt+' zroot')
    run('zfs mount zroot')
    run('zfs unmount bootdir')
    run('mkdir '+zroot_mnt+'/bootdir')
    run('zfs set mountpoint='+zroot_mnt+'/bootdir bootdir')
    run('zfs mount bootdir')
    run('zfs set checksum=fletcher4 zroot')
    run('zfs create -o compression=on -o exec=on -o setuid=off zroot/tmp')
    run('chmod 1777 '+zroot_mnt+'/tmp')
    run('zfs create zroot/usr')
    run('zfs create zroot/usr/home')
    run('cd '+zroot_mnt+'; ln -s /usr/home home')
    run('zfs create -o compression=lzjb -o setuid=off zroot/usr/ports')
    run('zfs create -o compression=off -o exec=off -o setuid=off zroot/usr/ports/distfiles')
    run('zfs create -o compression=off -o exec=off -o setuid=off zroot/usr/ports/packages')
    run('zfs create zroot/var')
    run('zfs create -o compression=lzjb -o exec=off -o setuid=off zroot/var/crash')
    run('zfs create -o exec=off -o setuid=off zroot/var/db')
    run('zfs create -o compression=lzjb -o exec=on -o setuid=off zroot/var/db/pkg')
    run('zfs create -o exec=off -o setuid=off zroot/var/empty')
    run('zfs create -o compression=lzjb -o exec=off -o setuid=off zroot/var/log')
    run('zfs create -o compression=gzip -o exec=off -o setuid=off zroot/var/mail')
    run('zfs create -o exec=off -o setuid=off zroot/var/run')
    run('zfs create -o compression=lzjb -o exec=on -o setuid=off zroot/var/tmp')
    run('chmod 1777 '+zroot_mnt+'/var/tmp')


# -------------------
# install FreeBSD
# -------------------
def install_freebsd():
    with cd(zroot_mnt):
        run('unxz -c /usr/freebsd-dist/base.txz | tar xpf -')
        run('unxz -c /usr/freebsd-dist/kernel.txz | tar xpf -')
        run('unxz -c /usr/freebsd-dist/src.txz | tar xpf -')

# -------------------
# post-install config
# -------------------
def post_install():

    run("zfs set readonly=on zroot/var/empty")
    chroot("mv /boot /bootdir")
    chroot("ln -fs /bootdir/boot")
    chroot("mv /bootdir/encryption.key /bootdir/boot/")
    for i in range(disks):
        chroot("mv /bootdir/"+dev_prefix+str(i)+"p3.eli /bootdir/boot/")

    chroot("touch /etc/fstab")
    chroot("touch /etc/rc.conf")
    chroot("touch /bootdir/boot/loader.conf")

    open("rc.conf", "w").write('zfs_enable="YES"')
    put("rc.conf", zroot_mnt+"/etc")
    # os.remove("rc.conf")

    loader = open("loader.conf", "w+")
    for i in ['vfs.zfs.prefetch_disable="1"',
         'vfs.root.mountfrom="zfs:zroot"',
         'zfs_load="YES"',
         'aesni_load="YES"',
         'geom_eli_load="YES"']:
        loader.write(i+"\n")

    for i in range(disks):
        for confstr in [
            'geli_{0}p3_keyfile0_load="YES"'.format(dev_prefix+str(i)),
            'geli_{0}p3_keyfile0_type="{1}p3:geli_keyfile0"'.format(dev_prefix+str(i), dev_prefix+str(i)),
            'geli_{0}p3_keyfile0_name="/boot/encryption.key"'.format(dev_prefix+str(i))]:
            loader.write(confstr+"\n")

    loader.close()
    put("loader.conf", zroot_mnt+"/bootdir/boot")
    # os.remove("loader.conf")

    print("[!] SETTING ROOT PASS")
    chroot('passwd root')

    print("[!] SETTING TIMEZONE")
    chroot('tzsetup')

    # see the article
    chroot('make -C /etc/mail aliases')
    run('cp /boot/zfs/zpool.cache '+zroot_mnt+'/bootdir/boot/zfs')

    # here's why we don't need an fstab:
    run('zfs unmount -a')
    run('zfs set mountpoint=legacy zroot')
    run('zfs set mountpoint=/tmp zroot/tmp')
    run('zfs set mountpoint=/usr zroot/usr')
    run('zfs set mountpoint=/var zroot/var')
    run('zfs set mountpoint=/bootdir bootdir')

    print("[!] REBOOTING")
    run('reboot')


# -------------------
# Full install
# -------------------
def full_install():
    # in order.
    # once again, see the linked blog post:
    with settings(warn_only=True):
        #execute(partition_setup)
        #execute(ram_disk)
        #execute(kernel_mods)
        #execute(loader_partition)
        #execute(key_gen)
        #execute(geli_init)
        #execute(build_root)
        #execute(install_freebsd)
        execute(post_install)
