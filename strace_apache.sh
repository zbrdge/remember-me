#!/bin/sh

strace $* $(pidof nginx |sed 's/\([0-9]*\)/\-p \1/g')
