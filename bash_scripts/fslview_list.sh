#!/bin/bash

# displays file with fslview iteratively on each item in list

while read f1 <&7
do
    echo $f1    
    fslview $f1 
done \
    7<$1 
