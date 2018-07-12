#!/bin/bash

# display geometric information for each entry in 2 lists 

while read f1 <&7
do
        read f2 <&8
        pxgetimageinformation -in $f1 -all
        pxgetimageinformation -in $f2 -all
        echo '-----------------------------------'
done \
    7<$1 \
    8<$2 \
