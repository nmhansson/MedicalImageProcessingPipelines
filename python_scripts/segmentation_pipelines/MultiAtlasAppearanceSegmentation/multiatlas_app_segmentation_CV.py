#!/usr/bin/env python

# Copyright 2011-2014 Biomedical Imaging Group Rotterdam, Departments of
# Medical Informatics and Radiology, Erasmus MC, Rotterdam, The Netherlands
#
# Authors: Mattias Hansson (n.hansson@erasmusmc.nl), Hakim Achterberg
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

# Cross-validate a multi-atlas appearance segmentation algorithm.
# This script uses appearance models trained in train_appearance_model_CV.py

import fastr
from sklearn import cross_validation

def main() :
    #################################################
    #### PARAMETERS #################################
    #################################################

    # network name
    network_name = 'multiatlas_femur_segm_CV'

    output_segm_name = 'segm_woapp_hip_foldnr'

    output_eval_meas_name = 'dice_woapp_hip_foldnr'

    # output folder segmentations
    output_segm_folder = 'vfs://fastr_data/hipdata/output/'

    # output folder evaluation measure
    output_eval_meas_folder = 'vfs://fastr_data/hipdata/output/'

    # number of cross-validation folds
    num_folds = 5
    # starting fold
    foldnr = 1

    nrclasses = 2
    # radius for dilation mask
    radius = [5.0]

   # registration parameter files
    registration_parameters = ('vfs://elastix_files/par_affine_multi.txt', 'vfs://elastix_files/par_bspline5mm_multi.txt')
    registration_parameters_generate_mask = ('vfs://elastix_file/par_similarity.txt',)

    # MRI volume names
    CV_img =    ['imageR112621fw', 'imageR112629fw','imageR112657fw','imageR113297fw',
                 'imageR115510fw','imageR118132fw','imageR118663fw','imageR118972fw',
                 'imageR119833fw','imageR119927fw','imageR128348fw','imageR129317fw',
                 'imageR129358fw','imageR131044fw','imageR131489fw','imageR131717fw',
                 'imageR132132fw']

    # label volume names
    CV_label =  [ 'maskR112621','maskR112629','maskR112657','maskR113297',
                  'maskR115510','maskR118132','maskR118663','maskR118972',
                  'maskR119833','maskR119927','maskR128348','maskR129317',
                  'maskR129358','maskR131044','maskR131489','maskR131717',
                  'maskR132132']

    # Region of interest volume
    CV_ROI =    ['ROI112621','ROI112629','ROI112657','ROI113297',
                 'ROI115510','ROI118132','ROI118663','ROI118972',
                 'ROI119833','ROI119927','ROI128348','ROI129317',
                 'ROI129358','ROI131044','ROI131489','ROI131717',
                 'ROI132132']
    


    cv=cross_validation.KFold(len(CV_img),n_folds=num_folds,random_state=0)

    # sourcedata dictionary contains path of all data volumes as well as path of
    # appearance model classifier : 'classifier'
    sourcedata = {
      'scalespace_img':   {
            'imageR112621fw':('vfs://fastr_data/hipdata/images/R112621f.nii.gz',),#1
            'imageR112629fw':('vfs://fastr_data/hipdata/images/R112629f.nii.gz',),#2
            'imageR112657fw':('vfs://fastr_data/hipdata/images/R112657f.nii.gz',),#3
            'imageR113297fw':('vfs://fastr_data/hipdata/images/R113297f.nii.gz',),#4
            'imageR115510fw':('vfs://fastr_data/hipdata/images/R115510f.nii.gz',),#5
            'imageR118132fw':('vfs://fastr_data/hipdata/images/R118132f.nii.gz',),#6
            'imageR118663fw':('vfs://fastr_data/hipdata/images/R118663f.nii.gz',),#7
            'imageR118972fw':('vfs://fastr_data/hipdata/images/R118972f.nii.gz',),#8
            'imageR119833fw':('vfs://fastr_data/hipdata/images/R119833f.nii.gz',),#9
            'imageR119927fw':('vfs://fastr_data/hipdata/images/R119927f.nii.gz',),#10
            'imageR128348fw':('vfs://fastr_data/hipdata/images/R128348f.nii.gz',),#11
            'imageR129317fw':('vfs://fastr_data/hipdata/images/R129317f.nii.gz',),#12
            'imageR129358fw':('vfs://fastr_data/hipdata/images/R129358f.nii.gz',),#13
            'imageR131044fw':('vfs://fastr_data/hipdata/images/R131044f.nii.gz',),#14
            'imageR131489fw':('vfs://fastr_data/hipdata/images/R131489f.nii.gz',),#15
            'imageR131717fw':('vfs://fastr_data/hipdata/images/R131717f.nii.gz',),#16
            'imageR132132fw':('vfs://fastr_data/hipdata/images/R132132f.nii.gz',),#17
        }, 
        'atlas_img':   {
            'imageR112621fw':('vfs://fastr_data/hipdata/images/R112621f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R112621w.nii.gz'),#1
            'imageR112629fw':('vfs://fastr_data/hipdata/images/R112629f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R112629w.nii.gz'),#2
            'imageR112657fw':('vfs://fastr_data/hipdata/images/R112657f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R112657w.nii.gz'),#3
            'imageR113297fw':('vfs://fastr_data/hipdata/images/R113297f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R113297w.nii.gz'),#4
            'imageR115510fw':('vfs://fastr_data/hipdata/images/R115510f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R115510w.nii.gz'),#5
            'imageR118132fw':('vfs://fastr_data/hipdata/images/R118132f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R118132w.nii.gz'),#6
            'imageR118663fw':('vfs://fastr_data/hipdata/images/R118663f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R118663w.nii.gz'),#7
            'imageR118972fw':('vfs://fastr_data/hipdata/images/R118972f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R118972w.nii.gz'),#8
            'imageR119833fw':('vfs://fastr_data/hipdata/images/R119833f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R119833w.nii.gz'),#9
            'imageR119927fw':('vfs://fastr_data/hipdata/images/R119927f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R119927w.nii.gz'),#10
            'imageR128348fw':('vfs://fastr_data/hipdata/images/R128348f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R128348f.nii.gz'),#11
            'imageR129317fw':('vfs://fastr_data/hipdata/images/R129317f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R129317w.nii.gz'),#12
            'imageR129358fw':('vfs://fastr_data/hipdata/images/R129358f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R129358w.nii.gz'),#13
            'imageR131044fw':('vfs://fastr_data/hipdata/images/R131044f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R131044w.nii.gz'),#14
            'imageR131489fw':('vfs://fastr_data/hipdata/images/R131489f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R131489w.nii.gz'),#15
            'imageR131717fw':('vfs://fastr_data/hipdata/images/R131717f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R131717w.nii.gz'),#16
            'imageR132132fw':('vfs://fastr_data/hipdata/images/R132132f.nii.gz',
                              'vfs://fastr_data/hipdata/images/R132132w.nii.gz')#17
        },
        'atlas_labels':  {
            'maskR112621':('vfs://fastr_data/hipdata/hip_masks/R112621.nii.gz',),#1
            'maskR112629':('vfs://fastr_data/hipdata/hip_masks/R112629.nii.gz',),#2
            'maskR112657':('vfs://fastr_data/hipdata/hip_masks/R112657.nii.gz',),#3
            'maskR113297':('vfs://fastr_data/hipdata/hip_masks/R113297.nii.gz',),#4
            'maskR115510':('vfs://fastr_data/hipdata/hip_masks/R115510.nii.gz',),#5
            'maskR118132':('vfs://fastr_data/hipdata/hip_masks/R118132.nii.gz',),#6
            'maskR118663':('vfs://fastr_data/hipdata/hip_masks/R118663.nii.gz',),#7
            'maskR118972':('vfs://fastr_data/hipdata/hip_masks/R118972.nii.gz',),#8
            'maskR119833':('vfs://fastr_data/hipdata/hip_masks/R119833.nii.gz',),#9
            'maskR119927':('vfs://fastr_data/hipdata/hip_masks/R119927.nii.gz',),#10
            'maskR128348':('vfs://fastr_data/hipdata/hip_masks/R128348.nii.gz',),#11
            'maskR129317':('vfs://fastr_data/hipdata/hip_masks/R129317.nii.gz',),#12
            'maskR129358':('vfs://fastr_data/hipdata/hip_masks/R129358.nii.gz',),#13
            'maskR131044':('vfs://fastr_data/hipdata/hip_masks/R131044.nii.gz',),#14
            'maskR131489':('vfs://fastr_data/hipdata/hip_masks/R131489.nii.gz',),#15
            'maskR131717':('vfs://fastr_data/hipdata/hip_masks/R131717.nii.gz',),#16
            'maskR132132':('vfs://fastr_data/hipdata/hip_masks/R132132.nii.gz',),#17
        },
        'atlas_ROI':{
            'ROI112621':('vfs://fastr_data/hipdata/ROI/R112621w.nii.gz',),#1
            'ROI112629':('vfs://fastr_data/hipdata/ROI/R112629w.nii.gz',),#2
            'ROI112657':('vfs://fastr_data/hipdata/ROI/R112657w.nii.gz',),#3
            'ROI113297':('vfs://fastr_data/hipdata/ROI/R113297w.nii.gz',),#4
            'ROI115510':('vfs://fastr_data/hipdata/ROI/R115510w.nii.gz',),#5
            'ROI118132':('vfs://fastr_data/hipdata/ROI/R118132w.nii.gz',),#6
            'ROI118663':('vfs://fastr_data/hipdata/ROI/R118663w.nii.gz',),#7
            'ROI118972':('vfs://fastr_data/hipdata/ROI/R118972w.nii.gz',),#8
            'ROI119833':('vfs://fastr_data/hipdata/ROI/R119833w.nii.gz',),#9
            'ROI119927':('vfs://fastr_data/hipdata/ROI/R119927w.nii.gz',),#10
            'ROI128348':('vfs://fastr_data/hipdata/ROI/R128348w.nii.gz',),#11
            'ROI129317':('vfs://fastr_data/hipdata/ROI/R129317w.nii.gz',),#12
            'ROI129358':('vfs://fastr_data/hipdata/ROI/R129358w.nii.gz',),#13
            'ROI131044':('vfs://fastr_data/hipdata/ROI/R131044w.nii.gz',),#14
            'ROI131489':('vfs://fastr_data/hipdata/ROI/R131489w.nii.gz',),#15
            'ROI131717':('vfs://fastr_data/hipdata/ROI/R131717w.nii.gz',),#16
            'ROI132132':('vfs://fastr_data/hipdata/ROI/R132132w.nii.gz',),#17
        }
    }
    #############################################################################
    ##################END PARAMETERS
    #############################################################################

# Start cross-validation
    while foldnr <= num_folds:
        for train_indices,test_indices in cv:
            sourcedata_fold= {}
            sourcedata_fold['atlas_img']= {}
            sourcedata_fold['atlas_labels']= {}
            sourcedata_fold['atlas_ROI']= {}
            sourcedata_fold['target_img']= {}
            sourcedata_fold['target_labels']= {}

        for ii in train_indices :
            sourcedata_fold['atlas_img'][CV_img[ii]]=sourcedata['atlas_img'][CV_img[ii]]
            sourcedata_fold['atlas_labels'][CV_label[ii]]=sourcedata['atlas_labels'][CV_label[ii]]
            sourcedata_fold['atlas_ROI'][CV_ROI[ii]]=sourcedata['atlas_ROI'][CV_ROI[ii]]

        for kk in test_indices:
            sourcedata_fold['target_img'][CV_img[kk]]=sourcedata['atlas_img'][CV_img[kk]]
            sourcedata_fold['target_labels'][CV_label[kk]]=sourcedata['atlas_labels'][CV_label[kk]]

        # Setup Network and sources
        network = fastr.Network(id_=network_name)

        # load MRI target volumes
        source_targetImages = network.create_source('NiftiImageFileCompressed', id_='target_img',nodegroup='target')
        source_targetlabel =  network.create_source('NiftiImageFileCompressed', id_='target_labels',nodegroup='target')

        # load MRI atlas volumes
        source_atlasImages = network.create_source('NiftiImageFileCompressed', id_='atlas_img', nodegroup='atlas')
        source_atlasLabels = network.create_source('NiftiImageFileCompressed', id_='atlas_labels', nodegroup='atlas')
        source_atlasROI = network.create_source(datatype=fastr.typelist['ITKImageFile'], id_='atlas_ROI',nodegroup='atlas')

        ###########################################################################################################
        #Generate target ROI using multi-atlas similarity transform
        ###########################################################################################################

        reg_genmask = network.create_node(fastr.toollist['Elastix','4.8'], id_='reg_genmask', memory='10G')
        reg_genmask.inputs['fixed_image'] = source_targetImages.output
        reg_genmask.inputs['moving_image'] = source_atlasImages.output
        reg_genmask.inputs['moving_image'].input_group = 'atlas'
        reg_genmask.inputs['parameters'] = registration_parameters_generate_mask

        # transform target ROI according to parameters estimated by elastix
        trans_label_genmask = network.create_node('Transformix', id_='trans_label_genmask', memory='6G')
        link_trans_label_genmask = trans_label_genmask.inputs['image'] << source_atlasROI.output
        trans_label_genmask.inputs['transform'] = reg_genmask.outputs['transform'][-1]

        # combine transformed target ROI - produces hard label decided by majority vote or soft label given as probability
        combine_label_genmask = network.create_node('PxCombineSegmentations', id_='combine_label_genmask')
        link_combine_genmask = network.create_link(trans_label_genmask.outputs['image'], combine_label_genmask.inputs['images'])
        link_combine_genmask.collapse = 'atlas'
        combine_label_genmask.inputs['method'] = ['VOTE']
        combine_label_genmask.inputs['number_of_classes'] = [nrclasses]

        # probability values greater than 0.5 are thresholded to 1, others 0.
        threshold = network.create_node('PxThresholdImage', id_='threshold', memory='2G')
        threshold.inputs['image'] = combine_label_genmask.outputs['soft_segment'][-1]
        threshold.inputs['upper_threshold'] = [0.5]

        # convert to char datatype (this is required for itktools, node starting with 'Px')
        castconvert = network.create_node('PxCastConvert', id_='castconvert', memory='2G')
        castconvert.inputs['image'] = threshold.outputs['image']
        castconvert.inputs['component_type'] = ['char']

        # morphological operation: dilation
        morph = network.create_node('PxMorphology', id_='morph', memory='5G')
        morph.inputs['image'] = castconvert.outputs['image']
        morph.inputs['operation'] = ['dilation']
        morph.inputs['operation_type'] = ['binary']
        morph.inputs['radius'] = radius

        #############################################################################
        # Apply image processing operations to MRI volumes
        ############################################################################

        # Apply n4 non-uniformity correction to MRI atlas volumes
        n4_atlas_im = network.create_node('N4', id_='n4_atlas', memory='15G')
        linkn4atlas  = n4_atlas_im.inputs['image'] << source_atlasImages.output
        linkn4atlas.expand = True
        n4_atlas_im.inputs['shrink_factor'] = 4,
        n4_atlas_im.inputs['converge'] = '[150,00001]',
        n4_atlas_im.inputs['bspline_fitting'] = '[50]',

        # Apply n4 non-uniformity correction to MRI target volumes
        n4_target_im = network.create_node('N4', id_='n4_target', memory='15G')
        linkn4target = n4_target_im.inputs['image'] << source_targetImages.output
        linkn4target.expand = True
        n4_target_im.inputs['shrink_factor'] = 4,
        n4_target_im.inputs['converge'] = '[150,00001]',
        n4_target_im.inputs['bspline_fitting'] = '[50]',

        # Range match MRI atlas images
        rama_atlas_im = network.create_node('RangeMatch', id_='rama_atlas',memory='15G')
        rama_atlas_im.inputs['image'] = n4_atlas_im.outputs['image']
        link_rama_mask_atlas = rama_atlas_im.inputs['mask'] << source_atlasROI.output

        # Range match MRI target images
        rama_target_im = network.create_node('RangeMatch', id_='rama_target',memory='15G')
        rama_target_im.inputs['image'] = n4_target_im.outputs['image']
        link_rama_mask_target = rama_target_im.inputs['mask'] << morph.outputs['image']

        ################################
        # Multi-atlas segmentation part
        ################################

        # perform registration with elastix
        reg_t1 = network.create_node(fastr.toollist['Elastix','4.8'], id_='reg_t1', memory='20G')
        link1 = reg_t1.inputs['fixed_image'] << rama_target_im.outputs['image']
        link1.collapse = "target_img__output"
        link2 = reg_t1.inputs['moving_image'] << rama_atlas_im.outputs['image']
        link2.collapse = "atlas_img__output"

        reg_t1.inputs['moving_image'].input_group = 'atlas'
        reg_t1.inputs['parameters'] = registration_parameters
        reg_t1.inputs['fixed_mask'] = (morph.outputs['image'],morph.outputs['image'])
        reg_t1.inputs['moving_mask'] = source_atlasROI.output
        reg_t1.inputs['moving_mask'].input_group = 'atlas'

        # transform masks according to registration results
        trans_label = network.create_node('Transformix', id_='trans_label')
        linktrans = trans_label.inputs['image'] << source_atlasLabels.output
        trans_label.inputs['transform'] = reg_t1.outputs['transform'][-1]

        # combine registered masks
        combine_label = network.create_node('PxCombineSegmentations', id_='combine_label')
        link_combine = network.create_link(trans_label.outputs['image'], combine_label.inputs['images'])
        link_combine.collapse = 'atlas'
        combine_label.inputs['method'] = ['VOTE']
        combine_label.inputs['number_of_classes'] = [nrclasses] 

        # Create sink for segmentation
        out_seg = network.create_sink('NiftiImageFileCompressed', id_='out_seg')
        #out_seg.input = argmax.outputs['image']
        out_seg.input = combine_label.outputs['hard_segment']

        # dice overlap
        dice_node = network.create_node(fastr.toollist['DiceMultilabelIms'],id_='dice_multi')
        #dice_node.inputs['image1'] = argmax.outputs['image']
        dice_node.inputs['image1'] = combine_label.outputs['hard_segment']
        dice_node.inputs['image2'] = source_targetlabel.output
        dice_node.inputs['numlabels'] = 1,

        # Create sink for dice overlap score
        outnumber = network.create_sink(datatype=fastr.typelist['Float'],id_='sink_measure')
        link = network.create_link(dice_node.outputs['output'],outnumber.input)
        link.collapse = 'target'

        # location of sink files
        sinkdata = {'out_seg': output_segm_folder + output_segm_name + str(foldnr) + '_{sample_id}{ext}',
                    'sink_measure': output_eval_meas_folder + output_eval_meas_name +
                                    str(foldnr) + '_{sample_id}_{cardinality}{ext}'}


        # print network
        print network.draw_network(img_format='svg', draw_dimension=True)
        fastr.log.info('^^^^^^^^^^^^^ Starting execution client.')

        # execute multi-atlas appearance segmentation
        network.execute(sourcedata_fold, sinkdata, cluster_queue="week")

        foldnr = foldnr + 1

if __name__ == '__main__':
    main()



