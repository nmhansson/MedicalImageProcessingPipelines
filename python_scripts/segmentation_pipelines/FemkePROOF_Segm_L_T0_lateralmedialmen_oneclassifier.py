#!/usr/bin/env python

# Copyright 2011-2014 Biomedical Imaging Group Rotterdam, Departments of
# Medical Informatics and Radiology, Erasmus MC, Rotterdam, The Netherlands
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

import time
from itertools import *
import os
import shutil
from sourcedata_L_T0_lateralmedialmen import sourcedata

def main():

    # Scales for the guassian scale space filtering
    scales = (1.0, 1.6, 4.)
    # Number of classes in the segmentation problem
    nrclasses = 2
    radius = [30.0]
    # Registration parameter files to use
    registration_parameters = ('vfs://fastr_data/tissue_segmentation/constant/par_affine.txt', 'vfs://fastr_data/tissue_segmentation/constant/par_bspline5mm.txt')

    registration_parameters_generate_mask = ('vfs://fastr_data/constant/par_similarity.txt',)

    staging_dir = '/scratch/mhansson/staging/lateralmedialMen_LT0'
    try:
        shutil.rmtree(staging_dir)
    except:
        pass

    session_id_keys = sorted(sourcedata['session_ids'].keys())

    numK = 0
    sizePart = 10

    while numK < len(sourcedata['session_ids']):
        sourcedata_part = {}
        sourcedata_part['atlas_img'] = sourcedata['atlas_img']
        sourcedata_part['atlas_labels'] = sourcedata['atlas_labels']
        sourcedata_part['atlas_ROI'] = sourcedata['atlas_ROI']

        sourcedata_part['classifier'] = sourcedata['classifier']
        sourcedata_part['session_ids'] = {}
        sourcedata_part['target_nii'] = {}
        sourcedata_part['target_ROI'] = {}

        for i in islice(count(), numK, numK+sizePart):
            try:
                sourcedata_part['target_nii'][session_id_keys[i]] = sourcedata['target_nii'][session_id_keys[i]]
                sourcedata_part['session_ids'][session_id_keys[i]] = sourcedata['session_ids'][session_id_keys[i]]
                sourcedata_part['target_ROI'][session_id_keys[i]] = sourcedata['target_ROI'][session_id_keys[i]]
            except:
                pass
        # Setup Network and sources
        network = fastr.Network(id_="LATERALMEDIAL_MEN_LT0")

        target_nii = network.create_source('NiftiImageFileCompressed', id_='target_nii', sourcegroup='target')
        session_id = network.create_source('String',id_='session_ids')

        source_targetROI = network.create_source(datatype=fastr.typelist['ITKImageFile'], id_='target_ROI',sourcegroup='target')

        source_atlasImages = network.create_source('NiftiImageFileCompressed', id_='atlas_img', sourcegroup='atlas')
        source_atlasLabels = network.create_source('NiftiImageFileCompressed', id_='atlas_labels', sourcegroup='atlas')
        source_atlasROI = network.create_source(datatype=fastr.typelist['ITKImageFile'], id_='atlas_ROI',sourcegroup='atlas')
         
        threshold_medialmen = network.create_node('FSLMaths', id_='threshold_medialmen', memory='15G')
        threshold_medialmen.inputs['image1'] = source_atlasLabels.output
        threshold_medialmen.inputs['operator1'] = ['-thr']
        threshold_medialmen.inputs['operator1_string'] = [1.5]

        binarize_medialmen = network.create_node('FSLMaths', id_='binarize_medialmen')
        binarize_medialmen.inputs['image1'] = threshold_medialmen.outputs['output_image']
        binarize_medialmen.inputs['operator1'] = ['-bin']
         
        threshold_lateralmen = network.create_node('FSLMaths', id_='threshold_lateralmen', memory='15G')
        threshold_lateralmen.inputs['image1'] = source_atlasLabels.output
        threshold_lateralmen.inputs['operator1'] = ['-uthr']
        threshold_lateralmen.inputs['operator1_string'] = [1.5]

        classifier = network.create_source('SKLearnClassifierFile', id_='classifier')

        # Apply n4 non-uniformity correction
        n4_atlas_im = network.create_node('N4', id_='n4_atlas', memory='15G')
        n4_atlas_im.inputs['image'] = source_atlasImages.output
        #n4_atlas_im.inputs['mask'] = source_normmask_atlas.output
        n4_atlas_im.inputs['shrink_factor'] = 4,
        n4_atlas_im.inputs['converge'] = '[150,00001]',
        n4_atlas_im.inputs['bspline_fitting'] = '[50]',

        n4_target_im = network.create_node('N4', id_='n4_target', memory='15G')
        n4_target_im.inputs['image'] = target_nii.output
        #n4_target_im.inputs['mask'] = source_normmask_target.output
        n4_target_im.inputs['shrink_factor'] = 4,
        n4_target_im.inputs['converge'] = '[150,00001]',
        n4_target_im.inputs['bspline_fitting'] = '[50]',

        # Range match images
        rama_atlas_im = network.create_node('RangeMatch', id_='rama_atlas',memory='15G')
        rama_atlas_im.inputs['image'] = n4_atlas_im.outputs['image']
        rama_atlas_im.inputs['mask'] = source_atlasROI.output

        rama_target_im = network.create_node('RangeMatch', id_='rama_target',memory='15G')
        rama_target_im.inputs['image'] = n4_target_im.outputs['image']
        rama_target_im.inputs['mask'] = source_targetROI.output


        # Create filter image for T1
        scalespacefilter = network.create_node('GaussianScaleSpace', id_='scalespacefilter', memory='15G')
        scalespacefilter.inputs['image'] = rama_target_im.outputs['image']
        scalespacefilter.inputs['scales'] = scales

        # Apply classifier
        n_cores = 8
        applyclass = network.create_node('ApplyClassifier', id_='applyclass', memory='6G',cores=n_cores)
        applyclass.inputs['image'] = scalespacefilter.outputs['image']
        applyclass.inputs['mask'] = source_targetROI.output
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
        reg_t1 = network.create_node(fastr.toollist['Elastix','4.8'], id_='reg_t1', memory='6G')
        reg_t1.inputs['threads'] = [1]
        reg_t1.inputs['fixed_image'] = rama_target_im.outputs['image']
        reg_t1.inputs['moving_image'] = rama_atlas_im.outputs['image']
        reg_t1.inputs['moving_image'].input_group = 'atlas'
        reg_t1.inputs['parameters'] = registration_parameters
        reg_t1.inputs['fixed_mask'] = source_targetROI.output
        reg_t1.inputs['moving_mask'] = source_atlasROI.output
        reg_t1.inputs['moving_mask'].input_group = 'atlas'

        trans_label_medial = network.create_node('Transformix', id_='trans_label_medial')
        trans_label_medial.inputs['threads'] = [1]
        trans_label_medial.inputs['image'] = binarize_medialmen.outputs['output_image']
        trans_label_medial.inputs['transform'] = reg_t1.outputs['transform'][-1]
        
        trans_label_lateral = network.create_node('Transformix', id_='trans_label_lateral')
        trans_label_lateral.inputs['threads'] = [1]
        trans_label_lateral.inputs['image'] = threshold_lateralmen.outputs['output_image']
        trans_label_lateral.inputs['transform'] = reg_t1.outputs['transform'][-1]
         
        combine_label_medial = network.create_node('PxCombineSegmentations', id_='combine_label_medial')
        link_combine_medial = network.create_link(trans_label_medial.outputs['image'], combine_label_medial.inputs['images'])
        link_combine_medial.collapse = 'atlas'
        combine_label_medial.inputs['method'] = ['VOTE']
        combine_label_medial.inputs['number_of_classes'] = [nrclasses]

        combine_label_lateral = network.create_node('PxCombineSegmentations', id_='combine_label_lateral')
        link_combine_lateral = network.create_link(trans_label_lateral.outputs['image'], combine_label_lateral.inputs['images'])
        link_combine_lateral.collapse = 'atlas'
        combine_label_lateral.inputs['method'] = ['VOTE']
        combine_label_lateral.inputs['number_of_classes'] = [nrclasses]

        # Combine medial atlas + classifier
        times_medial = network.create_node('PxBinaryImageOperator', id_='times_medial')
        times_medial.inputs['images'] = mult.outputs['image']
        times_medial.inputs['operator'] = ['TIMES']
        times_medial_link_1 = times_medial.inputs['images'].append(combine_label_medial.outputs['soft_segment'])
        times_medial_link_1.expand = True

        times_lateral = network.create_node('PxBinaryImageOperator', id_='times_lateral')
        times_lateral.inputs['images'] = mult.outputs['image']
        times_lateral.inputs['operator'] = ['TIMES']
        times_lateral_link_1 = times_lateral.inputs['images'].append(combine_label_lateral.outputs['soft_segment'])
        times_lateral_link_1.expand = True
        
        # Tool for picking the correct map based on the max prob
        argmax_medial = network.create_node('ArgMaxImage', id_='argmax_medial', memory='10G')
        link_medial = network.create_link(times_medial.outputs['image'], argmax_medial.inputs['image'])
        link_medial.collapse = 1

        argmax_lateral = network.create_node('ArgMaxImage', id_='argmax_lateral', memory='10G')
        link_lateral = network.create_link(times_lateral.outputs['image'], argmax_lateral.inputs['image'])
        link_lateral.collapse = 1

        # compute segmentation volume
        count_nonzero_medial = network.create_node(fastr.toollist['GetQuantitativeMeasures','0.2'], id_='count_nonzero_medial')
        count_nonzero_medial.inputs['label'] = argmax_medial.outputs['image']
        count_nonzero_medial.inputs['volume'] = ['mm^3']

        count_nonzero_lateral = network.create_node(fastr.toollist['GetQuantitativeMeasures','0.2'], id_='count_nonzero_lateral')
        count_nonzero_lateral.inputs['label'] = argmax_lateral.outputs['image']
        count_nonzero_lateral.inputs['volume'] = ['mm^3']

        # produce qib xml file

        convert_to_qib_medial = network.create_node(fastr.toollist['ConvertCsvToQibSessionMH','0.3'], id_='convert_to_qib_medial')
        convert_to_qib_medial.inputs['tool'] = ('MultiAtlas Appearance Model Segmentation with Volume Calculation'),
        convert_to_qib_medial.inputs['tool_version'] = ('0.1'),
        convert_to_qib_medial.inputs['description'] = ('MultiAtlas Appearance Model Segmentation'),
        convert_to_qib_medial.inputs['begin_date'] = (time.strftime("%Y-%m-%dT%H:%M")),
        convert_to_qib_medial.inputs['processing_site'] = ('Erasmus MC'),
        convert_to_qib_medial.inputs['paper_title'] = ('Automated brain structure segmentation based on atlas registration and appearance models'),
        convert_to_qib_medial.inputs['paper_link'] = ('/onlinelibrary.wiley.com/doi/10.1002/hbm.22522/full'),
        convert_to_qib_medial.inputs['paper_notes'] = ('Method is a variant of version described in paper (no MRF model for spatial coherence'),
        convert_to_qib_medial.inputs['categories'] = ('Femoral Cartilage'),
        convert_to_qib_medial.inputs['ontologyname'] = ('Uberon'),
        convert_to_qib_medial.inputs['ontologyIRI'] = ('NA'),
        convert_to_qib_medial.inputs['csv'] = count_nonzero_medial.outputs['statistics']
        convert_to_qib_medial.inputs['session'] = session_id.output
           
        convert_to_qib_lateral = network.create_node(fastr.toollist['ConvertCsvToQibSessionMH','0.3'], id_='convert_to_qib_lateral')
        convert_to_qib_lateral.inputs['tool'] = ('MultiAtlas Appearance Model Segmentation with Volume Calculation'),
        convert_to_qib_lateral.inputs['tool_version'] = ('0.1'),
        convert_to_qib_lateral.inputs['description'] = ('MultiAtlas Appearance Model Segmentation'),
        convert_to_qib_lateral.inputs['begin_date'] = (time.strftime("%Y-%m-%dT%H:%M")),
        convert_to_qib_lateral.inputs['processing_site'] = ('Erasmus MC'),
        convert_to_qib_lateral.inputs['paper_title'] = ('Automated brain structure segmentation based on atlas registration and appearance models'),
        convert_to_qib_lateral.inputs['paper_link'] = ('/onlinelibrary.wiley.com/doi/10.1002/hbm.22522/full'),
        convert_to_qib_lateral.inputs['paper_notes'] = ('Method is a variant of version described in paper (no MRF model for spatial coherence'),
        convert_to_qib_lateral.inputs['categories'] = ('Femoral Cartilage'),
        convert_to_qib_lateral.inputs['ontologyname'] = ('Uberon'),
        convert_to_qib_lateral.inputs['ontologyIRI'] = ('NA'),
        convert_to_qib_lateral.inputs['csv'] = count_nonzero_lateral.outputs['statistics']
        convert_to_qib_lateral.inputs['session'] = session_id.output


        # Create sink for dice overlap score
        out_qib_session_medial = network.create_sink(datatype=fastr.typelist['XmlFile'],id_='out_qib_session_medial')
        link = network.create_link(convert_to_qib_medial.outputs['qib_session'],out_qib_session_medial.input)
        #link.collapse = 'target'

        # Create sink
        out_seg_medial = network.create_sink('NiftiImageFileCompressed', id_='out_seg_medial')
        out_seg_medial.input = argmax_medial.outputs['image']

        # Create sink for dice overlap score
        out_qib_session_lateral = network.create_sink(datatype=fastr.typelist['XmlFile'],id_='out_qib_session_lateral')
        link = network.create_link(convert_to_qib_lateral.outputs['qib_session'],out_qib_session_lateral.input)
        #link.collapse = 'target'
         
        # Create sink
        out_seg_lateral = network.create_sink('NiftiImageFileCompressed', id_='out_seg_lateral')
        out_seg_lateral.input = argmax_lateral.outputs['image']


        sinkdata = {'out_seg_medial':     'vfs://scratch/data/FemkePROOF/lateralmedialmen/segm_medial_FEMKE_{sample_id}{ext}',
                    'out_qib_session_medial': 'vfs://scratch/data/FemkePROOF/lateralmedialmen/QIB_medial_FEMKE_{sample_id}{ext}',
                    'out_seg_lateral':     'vfs://scratch/data/FemkePROOF/lateralmedialmen/segm_lateral_FEMKE_{sample_id}{ext}',
                    'out_qib_session_lateral': 'vfs://scratch/data/FemkePROOF/lateralmedialmen/QIB_lateral_FEMKE_{sample_id}{ext}',
                    }

        print network.draw_network(img_format='svg', draw_dimension=True)
        fastr.log.info('^^^^^^^^^^^^^ Starting execution client.')
        network.execute(sourcedata_part, sinkdata,cluster_queue="month",tmpdir=staging_dir)
        
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

