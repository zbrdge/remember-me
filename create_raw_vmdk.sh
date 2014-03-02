#!/bin/sh

# I can never remember this particular command for VirtualBox:

VBoxManage internalcommands createrawvmdk -filename "$1" -rawdisk "$2"
