#!/bin/bash
# Current as of sumneko version 3.6.0
OUT_DIR=${LSP_DIR}/lua/sumneko
FORCE_REINSTALL=1

do_install() {
    if [ $FORCE_REINSTALL ]; then
        echo "Clearing out previous installation in ${OUT_DIR}"
        rm -rf $OUT_DIR
    fi
    if [ -d $OUT_DIR ]; then
        echo "${OUT_DIR} already exists. Force reinstall?"
        exit 1;
    fi
    apk add --update --no-cache ninja g++
    git clone --depth=1 https://github.com/sumneko/lua-language-server $OUT_DIR
    cd $OUT_DIR
    git submodule update --depth=1 --init --recursive
    cd $OUT_DIR/3rd/luamake
    ./compile/install.sh
    cd $OUT_DIR
    ./3rd/luamake/luamake rebuild
    rm -rf $OUT_DIR/3rd $OUT_DIR/log $OUT_DIR/doc $OUT_DIR/test* $OUT_DIR/build $OUT_DIR/theme_tokens.md $OUT_DIR/make* $OUT_DIR/*.tar.gz $OUT_DIR/tools
    exit 0;
}

while getopts "y" flag; do
    case $flag in
        y)
            FORCE_REINSTALL=0
            ;;
    esac
done

do_install
