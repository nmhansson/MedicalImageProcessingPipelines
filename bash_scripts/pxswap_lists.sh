#!/bin/bash

# Reflect pixel values in scan in y-axis

while read f1 <&7
do
      pxreflect -in $f1 -out ${f1%.nii.gz}_pxswap.nii.gz -d 0 
                                                                                     
done \
    7<$1 
