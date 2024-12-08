#!/bin/bash

tmpfile=$(mktemp -d) || exit 1
script=$(ls -1 *.py | sed -n '1s/\.py//p')
cp $script.py $tmpfile/__main__.py
python3 -m pip install -r requirements.txt --target $tmpfile
python3 -m zipapp --python "/usr/bin/env python3" --output $script.pyz $tmpfile
rm -r $tmpfile

sed -n '1,/^base64/p' post-bootstrap.skel > post-bootstrap
gzip -c9 $script.pyz | base64 >> post-bootstrap
echo EOF >> post-bootstrap
