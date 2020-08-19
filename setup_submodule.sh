#!/bin/bash
#
# Just init,update and install the pywikibot submodule

git submodule init
git submodule update
pip3 install --editable pywikibot
