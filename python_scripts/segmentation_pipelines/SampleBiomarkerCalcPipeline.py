#!/usr/bin/env python

# Copyright 2011-2017 Biomedical Imaging Group Rotterdam, Departments of
# Medical Informatics and Radiology, Erasmus MC, Rotterdam, The Netherlands
#
# Author: Mattias Hansson (n.hansson@erasmusmc.nl), Hakim Achterberg
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

# Multi-atlas appearance segmentation of knee-MRI data using ROI masks. 

import fastr
import time
from itertools import *
import os
import shutil

def create_network:

    # Scales for the guassian scale space filtering
    scales = (1.0, 1.6, 4.)
    # Number of classes in the segmentation problem
    nrclasses = 2
    radius = [30.0]
    # Regristration parameter files to use
    registration_parameters = ('vfs://fastr_data/tissue_segmentation/constant/par_affine.txt', 'vfs://fastr_data/tissue_segmentation/constant/par_bspline5mm.txt')

    registration_parameters_generate_mask = ('vfs://fastr_data/constant/par_similarity.txt',)

    staging_dir = '/scratch/mhansson/staging/testdir_R_T0_2'
    
    # remove staging directory if it already exists
    try:
        shutil.rmtree(staging_dir)
    except:
        pass
    
    network = fastr.Network(id_="PROOF_XNAT_VolumeCalc_R_T0")
    
    # sort session ids
    session_id_keys = sorted(sourcedata['session_ids'].keys())

    # start at scan number numK 
    numK = 0
    # sizePart = number of scans processed per round
    sizePart = 10

    while numK < len(sourcedata['target_dicom']):

        sourcedata_part = {}
        sourcedata_part['atlas_img'] = sourcedata['atlas_img']
        sourcedata_part['atlas_labels'] = sourcedata['atlas_labels']
        sourcedata_part['atlas_ROI'] = sourcedata['atlas_ROI']
        sourcedata_part['range_mask_target'] = sourcedata['range_mask_target']
        sourcedata_part['range_mask_atlas'] = sourcedata['range_mask_atlas']
        sourcedata_part['classifier'] = sourcedata['classifier']
        sourcedata_part['atlas_img_genmask'] = sourcedata['atlas_img_genmask']
        sourcedata_part['atlas_labels_genmask'] = sourcedata['atlas_labels_genmask']

        sourcedata_part['session_ids'] = {}
        sourcedata_part['target_dicom'] = {}

        for i in islice(count(), numK, numK+sizePart):
            try:
                sourcedata_part['target_dicom'][session_id_keys[i]] = sourcedata['target_dicom'][session_id_keys[i]]
                sourcedata_part['session_ids'][session_id_keys[i]] = sourcedata['session_ids'][session_id_keys[i]]
            except:
                pass

        
        target_dicom = network.create_source('DicomImageFile', id_='target_dicom')
        target_nii = network.create_node(('PxCastConvertDicom', '0.3.0'), id_='target_nii')
        target_nii.inputs['dicom_image'] = target_dicom.output
        session_id = network.create_source('String',id_='session_ids')

        source_atlasImages = network.create_source('NiftiImageFileCompressed', id_='atlas_img', sourcegroup='atlas')
        source_atlasLabels = network.create_source('NiftiImageFileCompressed', id_='atlas_labels', sourcegroup='atlas')
        source_atlasROI = network.create_source(datatype=fastr.typelist['ITKImageFile'], id_='atlas_ROI',sourcegroup='atlas')

        source_rangemask_target = network.create_source('NiftiImageFileCompressed', id_='range_mask_target')
        source_rangemask_atlas = network.create_source('NiftiImageFileCompressed', id_='range_mask_atlas')
        
        source_atlasGenMaskImages = network.create_source('NiftiImageFileCompressed', id_='atlas_img_genmask', sourcegroup='atlasgenmask')
        source_atlasGenMaskLabels = network.create_source('NiftiImageFileCompressed', id_='atlas_labels_genmask', sourcegroup='atlasgenmask')

        classifier = network.create_source('SKLearnClassifierFile', id_='classifier')

        #   Generate target ROI using multi-atlas similarity transform
        reg_genmask = network.create_node(fastr.toollist['Elastix','4.8'], id_='reg_genmask', memory='5G')
        reg_genmask.inputs['fixed_image'] = target_nii.outputs['image']
        reg_genmask.inputs['moving_image'] = source_atlasGenMaskImages.output
        :reg_genmask.inputs['moving_image'].input_group = 'atlasgenmask'
        reg_genmask.inputs['parameters'] = registration_parameters_generate_mask

        trans_label_genmask = network.create_node('Transformix', id_='trans_label_genmask')
        trans_label_genmask.inputs['image'] = source_atlasGenMaskLabels.output
        trans_label_genmask.inputs['transform'] = reg_genmask.outputs['transform'][-1]

        combine_label_genmask = network.create_node('PxCombineSegmentations', id_='combine_label_genmask')
        link_combine_genmask = network.create_link(trans_label_genmask.outputs['image'], combine_label_genmask.inputs['images'])
        link_combine_genmask.collapse = 'atlasgenmask'
        combine_label_genmask.inputs['method'] = ['VOTE']
        combine_label_genmask.inputs['number_of_classes'] = [nrclasses]
 
        threshold = network.create_node('PxThresholdImage', id_='threshold', memory='2G')
        threshold.inputs['image'] = combine_label_genmask.outputs['soft_segment'][-1]
        threshold.inputs['upper_threshold'] = [0]
 
        castconvert = network.create_node('PxCastConvert', id_='castconvert', memory='2G')
        castconvert.inputs['image'] = threshold.outputs['image']
        castconvert.inputs['component_type'] = ['char']
 
        morph = network.create_node('PxMorphology', id_='morph', memory='2G')
        morph.inputs['image'] = castconvert.outputs['image']
        morph.inputs['operation'] = ['dilation']
        morph.inputs['operation_type'] = ['binary']
        morph.inputs['radius'] = radius
 
        # Apply n4 non-uniformity correction
        n4_atlas_im = network.create_node('N4', id_='n4_atlas', memory='8G')
        n4_atlas_im.inputs['image'] = source_atlasImages.output
        n4_atlas_im.inputs['shrink_factor'] = 4,
        n4_atlas_im.inputs['converge'] = '[150,00001]',
        n4_atlas_im.inputs['bspline_fitting'] = '[50]',

        n4_target_im = network.create_node('N4', id_='n4_target', memory='8G')
        n4_target_im.inputs['image'] = target_nii.outputs['image']
        n4_target_im.inputs['shrink_factor'] = 4,
        n4_target_im.inputs['converge'] = '[150,00001]',
        n4_target_im.inputs['bspline_fitting'] = '[50]',

        # Range match images
        rama_atlas_im = network.create_node('RangeMatch', id_='rama_atlas',memory='5G')
        rama_atlas_im.inputs['image'] = n4_atlas_im.outputs['image']
        rama_atlas_im.inputs['mask'] = source_rangemask_atlas.output

        rama_target_im = network.create_node('RangeMatch', id_='rama_target',memory='5G')
        rama_target_im.inputs['image'] = n4_target_im.outputs['image']
        rama_target_im.inputs['mask'] = morph.outputs['image']

        # Create filter image for T1
        scalespacefilter = network.create_node('GaussianScaleSpace', id_='scalespacefilter', memory='12G')
        scalespacefilter.inputs['image'] = rama_target_im.outputs['image']
        scalespacefilter.inputs['scales'] = scales

        # Apply classifier
        n_cores = 8
        applyclass = network.create_node('ApplyClassifier', id_='applyclass', memory='8G',cores=n_cores)
        applyclass.inputs['image'] = scalespacefilter.outputs['image']
        applyclass.inputs['classifier'] = classifier.output
        applyclass.inputs['number_of_classes'] = [nrclasses]
        applyclass.inputs['number_of_cores'] = [n_cores]

        # Moderate class output to range 0.1 - 0.9
        mult = network.create_node('PxUnaryImageOperator', id_='mult')
        mult_link_1 = network.create_link(applyclass.outputs['probability_image'], mult.inputs['image'])
        mult_link_1.expand = True
        mult.inputs['operator'] = ['RPOWER']
        mult.inputs['argument'] = [0.2]

        # Multi-atlas segmentation part
        reg_t1 = network.create_node(fastr.toollist['Elastix','4.8'], id_='reg_t1', memory='8G')
        reg_t1.inputs['fixed_image'] = rama_target_im.outputs['image']
        reg_t1.inputs['moving_image'] = rama_atlas_im.outputs['image']
        reg_t1.inputs['moving_image'].input_group = 'atlas'
        reg_t1.inputs['parameters'] = registration_parameters
        reg_t1.inputs['fixed_mask'] = morph.outputs['image']
        reg_t1.inputs['moving_mask'] = source_atlasROI.output
        reg_t1.inputs['moving_mask'].input_group = 'atlas'

        trans_label = network.create_node('Transformix', id_='trans_label')
        trans_label.inputs['image'] = source_atlasLabels.output
        trans_label.inputs['transform'] = reg_t1.outputs['transform'][-1]

        combine_label = network.create_node('PxCombineSegmentations', id_='combine_label')
        link_combine = network.create_link(trans_label.outputs['image'], combine_label.inputs['images'])
        link_combine.collapse = 'atlas'
        combine_label.inputs['method'] = ['VOTE']
        combine_label.inputs['number_of_classes'] = [nrclasses]

        # Combine atlas + classifier
        times = network.create_node('PxBinaryImageOperator', id_='times')
        times.inputs['images'] = mult.outputs['image']
        times.inputs['operator'] = ['TIMES']
        times_link_1 = times.inputs['images'].append(combine_label.outputs['soft_segment'])
        times_link_1.expand = True

        # Tool for picking the correct map based on the max prob
        argmax = network.create_node('ArgMaxImage', id_='argmax')
        link = network.create_link(times.outputs['image'], argmax.inputs['image'])
        link.collapse = 1

        # compute segmentation volume
        count_nonzero = network.create_node(fastr.toollist['GetQuantitativeMeasures','0.2'], id_='count_nonzero')
        count_nonzero.inputs['label'] = argmax.outputs['image']
        count_nonzero.inputs['volume'] = ['mm^3']

        # produce qib xml file

        convert_to_qib = network.create_node(fastr.toollist['ConvertCsvToQibSessionMH','0.3'], id_='convert_to_qib')
        convert_to_qib.inputs['tool'] = ('MultiAtlas Appearance Model Segmentation with Volume Calculation'),
        convert_to_qib.inputs['tool_version'] = ('0.1'),
        convert_to_qib.inputs['description'] = ('MultiAtlas Appearance Model Segmentation'),
        convert_to_qib.inputs['begin_date'] = (time.strftime("%Y-%m-%dT%H:%M")),
        convert_to_qib.inputs['processing_site'] = ('Erasmus MC'),
        convert_to_qib.inputs['paper_title'] = ('Automated brain structure segmentation based on atlas registration and appearance models'),
        convert_to_qib.inputs['paper_link'] = ('/onlinelibrary.wiley.com/doi/10.1002/hbm.22522/full'),
        convert_to_qib.inputs['paper_notes'] = ('Method is a variant of version described in paper (no MRF model for spatial coherence'),
        convert_to_qib.inputs['categories'] = ('Femoral Cartilage'),
        convert_to_qib.inputs['ontologyname'] = ('Uberon'),
        convert_to_qib.inputs['ontologyIRI'] = ('NA'),
        convert_to_qib.inputs['csv'] = count_nonzero.outputs['statistics']
        convert_to_qib.inputs['session'] = session_id.output

        # Create sink for dice overlap score
        out_qib_session = network.create_sink(datatype=fastr.typelist['XmlFile'],id_='out_qib_session')
        link = network.create_link(convert_to_qib.outputs['qib_session'],out_qib_session.input)
        #link.collapse = 'target'

        # Create sink
        out_seg = network.create_sink('NiftiImageFileCompressed', id_='out_seg')
        out_seg.input = argmax.outputs['image']


def main():

    sinkdata = {'out_seg':     'vfs://fastr_data/PROOF170213_results/segm_biascor_appearatlas_PROOF_{sample_id}{ext}',
                'out_qib_session': 'vfs://fastr_data/PROOF170213_results/QIB_biascor_{sample_id}{ext}'}

    sourcedata = {
        'atlas_img_genmask': {
             'scan_9040390_20051221':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9040390_20051221_SAG_3D_DESS_RIGHT_016610646609_ims.nii.gz',#1
             'scan_9054866_20051031':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9054866_20051031_SAG_3D_DESS_RIGHT_016610951809_ims.nii.gz',#2
             'scan_9087863_20060130':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9087863_20060130_SAG_3D_DESS_RIGHT_016610820609_ims.nii.gz',#3
             'scan_9146462_20060213':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9146462_20060213_SAG_3D_DESS_RIGHT_016610859809_ims.nii.gz',#4
             'scan_9172459_20051217':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9172459_20051217_SAG_3D_DESS_RIGHT_016610642112_ims.nii.gz',#5
             'scan_9192885_20060130':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9192885_20060130_SAG_3D_DESS_RIGHT_016610822212_ims.nii.gz',#6
             'scan_9211869_20060307':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9211869_20060307_SAG_3D_DESS_RIGHT_016610880409_ims.nii.gz',#7
             'scan_9215390_20060131':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9215390_20060131_SAG_3D_DESS_RIGHT_016610821812_ims.nii.gz',#8
             'scan_9264046_20050622':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9264046_20050622_SAG_3D_DESS_RIGHT_016610935130_ims.nii.gz',#9
             'scan_9309170_20050812':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9309170_20050812_SAG_3D_DESS_RIGHT_016610469409_ims.nii.gz',#10
           },
        'atlas_labels_genmask':{
             'groundtruth_9040390_20051221':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9040390_20051221_SAG_3D_DESS_RIGHT_016610646609_FemoralCartilage_GT.nii.gz',#1
             'groundtruth_9054866_20051031':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9054866_20051031_SAG_3D_DESS_RIGHT_016610951809_FemoralCartilage_GT.nii.gz',#2
             'groundtruth_9087863_20060130':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9087863_20060130_SAG_3D_DESS_RIGHT_016610820609_FemoralCartilage_GT.nii.gz',#3
             'groundtruth_9146462_20060213':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9146462_20060213_SAG_3D_DESS_RIGHT_016610859809_FemoralCartilage_GT.nii.gz',#4
             'groundtruth_9172459_20051217':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9172459_20051217_SAG_3D_DESS_RIGHT_016610642112_FemoralCartilage_GT.nii.gz',#5
             'groundtruth_9192885_20060130':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9192885_20060130_SAG_3D_DESS_RIGHT_016610822212_FemoralCartilage_GT.nii.gz',#6
             'groundtruth_9211869_20060307':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9211869_20060307_SAG_3D_DESS_RIGHT_016610880409_FemoralCartilage_GT.nii.gz',#7
             'groundtruth_9215390_20060131':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9215390_20060131_SAG_3D_DESS_RIGHT_016610821812_FemoralCartilage_GT.nii.gz',#8
             'groundtruth_9264046_20050622':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9264046_20050622_SAG_3D_DESS_RIGHT_016610935130_FemoralCartilage_GT.nii.gz',#9
             'groundtruth_9309170_20050812':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9309170_20050812_SAG_3D_DESS_RIGHT_016610469409_FemoralCartilage_GT.nii.gz',#10
              },
        'atlas_img':  {
            'scan_9040390_20051221':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9040390_20051221_SAG_3D_DESS_RIGHT_016610646609_ims.nii.gz',#1
            'scan_9054866_20051031':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9054866_20051031_SAG_3D_DESS_RIGHT_016610951809_ims.nii.gz',#2
            'scan_9087863_20060130':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9087863_20060130_SAG_3D_DESS_RIGHT_016610820609_ims.nii.gz',#3
            'scan_9146462_20060213':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9146462_20060213_SAG_3D_DESS_RIGHT_016610859809_ims.nii.gz',#4
            'scan_9172459_20051217':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9172459_20051217_SAG_3D_DESS_RIGHT_016610642112_ims.nii.gz',#5
            'scan_9192885_20060130':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9192885_20060130_SAG_3D_DESS_RIGHT_016610822212_ims.nii.gz',#6
            'scan_9211869_20060307':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9211869_20060307_SAG_3D_DESS_RIGHT_016610880409_ims.nii.gz',#7
            'scan_9215390_20060131':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9215390_20060131_SAG_3D_DESS_RIGHT_016610821812_ims.nii.gz',#8
            'scan_9264046_20050622':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9264046_20050622_SAG_3D_DESS_RIGHT_016610935130_ims.nii.gz',#9
            'scan_9309170_20050812':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9309170_20050812_SAG_3D_DESS_RIGHT_016610469409_ims.nii.gz',#10
            'scan_9311328_20050415':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9311328_20050415_SAG_3D_DESS_RIGHT_016610374112_ims.nii.gz',#11
            'scan_9331465_20050419':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9331465_20050419_SAG_3D_DESS_RIGHT_016610382114_ims.nii.gz',#12
            'scan_9332085_20060109':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9332085_20060109_SAG_3D_DESS_RIGHT_016610666109_ims.nii.gz',#13
            'scan_9368622_20060408':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9368622_20060408_SAG_3D_DESS_RIGHT_016611081409_ims.nii.gz',#14
            'scan_9382271_20050415':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9382271_20050415_SAG_3D_DESS_RIGHT_016610375312_ims.nii.gz',#15
            'scan_9415074_20050726':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9415074_20050726_SAG_3D_DESS_RIGHT_016610438114_ims.nii.gz',#16
            'scan_9444401_20050712':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9444401_20050712_SAG_3D_DESS_RIGHT_016610417603_ims.nii.gz',#17
            'scan_9482482_20051128':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9482482_20051128_SAG_3D_DESS_RIGHT_016610800137_ims.nii.gz',#18
            'scan_9493245_20060223':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9493245_20060223_SAG_3D_DESS_RIGHT_016610867009_ims.nii.gz',#19
            'scan_9500390_20050831':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9500390_20050831_SAG_3D_DESS_RIGHT_016610497609_ims.nii.gz',#20
            'scan_9539084_20050824':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9539084_20050824_SAG_3D_DESS_RIGHT_016610488610_ims.nii.gz',#21
            'scan_9597990_20060223':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9597990_20060223_SAG_3D_DESS_RIGHT_016610861609_ims.nii.gz',#22
            'scan_9599539_20050809':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9599539_20050809_SAG_3D_DESS_RIGHT_016610455909_ims.nii.gz',#23
            'scan_9602703_20050523':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9602703_20050523_SAG_3D_DESS_RIGHT_016610742229_ims.nii.gz',#24
            'scan_9607698_20050512':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9607698_20050512_SAG_3D_DESS_RIGHT_016610760512_ims.nii.gz',#25
            'scan_9625955_20050810':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9625955_20050810_SAG_3D_DESS_RIGHT_016610460509_ims.nii.gz',#26
            'scan_9626069_20050819':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9626069_20050819_SAG_3D_DESS_RIGHT_016610487509_ims.nii.gz',#27
            'scan_9660697_20050526':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9660697_20050526_SAG_3D_DESS_RIGHT_016610534012_ims.nii.gz',#28
            'scan_9663706_20050629':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9663706_20050629_SAG_3D_DESS_RIGHT_016610409412_ims.nii.gz',#29
            'scan_9674570_20050829':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9674570_20050829_SAG_3D_DESS_RIGHT_016610488714_ims.nii.gz',#30
        },
        'atlas_labels':  {
            'groundtruth_9040390_20051221':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9040390_20051221_SAG_3D_DESS_RIGHT_016610646609_FemoralCartilage_GT.nii.gz',#1
            'groundtruth_9054866_20051031':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9054866_20051031_SAG_3D_DESS_RIGHT_016610951809_FemoralCartilage_GT.nii.gz',#2
            'groundtruth_9087863_20060130':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9087863_20060130_SAG_3D_DESS_RIGHT_016610820609_FemoralCartilage_GT.nii.gz',#3
            'groundtruth_9146462_20060213':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9146462_20060213_SAG_3D_DESS_RIGHT_016610859809_FemoralCartilage_GT.nii.gz',#4
            'groundtruth_9172459_20051217':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9172459_20051217_SAG_3D_DESS_RIGHT_016610642112_FemoralCartilage_GT.nii.gz',#5
            'groundtruth_9192885_20060130':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9192885_20060130_SAG_3D_DESS_RIGHT_016610822212_FemoralCartilage_GT.nii.gz',#6
            'groundtruth_9211869_20060307':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9211869_20060307_SAG_3D_DESS_RIGHT_016610880409_FemoralCartilage_GT.nii.gz',#7
            'groundtruth_9215390_20060131':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9215390_20060131_SAG_3D_DESS_RIGHT_016610821812_FemoralCartilage_GT.nii.gz',#8
            'groundtruth_9264046_20050622':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9264046_20050622_SAG_3D_DESS_RIGHT_016610935130_FemoralCartilage_GT.nii.gz',#9
            'groundtruth_9309170_20050812':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9309170_20050812_SAG_3D_DESS_RIGHT_016610469409_FemoralCartilage_GT.nii.gz',#10
            'groundtruth_9311328_20050415':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9311328_20050415_SAG_3D_DESS_RIGHT_016610374112_FemoralCartilage_GT.nii.gz',#11
            'groundtruth_9331465_20050419':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9331465_20050419_SAG_3D_DESS_RIGHT_016610382114_FemoralCartilage_GT.nii.gz',#12
            'groundtruth_9332085_20060109':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9332085_20060109_SAG_3D_DESS_RIGHT_016610666109_FemoralCartilage_GT.nii.gz',#13
            'groundtruth_9368622_20060408':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9368622_20060408_SAG_3D_DESS_RIGHT_016611081409_FemoralCartilage_GT.nii.gz',#14
            'groundtruth_9382271_20050415':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9382271_20050415_SAG_3D_DESS_RIGHT_016610375312_FemoralCartilage_GT.nii.gz',#15
            'groundtruth_9415074_20050726':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9415074_20050726_SAG_3D_DESS_RIGHT_016610438114_FemoralCartilage_GT.nii.gz',#16
            'groundtruth_9444401_20050712':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9444401_20050712_SAG_3D_DESS_RIGHT_016610417603_FemoralCartilage_GT.nii.gz',#17
            'groundtruth_9482482_20051128':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9482482_20051128_SAG_3D_DESS_RIGHT_016610800137_FemoralCartilage_GT.nii.gz',#18
            'groundtruth_9493245_20060223':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9493245_20060223_SAG_3D_DESS_RIGHT_016610867009_FemoralCartilage_GT.nii.gz',#19
            'groundtruth_9500390_20050831':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9500390_20050831_SAG_3D_DESS_RIGHT_016610497609_FemoralCartilage_GT.nii.gz',#20
            'groundtruth_9539084_20050824':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9539084_20050824_SAG_3D_DESS_RIGHT_016610488610_FemoralCartilage_GT.nii.gz',#21
            'groundtruth_9597990_20060223':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9597990_20060223_SAG_3D_DESS_RIGHT_016610861609_FemoralCartilage_GT.nii.gz',#22
            'groundtruth_9599539_20050809':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9599539_20050809_SAG_3D_DESS_RIGHT_016610455909_FemoralCartilage_GT.nii.gz',#23
            'groundtruth_9602703_20050523':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9602703_20050523_SAG_3D_DESS_RIGHT_016610742229_FemoralCartilage_GT.nii.gz',#24
            'groundtruth_9607698_20050512':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9607698_20050512_SAG_3D_DESS_RIGHT_016610760512_FemoralCartilage_GT.nii.gz',#25
            'groundtruth_9625955_20050810':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9625955_20050810_SAG_3D_DESS_RIGHT_016610460509_FemoralCartilage_GT.nii.gz',#26
            'groundtruth_9626069_20050819':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9626069_20050819_SAG_3D_DESS_RIGHT_016610487509_FemoralCartilage_GT.nii.gz',#27
            'groundtruth_9660697_20050526':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9660697_20050526_SAG_3D_DESS_RIGHT_016610534012_FemoralCartilage_GT.nii.gz',#28
            'groundtruth_9663706_20050629':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9663706_20050629_SAG_3D_DESS_RIGHT_016610409412_FemoralCartilage_GT.nii.gz',#29
            'groundtruth_9674570_20050829':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_FemoralCartilage_GT/9674570_20050829_SAG_3D_DESS_RIGHT_016610488714_FemoralCartilage_GT.nii.gz',#30
        },
        'atlas_ROI': {
            'maskROI_9040390_20051221':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9040390_20051221_SAG_3D_DESS_RIGHT_016610646609_ROI.nii.gz',#1
            'maskROI_9054866_20051031':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9054866_20051031_SAG_3D_DESS_RIGHT_016610951809_ROI.nii.gz',#2
            'maskROI_9087863_20060130':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9087863_20060130_SAG_3D_DESS_RIGHT_016610820609_ROI.nii.gz',#3
            'maskROI_9146462_20060213':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9146462_20060213_SAG_3D_DESS_RIGHT_016610859809_ROI.nii.gz',#4
            'maskROI_9172459_20051217':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9172459_20051217_SAG_3D_DESS_RIGHT_016610642112_ROI.nii.gz',#5
            'maskROI_9192885_20060130':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9192885_20060130_SAG_3D_DESS_RIGHT_016610822212_ROI.nii.gz',#6
            'maskROI_9211869_20060307':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9211869_20060307_SAG_3D_DESS_RIGHT_016610880409_ROI.nii.gz',#7
            'maskROI_9215390_20060131':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9215390_20060131_SAG_3D_DESS_RIGHT_016610821812_ROI.nii.gz',#8
            'maskROI_9264046_20050622':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9264046_20050622_SAG_3D_DESS_RIGHT_016610935130_ROI.nii.gz',#9
            'maskROI_9309170_20050812':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9309170_20050812_SAG_3D_DESS_RIGHT_016610469409_ROI.nii.gz',#10
            'maskROI_9311328_20050415':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9311328_20050415_SAG_3D_DESS_RIGHT_016610374112_ROI.nii.gz',#11
            'maskROI_9331465_20050419':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9331465_20050419_SAG_3D_DESS_RIGHT_016610382114_ROI.nii.gz',#12
            'maskROI_9332085_20060109':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9332085_20060109_SAG_3D_DESS_RIGHT_016610666109_ROI.nii.gz',#13
            'maskROI_9368622_20060408':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9368622_20060408_SAG_3D_DESS_RIGHT_016611081409_ROI.nii.gz',#14
            'maskROI_9382271_20050415':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9382271_20050415_SAG_3D_DESS_RIGHT_016610375312_ROI.nii.gz',#15
            'maskROI_9415074_20050726':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9415074_20050726_SAG_3D_DESS_RIGHT_016610438114_ROI.nii.gz',#16
            'maskROI_9444401_20050712':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9444401_20050712_SAG_3D_DESS_RIGHT_016610417603_ROI.nii.gz',#17
            'maskROI_9482482_20051128':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9482482_20051128_SAG_3D_DESS_RIGHT_016610800137_ROI.nii.gz',#18
            'maskROI_9493245_20060223':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9493245_20060223_SAG_3D_DESS_RIGHT_016610867009_ROI.nii.gz',#19
            'maskROI_9500390_20050831':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9500390_20050831_SAG_3D_DESS_RIGHT_016610497609_ROI.nii.gz',#20
            'maskROI_9539084_20050824':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9539084_20050824_SAG_3D_DESS_RIGHT_016610488610_ROI.nii.gz',#21
            'maskROI_9597990_20060223':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9597990_20060223_SAG_3D_DESS_RIGHT_016610861609_ROI.nii.gz',#22
            'maskROI_9599539_20050809':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9599539_20050809_SAG_3D_DESS_RIGHT_016610455909_ROI.nii.gz',#23
            'maskROI_9602703_20050523':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9602703_20050523_SAG_3D_DESS_RIGHT_016610742229_ROI.nii.gz',#24
            'maskROI_9607698_20050512':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9607698_20050512_SAG_3D_DESS_RIGHT_016610760512_ROI.nii.gz',#25
            'maskROI_9625955_20050810':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9625955_20050810_SAG_3D_DESS_RIGHT_016610460509_ROI.nii.gz',#26
            'maskROI_9626069_20050819':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9626069_20050819_SAG_3D_DESS_RIGHT_016610487509_ROI.nii.gz',#27
            'maskROI_9660697_20050526':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9660697_20050526_SAG_3D_DESS_RIGHT_016610534012_ROI.nii.gz',#28
            'maskROI_9663706_20050629':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9663706_20050629_SAG_3D_DESS_RIGHT_016610409412_ROI.nii.gz',#29
            'maskROI_9674570_20050829':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_ROI/9674570_20050829_SAG_3D_DESS_RIGHT_016610488714_ROI.nii.gz',#30
        },
        'target_dicom':           {
'PROOF001_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF001/experiments/PROOF001_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF002_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF002/experiments/PROOF002_MRI_R_T0/scans/801/resources/DICOM?insecure=true',
'PROOF003_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF003/experiments/PROOF003_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF004_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF004/experiments/PROOF004_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF005_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF005/experiments/PROOF005_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF006_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF006/experiments/PROOF006_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF007_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF007/experiments/PROOF007_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF008_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF008/experiments/PROOF008_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF009_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF009/experiments/PROOF009_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF010_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF010/experiments/PROOF010_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF011_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF011/experiments/PROOF011_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF012_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF012/experiments/PROOF012_MRI_R_T0/scans/801/resources/DICOM?insecure=true',
'PROOF013_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF013/experiments/PROOF013_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF014_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF014/experiments/PROOF014_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF015_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF015/experiments/PROOF015_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF016_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF016/experiments/PROOF016_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF017_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF017/experiments/PROOF017_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF018_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF018/experiments/PROOF018_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF019_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF019/experiments/PROOF019_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF020_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF020/experiments/PROOF020_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF021_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF021/experiments/PROOF021_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF022_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF022/experiments/PROOF022_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF023_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF023/experiments/PROOF023_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF024_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF024/experiments/PROOF024_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF025_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF025/experiments/PROOF025_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF026_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF026/experiments/PROOF026_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF027_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF027/experiments/PROOF027_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF028_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF028/experiments/PROOF028_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF029_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF029/experiments/PROOF029_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF030_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF030/experiments/PROOF030_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF031_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF031/experiments/PROOF031_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF032_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF032/experiments/PROOF032_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF033_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF033/experiments/PROOF033_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF034_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF034/experiments/PROOF034_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF035_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF035/experiments/PROOF035_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF036_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF036/experiments/PROOF036_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF037_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF037/experiments/PROOF037_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF038_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF038/experiments/PROOF038_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF039_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF039/experiments/PROOF039_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF040_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF040/experiments/PROOF040_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF041_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF041/experiments/PROOF041_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF042_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF042/experiments/PROOF042_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF043_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF043/experiments/PROOF043_MRI_R_T0/scans/801/resources/DICOM?insecure=true',
'PROOF044_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF044/experiments/PROOF044_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF045_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF045/experiments/PROOF045_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF046_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF046/experiments/PROOF046_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF047_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF047/experiments/PROOF047_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF048_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF048/experiments/PROOF048_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF049_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF049/experiments/PROOF049_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF050_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF050/experiments/PROOF050_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF051_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF051/experiments/PROOF051_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF052_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF052/experiments/PROOF052_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF053_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF053/experiments/PROOF053_MRI_R_T0/scans/801/resources/DICOM?insecure=true',
'PROOF054_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF054/experiments/PROOF054_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF055_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF055/experiments/PROOF055_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF056_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF056/experiments/PROOF056_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF057_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF057/experiments/PROOF057_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF058_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF058/experiments/PROOF058_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF059_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF059/experiments/PROOF059_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF060_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF060/experiments/PROOF060_MRI_R_T0/scans/701-MR2/resources/DICOM?insecure=true',
'PROOF061_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF061/experiments/PROOF061_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF062_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF062/experiments/PROOF062_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF063_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF063/experiments/PROOF063_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF064_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF064/experiments/PROOF064_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF065_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF065/experiments/PROOF065_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF066_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF066/experiments/PROOF066_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF067_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF067/experiments/PROOF067_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF068_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF068/experiments/PROOF068_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF069_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF069/experiments/PROOF069_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF070_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF070/experiments/PROOF070_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF070_MRI_R_T0_2':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF070/experiments/PROOF070_MRI_R_T0/scans/801/resources/DICOM?insecure=true',
'PROOF071_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF071/experiments/PROOF071_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF072_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF072/experiments/PROOF072_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF073_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF073/experiments/PROOF073_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF074_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF074/experiments/PROOF074_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF075_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF075/experiments/PROOF075_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF076_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF076/experiments/PROOF076_MRI_R_T0/scans/801/resources/DICOM?insecure=true',
'PROOF077_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF077/experiments/PROOF077_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF078_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF078/experiments/PROOF078_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF079_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF079/experiments/PROOF079_MRI_R_T0/scans/801/resources/DICOM?insecure=true',
'PROOF080_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF080/experiments/PROOF080_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF081_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF081/experiments/PROOF081_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF082_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF082/experiments/PROOF082_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF083_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF083/experiments/PROOF083_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF084_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF084/experiments/PROOF084_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF084_MRI_R_T0_2':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF084/experiments/PROOF084_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF085_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF085/experiments/PROOF085_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF086_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF086/experiments/PROOF086_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF087_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF087/experiments/PROOF087_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF088_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF088/experiments/PROOF088_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF089_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF089/experiments/PROOF089_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF090_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF090/experiments/PROOF090_MRI_R_T0/scans/901/resources/DICOM?insecure=true',
'PROOF090_MRI_R_T0_2':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF090/experiments/PROOF090_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF091_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF091/experiments/PROOF091_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF092_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF092/experiments/PROOF092_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF093_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF093/experiments/PROOF093_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF094_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF094/experiments/PROOF094_MRI_R_T0/scans/4/resources/DICOM?insecure=true',
'PROOF095_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF095/experiments/PROOF095_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF096_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF096/experiments/PROOF096_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF097_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF097/experiments/PROOF097_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF098_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF098/experiments/PROOF098_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF099_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF099/experiments/PROOF099_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF100_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF100/experiments/PROOF100_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF101_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF101/experiments/PROOF101_MRI_R_T0/scans/8/resources/DICOM?insecure=true',
'PROOF102_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF102/experiments/PROOF102_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF103_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF103/experiments/PROOF103_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF104_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF104/experiments/PROOF104_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF105_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF105/experiments/PROOF105_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF106_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF106/experiments/PROOF106_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF107_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF107/experiments/PROOF107_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF108_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF108/experiments/PROOF108_MRI_R_T0/scans/4/resources/DICOM?insecure=true',
'PROOF109_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF109/experiments/PROOF109_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF111_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF111/experiments/PROOF111_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF112_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF112/experiments/PROOF112_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF113_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF113/experiments/PROOF113_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF114_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF114/experiments/PROOF114_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF115_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF115/experiments/PROOF115_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF116_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF116/experiments/PROOF116_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF117_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF117/experiments/PROOF117_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF118_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF118/experiments/PROOF118_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF119_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF119/experiments/PROOF119_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF120_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF120/experiments/PROOF120_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF121_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF121/experiments/PROOF121_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF122_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF122/experiments/PROOF122_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF123_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF123/experiments/PROOF123_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF125_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF125/experiments/PROOF125_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF126_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF126/experiments/PROOF126_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF127_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF127/experiments/PROOF127_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF128_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF128/experiments/PROOF128_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF129_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF129/experiments/PROOF129_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF130_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF130/experiments/PROOF130_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF131_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF131/experiments/PROOF131_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF132_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF132/experiments/PROOF132_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF133_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF133/experiments/PROOF133_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF134_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF134/experiments/PROOF134_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF135_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF135/experiments/PROOF135_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF136_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF136/experiments/PROOF136_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF137_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF137/experiments/PROOF137_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF138_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF138/experiments/PROOF138_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF139_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF139/experiments/PROOF139_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF140_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF140/experiments/PROOF140_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF141_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF141/experiments/PROOF141_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF142_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF142/experiments/PROOF142_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF143_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF143/experiments/PROOF143_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF144_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF144/experiments/PROOF144_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF145_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF145/experiments/PROOF145_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF146_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF146/experiments/PROOF146_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF147_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF147/experiments/PROOF147_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF148_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF148/experiments/PROOF148_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF149_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF149/experiments/PROOF149_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF150_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF150/experiments/PROOF150_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF152_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF152/experiments/PROOF152_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF153_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF153/experiments/PROOF153_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF154_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF154/experiments/PROOF154_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF155_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF155/experiments/PROOF155_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF156_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF156/experiments/PROOF156_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF157_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF157/experiments/PROOF157_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF158_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF158/experiments/PROOF158_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF159_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF159/experiments/PROOF159_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF160_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF160/experiments/PROOF160_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF161_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF161/experiments/PROOF161_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF162_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF162/experiments/PROOF162_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF163_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF163/experiments/PROOF163_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF164_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF164/experiments/PROOF164_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF165_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF165/experiments/PROOF165_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF166_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF166/experiments/PROOF166_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF167_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF167/experiments/PROOF167_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF168_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF168/experiments/PROOF168_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF169_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF169/experiments/PROOF169_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF170_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF170/experiments/PROOF170_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF171_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF171/experiments/PROOF171_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF172_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF172/experiments/PROOF172_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF173_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF173/experiments/PROOF173_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF174_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF174/experiments/PROOF174_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF175_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF175/experiments/PROOF175_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF176_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF176/experiments/PROOF176_MRI_R_T0/scans/801/resources/DICOM?insecure=true',
'PROOF177_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF177/experiments/PROOF177_MRI_R_T0/scans/12/resources/DICOM?insecure=true',
'PROOF178_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF178/experiments/PROOF178_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF179_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF179/experiments/PROOF179_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF180_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF180/experiments/PROOF180_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF181_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF181/experiments/PROOF181_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF182_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF182/experiments/PROOF182_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF183_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF183/experiments/PROOF183_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF184_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF184/experiments/PROOF184_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF185_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF185/experiments/PROOF185_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF186_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF186/experiments/PROOF186_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF187_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF187/experiments/PROOF187_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF188_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF188/experiments/PROOF188_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF189_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF189/experiments/PROOF189_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF190_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF190/experiments/PROOF190_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF191_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF191/experiments/PROOF191_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF192_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF192/experiments/PROOF192_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF193_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF193/experiments/PROOF193_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF194_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF194/experiments/PROOF194_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF195_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF195/experiments/PROOF195_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF196_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF196/experiments/PROOF196_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF197_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF197/experiments/PROOF197_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF198_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF198/experiments/PROOF198_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF199_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF199/experiments/PROOF199_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF200_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF200/experiments/PROOF200_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF201_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF201/experiments/PROOF201_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF202_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF202/experiments/PROOF202_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF203_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF203/experiments/PROOF203_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF204_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF204/experiments/PROOF204_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF205_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF205/experiments/PROOF205_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF206_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF206/experiments/PROOF206_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF207_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF207/experiments/PROOF207_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF208_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF208/experiments/PROOF208_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF209_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF209/experiments/PROOF209_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF210_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF210/experiments/PROOF210_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF211_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF211/experiments/PROOF211_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF212_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF212/experiments/PROOF212_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF212_MRI_R_T0_2':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF212/experiments/PROOF212_MRI_R_T0/scans/801/resources/DICOM?insecure=true',
'PROOF213_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF213/experiments/PROOF213_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF214_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF214/experiments/PROOF214_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF215_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF215/experiments/PROOF215_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF216_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF216/experiments/PROOF216_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF217_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF217/experiments/PROOF217_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF218_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF218/experiments/PROOF218_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF219_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF219/experiments/PROOF219_MRI_R_T0/scans/14/resources/DICOM?insecure=true',
'PROOF220_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF220/experiments/PROOF220_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF221_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF221/experiments/PROOF221_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF222_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF222/experiments/PROOF222_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF223_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF223/experiments/PROOF223_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF224_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF224/experiments/PROOF224_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF225_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF225/experiments/PROOF225_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF226_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF226/experiments/PROOF226_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF227_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF227/experiments/PROOF227_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF228_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF228/experiments/PROOF228_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF229_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF229/experiments/PROOF229_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF230_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF230/experiments/PROOF230_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF231_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF231/experiments/PROOF231_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF232_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF232/experiments/PROOF232_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF233_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF233/experiments/PROOF233_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF234_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF234/experiments/PROOF234_MRI_R_T0/scans/801/resources/DICOM?insecure=true',
'PROOF235_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF235/experiments/PROOF235_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF236_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF236/experiments/PROOF236_MRI_R_T0/scans/501/resources/DICOM?insecure=true',
'PROOF237_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF237/experiments/PROOF237_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF238_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF238/experiments/PROOF238_MRI_R_T0/scans/3/resources/DICOM?insecure=true',
'PROOF239_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF239/experiments/PROOF239_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF240_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF240/experiments/PROOF240_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF241_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF241/experiments/PROOF241_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF242_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF242/experiments/PROOF242_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF243_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF243/experiments/PROOF243_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF244_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF244/experiments/PROOF244_MRI_R_T0/scans/701/resources/DICOM?insecure=true',
'PROOF245_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF245/experiments/PROOF245_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF246_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF246/experiments/PROOF246_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF247_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF247/experiments/PROOF247_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF248_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF248/experiments/PROOF248_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF249_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF249/experiments/PROOF249_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF250_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF250/experiments/PROOF250_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF251_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF251/experiments/PROOF251_MRI_R_T0/scans/14/resources/DICOM?insecure=true',
'PROOF253_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF253/experiments/PROOF253_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF254_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF254/experiments/PROOF254_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF255_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF255/experiments/PROOF255_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF256_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF256/experiments/PROOF256_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF257_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF257/experiments/PROOF257_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF258_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF258/experiments/PROOF258_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF259_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF259/experiments/PROOF259_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF260_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF260/experiments/PROOF260_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF261_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF261/experiments/PROOF261_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF262_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF262/experiments/PROOF262_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF263_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF263/experiments/PROOF263_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF264_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF264/experiments/PROOF264_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF265_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF265/experiments/PROOF265_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF266_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF266/experiments/PROOF266_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF267_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF267/experiments/PROOF267_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF268_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF268/experiments/PROOF268_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF269_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF269/experiments/PROOF269_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF270_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF270/experiments/PROOF270_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF271_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF271/experiments/PROOF271_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF272_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF272/experiments/PROOF272_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF273_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF273/experiments/PROOF273_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF274_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF274/experiments/PROOF274_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF275_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF275/experiments/PROOF275_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF276_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF276/experiments/PROOF276_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF277_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF277/experiments/PROOF277_MRI_R_T0/scans/601/resources/DICOM?insecure=true',
'PROOF278_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF278/experiments/PROOF278_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF279_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF279/experiments/PROOF279_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF280_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF280/experiments/PROOF280_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF281_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF281/experiments/PROOF281_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF282_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF282/experiments/PROOF282_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF283_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF283/experiments/PROOF283_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF284_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF284/experiments/PROOF284_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF285_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF285/experiments/PROOF285_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF286_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF286/experiments/PROOF286_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF287_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF287/experiments/PROOF287_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF288_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF288/experiments/PROOF288_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF289_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF289/experiments/PROOF289_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF290_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF290/experiments/PROOF290_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF291_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF291/experiments/PROOF291_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF292_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF292/experiments/PROOF292_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF293_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF293/experiments/PROOF293_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF294_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF294/experiments/PROOF294_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF295_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF295/experiments/PROOF295_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF296_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF296/experiments/PROOF296_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF297_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF297/experiments/PROOF297_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF300_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF300/experiments/PROOF300_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF301_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF301/experiments/PROOF301_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF302_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF302/experiments/PROOF302_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF303_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF303/experiments/PROOF303_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF304_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF304/experiments/PROOF304_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF305_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF305/experiments/PROOF305_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF306_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF306/experiments/PROOF306_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF307_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF307/experiments/PROOF307_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF308_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF308/experiments/PROOF308_MRI_R_T0/scans/12/resources/DICOM?insecure=true',
'PROOF309_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF309/experiments/PROOF309_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF310_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF310/experiments/PROOF310_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF311_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF311/experiments/PROOF311_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF312_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF312/experiments/PROOF312_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF314_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF314/experiments/PROOF314_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF315_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF315/experiments/PROOF315_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF316_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF316/experiments/PROOF316_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF317_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF317/experiments/PROOF317_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF318_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF318/experiments/PROOF318_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF319_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF319/experiments/PROOF319_MRI_R_T0/scans/12/resources/DICOM?insecure=true',
'PROOF320_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF320/experiments/PROOF320_MRI_R_T0/scans/12/resources/DICOM?insecure=true',
'PROOF321_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF321/experiments/PROOF321_MRI_R_T0/scans/12/resources/DICOM?insecure=true',
'PROOF322_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF322/experiments/PROOF322_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF323_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF323/experiments/PROOF323_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF324_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF324/experiments/PROOF324_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF325_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF325/experiments/PROOF325_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF326_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF326/experiments/PROOF326_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF327_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF327/experiments/PROOF327_MRI_R_T0/scans/9/resources/DICOM?insecure=true',
'PROOF328_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF328/experiments/PROOF328_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF329_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF329/experiments/PROOF329_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF330_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF330/experiments/PROOF330_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF331_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF331/experiments/PROOF331_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF332_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF332/experiments/PROOF332_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF333_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF333/experiments/PROOF333_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF334_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF334/experiments/PROOF334_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF336_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF336/experiments/PROOF336_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF337_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF337/experiments/PROOF337_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF338_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF338/experiments/PROOF338_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF339_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF339/experiments/PROOF339_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF340_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF340/experiments/PROOF340_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF341_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF341/experiments/PROOF341_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF343_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF343/experiments/PROOF343_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF344_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF344/experiments/PROOF344_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF345_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF345/experiments/PROOF345_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF346_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF346/experiments/PROOF346_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF347_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF347/experiments/PROOF347_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF348_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF348/experiments/PROOF348_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF349_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF349/experiments/PROOF349_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF350_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF350/experiments/PROOF350_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF351_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF351/experiments/PROOF351_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF352_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF352/experiments/PROOF352_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF353_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF353/experiments/PROOF353_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF354_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF354/experiments/PROOF354_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF356_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF356/experiments/PROOF356_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF357_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF357/experiments/PROOF357_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF358_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF358/experiments/PROOF358_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF359_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF359/experiments/PROOF359_MRI_R_T0/scans/9/resources/DICOM?insecure=true',
'PROOF360_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF360/experiments/PROOF360_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF362_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF362/experiments/PROOF362_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF363_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF363/experiments/PROOF363_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF364_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF364/experiments/PROOF364_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF365_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF365/experiments/PROOF365_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF366_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF366/experiments/PROOF366_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF367_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF367/experiments/PROOF367_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF368_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF368/experiments/PROOF368_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF369_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF369/experiments/PROOF369_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF370_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF370/experiments/PROOF370_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF371_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF371/experiments/PROOF371_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF372_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF372/experiments/PROOF372_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF373_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF373/experiments/PROOF373_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF374_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF374/experiments/PROOF374_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF375_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF375/experiments/PROOF375_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF376_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF376/experiments/PROOF376_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF377_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF377/experiments/PROOF377_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF378_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF378/experiments/PROOF378_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF379_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF379/experiments/PROOF379_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF380_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF380/experiments/PROOF380_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF381_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF381/experiments/PROOF381_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF382_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF382/experiments/PROOF382_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF383_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF383/experiments/PROOF383_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF384_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF384/experiments/PROOF384_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF385_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF385/experiments/PROOF385_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF386_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF386/experiments/PROOF386_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF387_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF387/experiments/PROOF387_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF388_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF388/experiments/PROOF388_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF389_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF389/experiments/PROOF389_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF390_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF390/experiments/PROOF390_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF391_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF391/experiments/PROOF391_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF392_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF392/experiments/PROOF392_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF393_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF393/experiments/PROOF393_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF394_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF394/experiments/PROOF394_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF395_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF395/experiments/PROOF395_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF396_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF396/experiments/PROOF396_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF397_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF397/experiments/PROOF397_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF398_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF398/experiments/PROOF398_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF399_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF399/experiments/PROOF399_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF400_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF400/experiments/PROOF400_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF401_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF401/experiments/PROOF401_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF402_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF402/experiments/PROOF402_MRI_R_T0/scans/7/resources/DICOM?insecure=true',
'PROOF403_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF403/experiments/PROOF403_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF404_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF404/experiments/PROOF404_MRI_R_T0/scans/9/resources/DICOM?insecure=true',
'PROOF405_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF405/experiments/PROOF405_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF406_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF406/experiments/PROOF406_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
'PROOF407_MRI_R_T0':'xnat://bigr-rad-xnat.erasmusmc.nl/data/archive/projects/Proof_Study/subjects/PROOF407/experiments/PROOF407_MRI_R_T0/scans/6/resources/DICOM?insecure=true',
        },   #
        'session_ids':{
            'PROOF001_MRI_R_T0':'PROOF001_MRI_R_T0',#1
            'PROOF002_MRI_R_T0':'PROOF002_MRI_R_T0',#2
            'PROOF003_MRI_R_T0':'PROOF003_MRI_R_T0',#3
            'PROOF004_MRI_R_T0':'PROOF004_MRI_R_T0',#4
            'PROOF005_MRI_R_T0':'PROOF005_MRI_R_T0',#5
            'PROOF006_MRI_R_T0':'PROOF006_MRI_R_T0',#6
            'PROOF007_MRI_R_T0':'PROOF007_MRI_R_T0',#7
            'PROOF008_MRI_R_T0':'PROOF008_MRI_R_T0',#8
            'PROOF009_MRI_R_T0':'PROOF009_MRI_R_T0',#9
            'PROOF010_MRI_R_T0':'PROOF010_MRI_R_T0',#10
            'PROOF011_MRI_R_T0':'PROOF011_MRI_R_T0',#11
            'PROOF012_MRI_R_T0':'PROOF012_MRI_R_T0',#12
            'PROOF013_MRI_R_T0':'PROOF013_MRI_R_T0',#13
            'PROOF014_MRI_R_T0':'PROOF014_MRI_R_T0',#14
            'PROOF015_MRI_R_T0':'PROOF015_MRI_R_T0',#15
            'PROOF016_MRI_R_T0':'PROOF016_MRI_R_T0',#16
            'PROOF017_MRI_R_T0':'PROOF017_MRI_R_T0',#17
            'PROOF018_MRI_R_T0':'PROOF018_MRI_R_T0',#18
            'PROOF019_MRI_R_T0':'PROOF019_MRI_R_T0',#19
            'PROOF020_MRI_R_T0':'PROOF020_MRI_R_T0',#20
            'PROOF021_MRI_R_T0':'PROOF021_MRI_R_T0',#21
            'PROOF022_MRI_R_T0':'PROOF022_MRI_R_T0',#22
            'PROOF023_MRI_R_T0':'PROOF023_MRI_R_T0',#23
            'PROOF024_MRI_R_T0':'PROOF024_MRI_R_T0',#24
            'PROOF025_MRI_R_T0':'PROOF025_MRI_R_T0',#25
            'PROOF026_MRI_R_T0':'PROOF026_MRI_R_T0',#26
            'PROOF027_MRI_R_T0':'PROOF027_MRI_R_T0',#27
            'PROOF028_MRI_R_T0':'PROOF028_MRI_R_T0',#28
            'PROOF029_MRI_R_T0':'PROOF029_MRI_R_T0',#29
            'PROOF030_MRI_R_T0':'PROOF030_MRI_R_T0',#30
            'PROOF031_MRI_R_T0':'PROOF031_MRI_R_T0',#31
            'PROOF032_MRI_R_T0':'PROOF032_MRI_R_T0',#32
            'PROOF033_MRI_R_T0':'PROOF033_MRI_R_T0',#33
            'PROOF034_MRI_R_T0':'PROOF034_MRI_R_T0',#34
            'PROOF035_MRI_R_T0':'PROOF035_MRI_R_T0',#35
            'PROOF036_MRI_R_T0':'PROOF036_MRI_R_T0',#36
            'PROOF037_MRI_R_T0':'PROOF037_MRI_R_T0',
            'PROOF038_MRI_R_T0':'PROOF038_MRI_R_T0',
            'PROOF039_MRI_R_T0':'PROOF039_MRI_R_T0',
            'PROOF040_MRI_R_T0':'PROOF040_MRI_R_T0',
            'PROOF041_MRI_R_T0':'PROOF041_MRI_R_T0',
            'PROOF042_MRI_R_T0':'PROOF042_MRI_R_T0',
            'PROOF043_MRI_R_T0':'PROOF043_MRI_R_T0',
            'PROOF044_MRI_R_T0':'PROOF044_MRI_R_T0',
            'PROOF045_MRI_R_T0':'PROOF045_MRI_R_T0',
            'PROOF046_MRI_R_T0':'PROOF046_MRI_R_T0',
            'PROOF047_MRI_R_T0':'PROOF047_MRI_R_T0',
            'PROOF048_MRI_R_T0':'PROOF048_MRI_R_T0',
            'PROOF049_MRI_R_T0':'PROOF049_MRI_R_T0',
            'PROOF050_MRI_R_T0':'PROOF050_MRI_R_T0',
            'PROOF051_MRI_R_T0':'PROOF051_MRI_R_T0',
            'PROOF052_MRI_R_T0':'PROOF052_MRI_R_T0',
            'PROOF053_MRI_R_T0':'PROOF053_MRI_R_T0',
            'PROOF054_MRI_R_T0':'PROOF054_MRI_R_T0',
            'PROOF055_MRI_R_T0':'PROOF055_MRI_R_T0',
            'PROOF056_MRI_R_T0':'PROOF056_MRI_R_T0',
            'PROOF057_MRI_R_T0':'PROOF057_MRI_R_T0',
            'PROOF058_MRI_R_T0':'PROOF058_MRI_R_T0',
            'PROOF059_MRI_R_T0':'PROOF059_MRI_R_T0',
            'PROOF060_MRI_R_T0':'PROOF060_MRI_R_T0',
            'PROOF061_MRI_R_T0':'PROOF061_MRI_R_T0',
            'PROOF062_MRI_R_T0':'PROOF062_MRI_R_T0',
            'PROOF063_MRI_R_T0':'PROOF063_MRI_R_T0',
            'PROOF064_MRI_R_T0':'PROOF064_MRI_R_T0',
            'PROOF065_MRI_R_T0':'PROOF065_MRI_R_T0',
            'PROOF066_MRI_R_T0':'PROOF066_MRI_R_T0',
            'PROOF067_MRI_R_T0':'PROOF067_MRI_R_T0',
            'PROOF068_MRI_R_T0':'PROOF068_MRI_R_T0',
            'PROOF069_MRI_R_T0':'PROOF069_MRI_R_T0',
            'PROOF070_MRI_R_T0':'PROOF070_MRI_R_T0',
            'PROOF070_MRI_R_T0_2':'PROOF070_MRI_R_T0_2',
            'PROOF071_MRI_R_T0':'PROOF071_MRI_R_T0',
            'PROOF072_MRI_R_T0':'PROOF072_MRI_R_T0',
            'PROOF073_MRI_R_T0':'PROOF073_MRI_R_T0',
            'PROOF074_MRI_R_T0':'PROOF074_MRI_R_T0',
            'PROOF075_MRI_R_T0':'PROOF075_MRI_R_T0',
            'PROOF076_MRI_R_T0':'PROOF076_MRI_R_T0',
            'PROOF077_MRI_R_T0':'PROOF077_MRI_R_T0',
            'PROOF078_MRI_R_T0':'PROOF078_MRI_R_T0',
            'PROOF079_MRI_R_T0':'PROOF079_MRI_R_T0',
            'PROOF080_MRI_R_T0':'PROOF080_MRI_R_T0',
            'PROOF081_MRI_R_T0':'PROOF081_MRI_R_T0',
            'PROOF082_MRI_R_T0':'PROOF082_MRI_R_T0',
            'PROOF083_MRI_R_T0':'PROOF083_MRI_R_T0',
            'PROOF084_MRI_R_T0':'PROOF084_MRI_R_T0',
            'PROOF084_MRI_R_T0_2':'PROOF084_MRI_R_T0_2',
            'PROOF085_MRI_R_T0':'PROOF085_MRI_R_T0',
            'PROOF086_MRI_R_T0':'PROOF086_MRI_R_T0',
            'PROOF087_MRI_R_T0':'PROOF087_MRI_R_T0',
            'PROOF088_MRI_R_T0':'PROOF088_MRI_R_T0',
            'PROOF089_MRI_R_T0':'PROOF089_MRI_R_T0',
            'PROOF090_MRI_R_T0':'PROOF090_MRI_R_T0',
            'PROOF090_MRI_R_T0_2':'PROOF090_MRI_R_T0_2',
            'PROOF091_MRI_R_T0':'PROOF091_MRI_R_T0',
            'PROOF092_MRI_R_T0':'PROOF092_MRI_R_T0',
            'PROOF093_MRI_R_T0':'PROOF093_MRI_R_T0',
            'PROOF094_MRI_R_T0':'PROOF094_MRI_R_T0',
            'PROOF095_MRI_R_T0':'PROOF095_MRI_R_T0',
            'PROOF096_MRI_R_T0':'PROOF096_MRI_R_T0',
            'PROOF097_MRI_R_T0':'PROOF097_MRI_R_T0',
            'PROOF098_MRI_R_T0':'PROOF098_MRI_R_T0',
            'PROOF099_MRI_R_T0':'PROOF099_MRI_R_T0',
            'PROOF100_MRI_R_T0':'PROOF100_MRI_R_T0',
            'PROOF101_MRI_R_T0':'PROOF101_MRI_R_T0',
            'PROOF102_MRI_R_T0':'PROOF102_MRI_R_T0',
            'PROOF103_MRI_R_T0':'PROOF103_MRI_R_T0',
            'PROOF104_MRI_R_T0':'PROOF104_MRI_R_T0',
            'PROOF105_MRI_R_T0':'PROOF105_MRI_R_T0',
            'PROOF106_MRI_R_T0':'PROOF106_MRI_R_T0',
            'PROOF107_MRI_R_T0':'PROOF107_MRI_R_T0',
            'PROOF108_MRI_R_T0':'PROOF108_MRI_R_T0',
            'PROOF109_MRI_R_T0':'PROOF109_MRI_R_T0',
            'PROOF111_MRI_R_T0':'PROOF111_MRI_R_T0',
            'PROOF112_MRI_R_T0':'PROOF112_MRI_R_T0',
            'PROOF113_MRI_R_T0':'PROOF113_MRI_R_T0',
            'PROOF114_MRI_R_T0':'PROOF114_MRI_R_T0',
            'PROOF115_MRI_R_T0':'PROOF115_MRI_R_T0',
            'PROOF116_MRI_R_T0':'PROOF116_MRI_R_T0',
            'PROOF117_MRI_R_T0':'PROOF117_MRI_R_T0',
            'PROOF118_MRI_R_T0':'PROOF118_MRI_R_T0',
            'PROOF119_MRI_R_T0':'PROOF119_MRI_R_T0',
            'PROOF120_MRI_R_T0':'PROOF120_MRI_R_T0',
            'PROOF121_MRI_R_T0':'PROOF121_MRI_R_T0',
            'PROOF122_MRI_R_T0':'PROOF122_MRI_R_T0',
            'PROOF123_MRI_R_T0':'PROOF123_MRI_R_T0',
            'PROOF125_MRI_R_T0':'PROOF125_MRI_R_T0',
            'PROOF126_MRI_R_T0':'PROOF126_MRI_R_T0',
            'PROOF127_MRI_R_T0':'PROOF127_MRI_R_T0',
            'PROOF128_MRI_R_T0':'PROOF128_MRI_R_T0',
            'PROOF129_MRI_R_T0':'PROOF129_MRI_R_T0',
            'PROOF130_MRI_R_T0':'PROOF130_MRI_R_T0',
            'PROOF131_MRI_R_T0':'PROOF131_MRI_R_T0',
            'PROOF132_MRI_R_T0':'PROOF132_MRI_R_T0',
            'PROOF133_MRI_R_T0':'PROOF133_MRI_R_T0',
            'PROOF134_MRI_R_T0':'PROOF134_MRI_R_T0',
            'PROOF135_MRI_R_T0':'PROOF135_MRI_R_T0',
            'PROOF136_MRI_R_T0':'PROOF136_MRI_R_T0',
            'PROOF137_MRI_R_T0':'PROOF137_MRI_R_T0',
            'PROOF138_MRI_R_T0':'PROOF138_MRI_R_T0',
            'PROOF139_MRI_R_T0':'PROOF139_MRI_R_T0',
            'PROOF140_MRI_R_T0':'PROOF140_MRI_R_T0',
            'PROOF141_MRI_R_T0':'PROOF141_MRI_R_T0',
            'PROOF142_MRI_R_T0':'PROOF142_MRI_R_T0',
            'PROOF143_MRI_R_T0':'PROOF143_MRI_R_T0',
            'PROOF144_MRI_R_T0':'PROOF144_MRI_R_T0',
            'PROOF145_MRI_R_T0':'PROOF145_MRI_R_T0',
            'PROOF146_MRI_R_T0':'PROOF146_MRI_R_T0',
            'PROOF147_MRI_R_T0':'PROOF147_MRI_R_T0',
            'PROOF148_MRI_R_T0':'PROOF148_MRI_R_T0',
            'PROOF149_MRI_R_T0':'PROOF149_MRI_R_T0',
            'PROOF150_MRI_R_T0':'PROOF150_MRI_R_T0',
            'PROOF152_MRI_R_T0':'PROOF152_MRI_R_T0',
            'PROOF153_MRI_R_T0':'PROOF153_MRI_R_T0',
            'PROOF154_MRI_R_T0':'PROOF154_MRI_R_T0',
            'PROOF155_MRI_R_T0':'PROOF155_MRI_R_T0',
            'PROOF156_MRI_R_T0':'PROOF156_MRI_R_T0',
            'PROOF157_MRI_R_T0':'PROOF157_MRI_R_T0',
            'PROOF158_MRI_R_T0':'PROOF158_MRI_R_T0',
            'PROOF159_MRI_R_T0':'PROOF159_MRI_R_T0',
            'PROOF160_MRI_R_T0':'PROOF160_MRI_R_T0',
            'PROOF161_MRI_R_T0':'PROOF161_MRI_R_T0',
            'PROOF162_MRI_R_T0':'PROOF162_MRI_R_T0',
            'PROOF163_MRI_R_T0':'PROOF163_MRI_R_T0',
            'PROOF164_MRI_R_T0':'PROOF164_MRI_R_T0',
            'PROOF165_MRI_R_T0':'PROOF165_MRI_R_T0',
            'PROOF166_MRI_R_T0':'PROOF166_MRI_R_T0',
            'PROOF167_MRI_R_T0':'PROOF167_MRI_R_T0',
            'PROOF168_MRI_R_T0':'PROOF168_MRI_R_T0',
            'PROOF169_MRI_R_T0':'PROOF169_MRI_R_T0',
            'PROOF170_MRI_R_T0':'PROOF170_MRI_R_T0',
            'PROOF171_MRI_R_T0':'PROOF171_MRI_R_T0',
            'PROOF172_MRI_R_T0':'PROOF172_MRI_R_T0',
            'PROOF173_MRI_R_T0':'PROOF173_MRI_R_T0',
            'PROOF174_MRI_R_T0':'PROOF174_MRI_R_T0',
            'PROOF175_MRI_R_T0':'PROOF175_MRI_R_T0',
            'PROOF176_MRI_R_T0':'PROOF176_MRI_R_T0',
            'PROOF177_MRI_R_T0':'PROOF177_MRI_R_T0',
            'PROOF178_MRI_R_T0':'PROOF178_MRI_R_T0',
            'PROOF179_MRI_R_T0':'PROOF179_MRI_R_T0',
            'PROOF180_MRI_R_T0':'PROOF180_MRI_R_T0',
            'PROOF181_MRI_R_T0':'PROOF181_MRI_R_T0',
            'PROOF182_MRI_R_T0':'PROOF182_MRI_R_T0',
            'PROOF183_MRI_R_T0':'PROOF183_MRI_R_T0',
            'PROOF184_MRI_R_T0':'PROOF184_MRI_R_T0',
            'PROOF185_MRI_R_T0':'PROOF185_MRI_R_T0',
            'PROOF186_MRI_R_T0':'PROOF186_MRI_R_T0',
            'PROOF187_MRI_R_T0':'PROOF187_MRI_R_T0',
            'PROOF188_MRI_R_T0':'PROOF188_MRI_R_T0',
            'PROOF189_MRI_R_T0':'PROOF189_MRI_R_T0',
            'PROOF190_MRI_R_T0':'PROOF190_MRI_R_T0',
            'PROOF191_MRI_R_T0':'PROOF191_MRI_R_T0',
            'PROOF192_MRI_R_T0':'PROOF192_MRI_R_T0',
            'PROOF193_MRI_R_T0':'PROOF193_MRI_R_T0',
            'PROOF194_MRI_R_T0':'PROOF194_MRI_R_T0',
            'PROOF195_MRI_R_T0':'PROOF195_MRI_R_T0',
            'PROOF196_MRI_R_T0':'PROOF196_MRI_R_T0',
            'PROOF197_MRI_R_T0':'PROOF197_MRI_R_T0',
            'PROOF198_MRI_R_T0':'PROOF198_MRI_R_T0',
            'PROOF199_MRI_R_T0':'PROOF199_MRI_R_T0',
            'PROOF200_MRI_R_T0':'PROOF200_MRI_R_T0',
            'PROOF201_MRI_R_T0':'PROOF201_MRI_R_T0',
            'PROOF202_MRI_R_T0':'PROOF202_MRI_R_T0',
            'PROOF203_MRI_R_T0':'PROOF203_MRI_R_T0',
            'PROOF204_MRI_R_T0':'PROOF204_MRI_R_T0',
            'PROOF205_MRI_R_T0':'PROOF205_MRI_R_T0',
            'PROOF206_MRI_R_T0':'PROOF206_MRI_R_T0',
            'PROOF207_MRI_R_T0':'PROOF207_MRI_R_T0',
            'PROOF208_MRI_R_T0':'PROOF208_MRI_R_T0',
            'PROOF209_MRI_R_T0':'PROOF209_MRI_R_T0',
            'PROOF210_MRI_R_T0':'PROOF210_MRI_R_T0',
            'PROOF211_MRI_R_T0':'PROOF211_MRI_R_T0',
            'PROOF212_MRI_R_T0':'PROOF212_MRI_R_T0',
            'PROOF212_MRI_R_T0_2':'PROOF212_MRI_R_T0_2',
            'PROOF213_MRI_R_T0':'PROOF213_MRI_R_T0',
            'PROOF214_MRI_R_T0':'PROOF214_MRI_R_T0',
            'PROOF215_MRI_R_T0':'PROOF215_MRI_R_T0',
            'PROOF216_MRI_R_T0':'PROOF216_MRI_R_T0',
            'PROOF217_MRI_R_T0':'PROOF217_MRI_R_T0',
            'PROOF218_MRI_R_T0':'PROOF218_MRI_R_T0',
            'PROOF219_MRI_R_T0':'PROOF219_MRI_R_T0',
            'PROOF220_MRI_R_T0':'PROOF220_MRI_R_T0',
            'PROOF221_MRI_R_T0':'PROOF221_MRI_R_T0',
            'PROOF222_MRI_R_T0':'PROOF222_MRI_R_T0',
            'PROOF223_MRI_R_T0':'PROOF223_MRI_R_T0',
            'PROOF224_MRI_R_T0':'PROOF224_MRI_R_T0',
            'PROOF225_MRI_R_T0':'PROOF225_MRI_R_T0',
            'PROOF226_MRI_R_T0':'PROOF226_MRI_R_T0',
            'PROOF227_MRI_R_T0':'PROOF227_MRI_R_T0',
            'PROOF228_MRI_R_T0':'PROOF228_MRI_R_T0',
            'PROOF229_MRI_R_T0':'PROOF229_MRI_R_T0',
            'PROOF230_MRI_R_T0':'PROOF230_MRI_R_T0',
            'PROOF231_MRI_R_T0':'PROOF231_MRI_R_T0',
            'PROOF232_MRI_R_T0':'PROOF232_MRI_R_T0',
            'PROOF233_MRI_R_T0':'PROOF233_MRI_R_T0',
            'PROOF234_MRI_R_T0':'PROOF234_MRI_R_T0',
            'PROOF235_MRI_R_T0':'PROOF235_MRI_R_T0',
            'PROOF236_MRI_R_T0':'PROOF236_MRI_R_T0',
            'PROOF237_MRI_R_T0':'PROOF237_MRI_R_T0',
            'PROOF238_MRI_R_T0':'PROOF238_MRI_R_T0',
            'PROOF239_MRI_R_T0':'PROOF239_MRI_R_T0',
            'PROOF240_MRI_R_T0':'PROOF240_MRI_R_T0',
            'PROOF241_MRI_R_T0':'PROOF241_MRI_R_T0',
            'PROOF242_MRI_R_T0':'PROOF242_MRI_R_T0',
            'PROOF243_MRI_R_T0':'PROOF243_MRI_R_T0',
            'PROOF244_MRI_R_T0':'PROOF244_MRI_R_T0',
            'PROOF245_MRI_R_T0':'PROOF245_MRI_R_T0',
            'PROOF246_MRI_R_T0':'PROOF246_MRI_R_T0',
            'PROOF247_MRI_R_T0':'PROOF247_MRI_R_T0',
            'PROOF248_MRI_R_T0':'PROOF248_MRI_R_T0',
            'PROOF249_MRI_R_T0':'PROOF249_MRI_R_T0',
            'PROOF250_MRI_R_T0':'PROOF250_MRI_R_T0',
            'PROOF251_MRI_R_T0':'PROOF251_MRI_R_T0',
            'PROOF253_MRI_R_T0':'PROOF253_MRI_R_T0',
            'PROOF254_MRI_R_T0':'PROOF254_MRI_R_T0',
            'PROOF255_MRI_R_T0':'PROOF255_MRI_R_T0',
            'PROOF256_MRI_R_T0':'PROOF256_MRI_R_T0',
            'PROOF257_MRI_R_T0':'PROOF257_MRI_R_T0',
            'PROOF258_MRI_R_T0':'PROOF258_MRI_R_T0',
            'PROOF259_MRI_R_T0':'PROOF259_MRI_R_T0',
            'PROOF260_MRI_R_T0':'PROOF260_MRI_R_T0',
            'PROOF261_MRI_R_T0':'PROOF261_MRI_R_T0',
            'PROOF262_MRI_R_T0':'PROOF262_MRI_R_T0',
            'PROOF263_MRI_R_T0':'PROOF263_MRI_R_T0',
            'PROOF264_MRI_R_T0':'PROOF264_MRI_R_T0',
            'PROOF265_MRI_R_T0':'PROOF265_MRI_R_T0',
            'PROOF266_MRI_R_T0':'PROOF266_MRI_R_T0',
            'PROOF267_MRI_R_T0':'PROOF267_MRI_R_T0',
            'PROOF268_MRI_R_T0':'PROOF268_MRI_R_T0',
            'PROOF269_MRI_R_T0':'PROOF269_MRI_R_T0',
            'PROOF270_MRI_R_T0':'PROOF270_MRI_R_T0',
            'PROOF271_MRI_R_T0':'PROOF271_MRI_R_T0',
            'PROOF272_MRI_R_T0':'PROOF272_MRI_R_T0',
            'PROOF273_MRI_R_T0':'PROOF273_MRI_R_T0',
            'PROOF274_MRI_R_T0':'PROOF274_MRI_R_T0',
            'PROOF275_MRI_R_T0':'PROOF275_MRI_R_T0',
            'PROOF276_MRI_R_T0':'PROOF276_MRI_R_T0',
            'PROOF277_MRI_R_T0':'PROOF277_MRI_R_T0',
            'PROOF278_MRI_R_T0':'PROOF278_MRI_R_T0',
            'PROOF279_MRI_R_T0':'PROOF279_MRI_R_T0',
            'PROOF280_MRI_R_T0':'PROOF280_MRI_R_T0',
            'PROOF281_MRI_R_T0':'PROOF281_MRI_R_T0',
            'PROOF282_MRI_R_T0':'PROOF282_MRI_R_T0',
            'PROOF283_MRI_R_T0':'PROOF283_MRI_R_T0',
            'PROOF284_MRI_R_T0':'PROOF284_MRI_R_T0',
            'PROOF285_MRI_R_T0':'PROOF285_MRI_R_T0',
            'PROOF286_MRI_R_T0':'PROOF286_MRI_R_T0',
            'PROOF287_MRI_R_T0':'PROOF287_MRI_R_T0',
            'PROOF288_MRI_R_T0':'PROOF288_MRI_R_T0',
            'PROOF289_MRI_R_T0':'PROOF289_MRI_R_T0',
            'PROOF290_MRI_R_T0':'PROOF290_MRI_R_T0',
            'PROOF291_MRI_R_T0':'PROOF291_MRI_R_T0',
            'PROOF292_MRI_R_T0':'PROOF292_MRI_R_T0',
            'PROOF293_MRI_R_T0':'PROOF293_MRI_R_T0',
            'PROOF294_MRI_R_T0':'PROOF294_MRI_R_T0',
            'PROOF295_MRI_R_T0':'PROOF295_MRI_R_T0',
            'PROOF296_MRI_R_T0':'PROOF296_MRI_R_T0',
            'PROOF297_MRI_R_T0':'PROOF297_MRI_R_T0',
            'PROOF300_MRI_R_T0':'PROOF300_MRI_R_T0',
            'PROOF301_MRI_R_T0':'PROOF301_MRI_R_T0',
            'PROOF302_MRI_R_T0':'PROOF302_MRI_R_T0',
            'PROOF303_MRI_R_T0':'PROOF303_MRI_R_T0',
            'PROOF304_MRI_R_T0':'PROOF304_MRI_R_T0',
            'PROOF305_MRI_R_T0':'PROOF305_MRI_R_T0',
            'PROOF306_MRI_R_T0':'PROOF306_MRI_R_T0',
            'PROOF307_MRI_R_T0':'PROOF307_MRI_R_T0',
            'PROOF308_MRI_R_T0':'PROOF308_MRI_R_T0',
            'PROOF309_MRI_R_T0':'PROOF309_MRI_R_T0',
            'PROOF310_MRI_R_T0':'PROOF310_MRI_R_T0',
            'PROOF311_MRI_R_T0':'PROOF311_MRI_R_T0',
            'PROOF312_MRI_R_T0':'PROOF312_MRI_R_T0',
            'PROOF314_MRI_R_T0':'PROOF314_MRI_R_T0',
            'PROOF315_MRI_R_T0':'PROOF315_MRI_R_T0',
            'PROOF316_MRI_R_T0':'PROOF316_MRI_R_T0',
            'PROOF317_MRI_R_T0':'PROOF317_MRI_R_T0',
            'PROOF318_MRI_R_T0':'PROOF318_MRI_R_T0',
            'PROOF319_MRI_R_T0':'PROOF319_MRI_R_T0',
            'PROOF320_MRI_R_T0':'PROOF320_MRI_R_T0',
            'PROOF321_MRI_R_T0':'PROOF321_MRI_R_T0',
            'PROOF322_MRI_R_T0':'PROOF322_MRI_R_T0',
            'PROOF323_MRI_R_T0':'PROOF323_MRI_R_T0',
            'PROOF324_MRI_R_T0':'PROOF324_MRI_R_T0',
            'PROOF325_MRI_R_T0':'PROOF325_MRI_R_T0',
            'PROOF326_MRI_R_T0':'PROOF326_MRI_R_T0',
            'PROOF327_MRI_R_T0':'PROOF327_MRI_R_T0',
            'PROOF328_MRI_R_T0':'PROOF328_MRI_R_T0',
            'PROOF329_MRI_R_T0':'PROOF329_MRI_R_T0',
            'PROOF330_MRI_R_T0':'PROOF330_MRI_R_T0',
            'PROOF331_MRI_R_T0':'PROOF331_MRI_R_T0',
            'PROOF332_MRI_R_T0':'PROOF332_MRI_R_T0',
            'PROOF333_MRI_R_T0':'PROOF333_MRI_R_T0',
            'PROOF334_MRI_R_T0':'PROOF334_MRI_R_T0',
            'PROOF336_MRI_R_T0':'PROOF336_MRI_R_T0',
            'PROOF337_MRI_R_T0':'PROOF337_MRI_R_T0',
            'PROOF338_MRI_R_T0':'PROOF338_MRI_R_T0',
            'PROOF339_MRI_R_T0':'PROOF339_MRI_R_T0',
            'PROOF340_MRI_R_T0':'PROOF340_MRI_R_T0',
            'PROOF341_MRI_R_T0':'PROOF341_MRI_R_T0',
            'PROOF343_MRI_R_T0':'PROOF343_MRI_R_T0',
            'PROOF344_MRI_R_T0':'PROOF344_MRI_R_T0',
            'PROOF345_MRI_R_T0':'PROOF345_MRI_R_T0',
            'PROOF346_MRI_R_T0':'PROOF346_MRI_R_T0',
            'PROOF347_MRI_R_T0':'PROOF347_MRI_R_T0',
            'PROOF348_MRI_R_T0':'PROOF348_MRI_R_T0',
            'PROOF349_MRI_R_T0':'PROOF349_MRI_R_T0',
            'PROOF350_MRI_R_T0':'PROOF350_MRI_R_T0',
            'PROOF351_MRI_R_T0':'PROOF351_MRI_R_T0',
            'PROOF352_MRI_R_T0':'PROOF352_MRI_R_T0',
            'PROOF353_MRI_R_T0':'PROOF353_MRI_R_T0',
            'PROOF354_MRI_R_T0':'PROOF354_MRI_R_T0',
            'PROOF356_MRI_R_T0':'PROOF356_MRI_R_T0',
            'PROOF357_MRI_R_T0':'PROOF357_MRI_R_T0',
            'PROOF358_MRI_R_T0':'PROOF358_MRI_R_T0',
            'PROOF359_MRI_R_T0':'PROOF359_MRI_R_T0',
            'PROOF360_MRI_R_T0':'PROOF360_MRI_R_T0',
            'PROOF362_MRI_R_T0':'PROOF362_MRI_R_T0',
            'PROOF363_MRI_R_T0':'PROOF363_MRI_R_T0',
            'PROOF364_MRI_R_T0':'PROOF364_MRI_R_T0',
            'PROOF365_MRI_R_T0':'PROOF365_MRI_R_T0',
            'PROOF366_MRI_R_T0':'PROOF366_MRI_R_T0',
            'PROOF367_MRI_R_T0':'PROOF367_MRI_R_T0',
            'PROOF368_MRI_R_T0':'PROOF368_MRI_R_T0',
            'PROOF369_MRI_R_T0':'PROOF369_MRI_R_T0',
            'PROOF370_MRI_R_T0':'PROOF370_MRI_R_T0',
            'PROOF371_MRI_R_T0':'PROOF371_MRI_R_T0',
            'PROOF372_MRI_R_T0':'PROOF372_MRI_R_T0',
            'PROOF373_MRI_R_T0':'PROOF373_MRI_R_T0',
            'PROOF374_MRI_R_T0':'PROOF374_MRI_R_T0',
            'PROOF375_MRI_R_T0':'PROOF375_MRI_R_T0',
            'PROOF376_MRI_R_T0':'PROOF376_MRI_R_T0',
            'PROOF377_MRI_R_T0':'PROOF377_MRI_R_T0',
            'PROOF378_MRI_R_T0':'PROOF378_MRI_R_T0',
            'PROOF379_MRI_R_T0':'PROOF379_MRI_R_T0',
            'PROOF380_MRI_R_T0':'PROOF380_MRI_R_T0',
            'PROOF381_MRI_R_T0':'PROOF381_MRI_R_T0',
            'PROOF382_MRI_R_T0':'PROOF382_MRI_R_T0',
            'PROOF383_MRI_R_T0':'PROOF383_MRI_R_T0',
            'PROOF384_MRI_R_T0':'PROOF384_MRI_R_T0',
            'PROOF385_MRI_R_T0':'PROOF385_MRI_R_T0',
            'PROOF386_MRI_R_T0':'PROOF386_MRI_R_T0',
            'PROOF387_MRI_R_T0':'PROOF387_MRI_R_T0',
            'PROOF388_MRI_R_T0':'PROOF388_MRI_R_T0',
            'PROOF389_MRI_R_T0':'PROOF389_MRI_R_T0',
            'PROOF390_MRI_R_T0':'PROOF390_MRI_R_T0',
            'PROOF391_MRI_R_T0':'PROOF391_MRI_R_T0',
            'PROOF392_MRI_R_T0':'PROOF392_MRI_R_T0',
            'PROOF393_MRI_R_T0':'PROOF393_MRI_R_T0',
            'PROOF394_MRI_R_T0':'PROOF394_MRI_R_T0',
            'PROOF395_MRI_R_T0':'PROOF395_MRI_R_T0',
            'PROOF396_MRI_R_T0':'PROOF396_MRI_R_T0',
            'PROOF397_MRI_R_T0':'PROOF397_MRI_R_T0',
            'PROOF398_MRI_R_T0':'PROOF398_MRI_R_T0',
            'PROOF399_MRI_R_T0':'PROOF399_MRI_R_T0',
            'PROOF400_MRI_R_T0':'PROOF400_MRI_R_T0',
            'PROOF401_MRI_R_T0':'PROOF401_MRI_R_T0',
            'PROOF402_MRI_R_T0':'PROOF402_MRI_R_T0',
            'PROOF403_MRI_R_T0':'PROOF403_MRI_R_T0',
            'PROOF404_MRI_R_T0':'PROOF404_MRI_R_T0',
            'PROOF405_MRI_R_T0':'PROOF405_MRI_R_T0',
            'PROOF406_MRI_R_T0':'PROOF406_MRI_R_T0',
            'PROOF407_MRI_R_T0':'PROOF407_MRI_R_T0',
        },
        'range_mask_target':{'range_mask_T0':'vfs://scratch/data/fastr-data/OsteoValResults/PROOF004_MRI_L_T0_prWATSc3Dli_rangemask.nii.gz'},
        'range_mask_atlas':{'norm_mask_atlas_9003406_20060322':'vfs://fastr_data/OAI_KneeMRI_testdata/Nifti_gz_IMS/9003406_20060322_SAG_3D_DESS_LEFT_016610899303_ims_rangemask.nii.gz'},
        'classifier': ['vfs://fastr_data/seg/class/PROOF_RIGHT_classifier_all.clf']
    }
    
    
    network = create_network()
    print network.draw_network(img_format='svg', draw_dimension=True)
    fastr.log.info('^^^^^^^^^^^^^ Starting execution client.')
    
    network.execute(sourcedata_part, sinkdata,cluster_queue="day,week,month",tmpdir=staging_dir)
    
    # Empty staging directory
        for filename in os.listdir(staging_dir):
            filepath = os.path.join(staging_dir, filename)
            try:
                shutil.rmtree(filepath)
            except OSError:
                os.remove(filepath)
        numK = numK + sizePart

if __name__ == '__main__':
    main()

