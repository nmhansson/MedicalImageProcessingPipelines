#!/bin/bash

#Copies geometry header info from first entry list 1 to first entry list 2, 
#etc.

while read f1 <&7
do
        read f2 <&8
        echo fslcpgeom $f1 $f2
        fslcpgeom $f1 $f2
done \
    7<$1 \
    8<$2
