#!/usr/bin/env python

# Copyright 2011-2014 Biomedical Imaging Group Rotterdam, Departments of
# Medical Informatics and Radiology, Erasmus MC, Rotterdam, The Netherlands
#
# Authors: Mattias Hansson (n.hansson@erasmusmc.nl), Hakim Achterberg
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Training appearance model classifiers for each cross-validation fold
# in multiatlas_app_segmentation_CV.py

import fastr
from sklearn import cross_validation


def main():
 #################################################
 #### PARAMETERS #################################
 #################################################

    # network name
    network_name = 'trainAppearanceModelCV'

    output_appearance_name = 'fastr_voxclass_single_femcart_foldnr'

    output_folder_appearance =  'vfs://fastr_data/seg/class/

    # Scale space scales to extract (in mm)
    scales = (1.0, 1.6, 4.0)
    # Radius for the background sampling mask dilation (mm?)
    radius = [5.0]
    # Number/fraction of sample to sample per images
    # On element per class (class0, class1, etc)
    # If value between [0.0 - 1.0] it is a fraction of the number of samples
    # available in that class
    # If the value is above 1, it is the number of samples to take, if the
    # available number of samples is lower, it will take all samples.
    nsamples = (1000,1000)

    # Note: the parameters for the random forest classifier are in the
    # parameter file supplied as source data

    # number of cross-validation folds
    num_folds = 5
    # starting fold
    foldnr = 1

    # atlas MRIs
    CV_ims = ['image9003406_20060322','image9007827_20051219','image9200458_20051202','image9352437_20050411',
              'image9403165_20060316','image9496443_20050811','image9567704_20050505','image9047800_20060306',
              'image9056363_20051010','image9068453_20060131','image9085290_20051103','image9102858_20060210',
              'image9279291_20051025','image9352883_20051123','image9357137_20051212','image9357383_20050912',
              'image9369649_20060224','image9587749_20050707']

    # atlas label volumes
    CV_label = ['groundtruth9003406_20060322','groundtruth9007827_20051219','groundtruth9200458_20051202','groundtruth9352437_20050411',
                'groundtruth9403165_20060316','groundtruth9496443_20050811','groundtruth9567704_20050505','groundtruth9047800_20060306',
                'groundtruth9056363_20051010','groundtruth9068453_20060131','groundtruth9085290_20051103','groundtruth9102858_20060210',
                'groundtruth9279291_20051025','groundtruth9352883_20051123','groundtruth9357137_20051212','groundtruth9357383_20050912',
                'groundtruth9369649_20060224','groundtruth9587749_20050707']

    cv = cross_validation.KFold(len(CV_ims), n_folds=num_folds, random_state=0)

    sourcedata = {
        'images':  {
            'image9003406_20060322':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9003406_20060322_SAG_3D_DESS_LEFT_016610899303_FemoralCartilage_ims_crop.nii.gz',
            'image9007827_20051219':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9007827_20051219_SAG_3D_DESS_LEFT_016610641606_FemoralCartilage_ims_crop.nii.gz',
            'image9047800_20060306':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9047800_20060306_SAG_3D_DESS_LEFT_016610874403_FemoralCartilage_ims_crop.nii.gz',
            'image9056363_20051010':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9056363_20051010_SAG_3D_DESS_LEFT_016610100103_FemoralCartilage_ims_crop.nii.gz',
            'image9068453_20060131':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9068453_20060131_SAG_3D_DESS_LEFT_016610822403_FemoralCartilage_ims_crop.nii.gz',
            'image9085290_20051103':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9085290_20051103_SAG_3D_DESS_LEFT_016610952703_FemoralCartilage_ims_crop.nii.gz',
            'image9094865_20060209':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9094865_20060209_SAG_3D_DESS_LEFT_016610837203_FemoralCartilage_ims_crop.nii.gz',
            'image9102858_20060210':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9102858_20060210_SAG_3D_DESS_LEFT_016610859602_FemoralCartilage_ims_crop.nii.gz',
            'image9200458_20051202':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9200458_20051202_SAG_3D_DESS_LEFT_016610610903_FemoralCartilage_ims_crop.nii.gz',
            'image9279291_20051025':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9279291_20051025_SAG_3D_DESS_LEFT_016610219303_FemoralCartilage_ims_crop.nii.gz',
            'image9352437_20050411':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9352437_20050411_SAG_3D_DESS_LEFT_016610106806_FemoralCartilage_ims_crop.nii.gz',
            'image9352883_20051123':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9352883_20051123_SAG_3D_DESS_LEFT_016610798103_FemoralCartilage_ims_crop.nii.gz',
            'image9357137_20051212':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9357137_20051212_SAG_3D_DESS_LEFT_016610629903_FemoralCartilage_ims_crop.nii.gz',
            'image9357383_20050912':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9357383_20050912_SAG_3D_DESS_LEFT_016610520402_FemoralCartilage_ims_crop.nii.gz',
            'image9369649_20060224':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9369649_20060224_SAG_3D_DESS_LEFT_016610861903_FemoralCartilage_ims_crop.nii.gz',
            'image9403165_20060316':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9403165_20060316_SAG_3D_DESS_LEFT_016610900302_FemoralCartilage_ims_crop.nii.gz',
            'image9496443_20050811':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9496443_20050811_SAG_3D_DESS_LEFT_016610469823_FemoralCartilage_ims_crop.nii.gz',
            'image9567704_20050505':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9567704_20050505_SAG_3D_DESS_LEFT_016610398706_FemoralCartilage_ims_crop.nii.gz',
            'image9587749_20050707':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9587749_20050707_SAG_3D_DESS_LEFT_016610415806_FemoralCartilage_ims_crop.nii.gz',
            'image9596610_20050909':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_IMS_crop/9596610_20050909_SAG_3D_DESS_LEFT_016610499502_FemoralCartilage_ims_crop.nii.gz',
        },
        'label_images':  {
            'groundtruth9003406_20060322':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20060322_SAG_3D_DESS_LEFT_016610899303_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9007827_20051219':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20051219_SAG_3D_DESS_LEFT_016610641606_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9094865_20060209':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20060209_SAG_3D_DESS_LEFT_016610837203_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9200458_20051202':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20051202_SAG_3D_DESS_LEFT_016610610903_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9352437_20050411':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20050411_SAG_3D_DESS_LEFT_016610106806_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9403165_20060316':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20060316_SAG_3D_DESS_LEFT_016610900302_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9496443_20050811':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20050811_SAG_3D_DESS_LEFT_016610469823_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9567704_20050505':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20050505_SAG_3D_DESS_LEFT_016610398706_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9047800_20060306':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20060306_SAG_3D_DESS_LEFT_016610874403_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9056363_20051010':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20051010_SAG_3D_DESS_LEFT_016610100103_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9068453_20060131':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20060131_SAG_3D_DESS_LEFT_016610822403_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9085290_20051103':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20051103_SAG_3D_DESS_LEFT_016610952703_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9102858_20060210':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20060210_SAG_3D_DESS_LEFT_016610859602_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9279291_20051025':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20051025_SAG_3D_DESS_LEFT_016610219303_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9352883_20051123':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20051123_SAG_3D_DESS_LEFT_016610798103_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9357137_20051212':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20051212_SAG_3D_DESS_LEFT_016610629903_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9357383_20050912':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20050912_SAG_3D_DESS_LEFT_016610520402_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9369649_20060224':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20060224_SAG_3D_DESS_LEFT_016610861903_FemoralCartilage_GT_crop.nii.gz',
            'groundtruth9587749_20050707':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/cropped_data/20050707_SAG_3D_DESS_LEFT_016610415806_FemoralCartilage_GT_crop.nii.gz'
        },
        'param_file':     ['vfs://fastr_data/seg/param/param_single.ini']
    }

#############################################################################
##################END PARAMETERS
#############################################################################

# cross-validation
    for train_indices,test_indices in cv:
        sourcedata_fold = {}
        sourcedata_fold['images'] = {}
        sourcedata_fold['label_images'] = {}
        sourcedata_fold['param_file'] = sourcedata['param_file']

        for ii in train_indices:
            sourcedata_fold['images'][CV_ims[ii]] = sourcedata['images'][CV_ims[ii]]
            sourcedata_fold['label_images'][CV_label[ii]] = sourcedata['label_images'][CV_label[ii]]

        #instantiate network
        network = fastr.Network(id_=network_name)
        
        #load MRI volumes 
        source_t1 = network.create_source('NiftiImageFileCompressed', id_='images', sourcegroup='atlas')
        #load label volumes
        source_label = network.create_source('NiftiImageFileCompressed', id_='label_images', sourcegroup='atlas')
        # load configuration file for appearance model
        source_param = network.create_source('ConfigFile', id_='param_file')

        # Create filter image for source data
        scalespacefilter = network.create_node('GaussianScaleSpace', id_='scalespacefilter', memory='15G')
        scalespacefilter.inputs['image'] = source_t1.output
        scalespacefilter.inputs['scales'] = scales

        # Prepare mask
        threshold = network.create_node('PxThresholdImage', id_='threshold', memory='15G')
        morph = network.create_node('PxMorphology', id_='morph', memory='15G')

        # threshold mask at 0.5        
        threshold.inputs['image'] = source_label.output
        threshold.inputs['upper_threshold'] = [0.5]

        # dilate mask
        morph.inputs['image'] = threshold.outputs['image']
        morph.inputs['operation'] = ['dilation']
        morph.inputs['operation_type'] = ['binary']
        morph.inputs['radius'] = radius

        # Sample the feature images
        sampler = network.create_node('SampleImage', id_='sampler', memory='15G')
        sampler.inputs['image'] = scalespacefilter.outputs['image']
        sampler.inputs['labels'] = source_label.output
        sampler.inputs['mask'] = morph.outputs['image']
        sampler.inputs['nsamples'] = nsamples

        # Train the classifier, use 8 cores in parallel
        classifier = network.create_node('RandomForestTrain', id_='classifier', memory='15G', cores=8)
        link = network.create_link(sampler.outputs['sample_file'], classifier.inputs['samples'])
        link.collapse = 0
        classifier.inputs['parameters'] = source_param.output
        classifier.inputs['number_of_cores'] = (8,)

        # Create sink
        out_classifier = network.create_sink('SKLearnClassifierFile', id_='out_classifier')
        out_classifier.input = classifier.outputs['classifier']

        # location of sink files
        sinkdata = {'out_classifier': output_folder_appearance + output_appearance_name +
                                      str(foldnr) + '_{sample_id}{ext}'}

        # print network
        print network.draw_network(img_format='svg', draw_dimension=True)
        fastr.log.info('^^^^^^^^^^^^^ Starting execution client.')
        # execute appearance model training
        network.execute(sourcedata_fold, sinkdata)
        foldnr = foldnr + 1

if __name__ == '__main__':
    main()

