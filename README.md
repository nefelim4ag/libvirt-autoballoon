# libvirt-autoballoon
libvirt-autoballoon: daemon to autoballoon guest memory by virsh on host with libvirt

That script just detect all running libvirt-qemu guests on localhost  
and try balloon unused memory from guests to host

Proof of concept

# Installation

```
~# make install
~# systemctl enable libvirt-autoballoon
~# systemctl start libvirt-autoballoon
```
