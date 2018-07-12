#!/bin/bash

#Take list of files and report qform and sform 

while read f1 <&7
do
        fslhd $f1 | grep "qform_xorient"
        fslhd $f1 | grep "qform_yorient"
        fslhd $f1 | grep "qform_zorient"
        fslhd $f1 | grep "sform_xorient"
        fslhd $f1 | grep "sform_yorient"
        fslhd $f1 | grep "sform_zorient"
        echo "----------------------" 
done \
    7<$1 
