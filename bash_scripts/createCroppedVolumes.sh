#!/usr/bin/env bash

# Create cropped versions of images and GT images according to boundingbox of GT image

impath="/scratch/mhansson/data/OAI_nifti/Nifti_IMS/"
file_extension="nii.gz"

gtpath="/scratch/mhansson/data/OAI_nifti/Nifti_FemoralCartilage_GT/"
gtfile_suffix="FemoralCartilage_GT"

cropGTpath="/scratch/mhansson/data/OAI_nifti/Nifti_FemoralCartilage_GT_crop/"
cropIMpath="/scratch/mhansson/data/OAI_nifti/Nifti_IMS_crop/"

# images in impath folder have suffix "ims"
# images in gtpath folder hacve suffix ${gtfile_suffix} 

#read -p "<path to image>:" impath
#read -p "<path to GT>:" gtpath
#read -p "<cropped GT dest path>:" cropGTpath
#read -p "<cropped image dest path>:" cropIMpath

for filename_fullpath in $gtpath*.${file_extension}
    do  
        filename="$(echo ${filename_fullpath} | tr '/' '\n' | tail -1)"
        list="$(pxcomputeboundingbox -in ${filename_fullpath} | sed -e 's/[^0-9 ]//g')" 
        min_xcoord="$(echo ${list} |cut -d " " -f1)"
        min_ycoord="$(echo ${list} |cut -d " " -f2)"
        max_xcoord="$(echo ${list} |cut -d " " -f4)" 
        max_ycoord="$(echo ${list} |cut -d " " -f5)"
        range_x="$(echo `expr ${max_xcoord} - ${min_xcoord} + 1`)"
        range_y="$(echo `expr ${max_ycoord} - ${min_ycoord} + 1`)"
         
         
    fslmaths ${gtpath}${filename} -roi ${min_xcoord} ${range_x} ${min_ycoord} ${range_y} 0 -1 0 1 ${cropGTpath}${filename%.${file_extension}}_crop.${file_extension}
    fslmaths ${impath}${filename%${gtfile_suffix}.${file_extension}}ims.${file_extension} -roi ${min_xcoord} ${range_x} ${min_ycoord} ${range_y} 0 -1 0 1 ${cropIMpath}${filename%${gtfile_suffix}.${file_extension}}ims_crop.${file_extension}          
    done
