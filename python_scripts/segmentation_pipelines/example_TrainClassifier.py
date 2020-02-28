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

# Cross-validation code for multi-atlas segmentation of knee-MRI data using ROI masks. Output is currently
# one textfile containing Jaccard index for each fold of CV.

import fastr
from sourcedata_TrainClassifier_PROOF import sourcedata

def main():

    # Scale space scales to extract (in mm)
    scales = (1.0, 1.6, 4.0)
    # Radius for the background sampling mask dilation (mm?)
    radius = [5.0]
    # Number/fraction of sample to sample per images
    # On element per class (class0, class1, etc)
    # If value between [0.0 - 1.0] it is a fraction of the number of samples
    # available in that class
    # If the value is above 1, it is the number of samples to take, if the
    # avaialble number of samples is lower, it will take all samples.
    nsamples = (1000,1000)
    # Note: the parameters for the random forest classifier are in the
    # parameter file supplied as source data

    network = fastr.Network(id_="Femke_LEFT_train_classifer")
    source_t1 = network.create_source('NiftiImageFileCompressed', id_='images', sourcegroup='atlas')
    source_label = network.create_source('NiftiImageFileCompressed', id_='label_images', sourcegroup='atlas')
    source_param = network.create_source('KeyValueFile', id_='param_file')
    source_atlasROI = network.create_source('NiftiImageFileCompressed', id_='ROI', sourcegroup='atlas')
    
    n4_atlas_im = network.create_node('N4', id_='n4_atlas', memory='15G')
    n4_atlas_im.inputs['image'] = source_t1.output
    #n4_atlas_im.inputs['mask'] = source_normmask_atlas.output
    n4_atlas_im.inputs['shrink_factor'] = 4,
    n4_atlas_im.inputs['converge'] = '[150,00001]',
    n4_atlas_im.inputs['bspline_fitting'] = '[50]',
    
    # Range match images
    rama_atlas_im = network.create_node('RangeMatch', id_='rama_atlas',memory='15G')
    rama_atlas_im.inputs['image'] = n4_atlas_im.outputs['image']
    rama_atlas_im.inputs['mask'] = source_atlasROI.output

    #threshold = network.create_node('FSLMaths', id_='threshold_preprocess', memory='15G')
    #threshold.inputs['image1'] = source_label.output
    #threshold.inputs['operator1'] = ['-thr']
    #threshold.inputs['operator1_string'] = [1.5]

    #binarize_medialmen = network.create_node('FSLMaths', id_='binarize_medialmen')
    #binarize_medialmen.inputs['image1'] = threshold.outputs['output_image']
    #binarize_medialmen.inputs['operator1'] = ['-bin']

    pxcastconvert = network.create_node('PxCastConvert', id_='castconvert')
    pxcastconvert.inputs['image'] = source_label.output
    pxcastconvert.inputs['component_type'] = ['char']
    
    # Create filter image for source data
    scalespacefilter = network.create_node('GaussianScaleSpace', id_='scalespacefilter', memory='15G')
    scalespacefilter.inputs['image'] = rama_atlas_im.outputs['image']
    scalespacefilter.inputs['scales'] = scales

    # Prepare mask
    morph = network.create_node('PxMorphology', id_='morph', memory='6G')
    morph.inputs['image'] = pxcastconvert.outputs['image']
    morph.inputs['operation'] = ['dilation']
    morph.inputs['operation_type'] = ['binary']
    morph.inputs['radius'] = radius

    # Sample the feature images
    sampler = network.create_node('SampleImage', id_='sampler', memory='15G')
    sampler.inputs['image'] = scalespacefilter.outputs['image']
    sampler.inputs['labels'] = pxcastconvert.outputs['image']
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

    sinkdata = {'out_classifier': 'vfs://fastr_data/seg/class/Femke_LEFT_trained_classifer{ext}'}

    print network.draw_network(img_format='svg', draw_dimension=True)
    fastr.log.info('^^^^^^^^^^^^^ Starting execution client.')
    network.execute(sourcedata, sinkdata,cluster_queue="week")
    
if __name__ == '__main__':
    main()

