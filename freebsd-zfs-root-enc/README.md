FreeBSD encrypted root install on ZFS, via Fabric
------------------
Adapted from:
------------------
   https://www.dan.me.uk/blog/2012/05/06/full-disk-encryption-with-zfs-root-for-freebsd-9-x/

Software versions:
------------------
    Python 2.7.5
    pip 1.4.1
    Fabric 1.8.0
    Paramiko 1.12.0

Invocation: (call it task by task if you like)
----------------------------------------------
    $ fab -I -k -f freebsd-zfs-fabfile.py -u root -H {HOST} full_install

!!! NOTE !!! I had to use the '-I' and then just hit 'enter' when prompted for env.password,
    in order to use an empty password. Seems like a bug...

SSHD Notes
------------
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
