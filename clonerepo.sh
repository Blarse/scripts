#!/bin/sh

HOST=http://git.altlinux.org
PKG=$1; shift

#clone git repo for selected package
[ -z $PKG ] && echo "Usage: $0 <package>" && exit 1

PKG=${PKG%.git}

if [ -d "./$PKG" ]; then
	echo "Package is already cloned"
	exit 0
fi

PKG_PATH="$HOST/gears/${PKG::1}/$PKG.git"
if git clone $PKG_PATH; then
	echo "DONE"
else
	echo "FAIL"
    PKG_PATH="$HOST/srpms/${PKG::1}/$PKG.git"
    if git clone $PKG_PATH; then
	    echo "DONE"
    else
	    echo "FAIL"
        exit 1
    fi
fi
