# README #


This repo contains bash and python scripts for medical image processing.

Scripts are aimed at data cleaning and multi-atlas segmentation. 

Specifically, Segmentation pipelines are contained in med_im_proc_python_bash/python_scripts/segmentation_pipelines

Please note that the pipelines depend on the python package fastr (https://gitlab.com/radiology/infrastructure/fastr)
developed at Erasmus Medical Center.

Segmentation is two step: 

1) Classifier is trained. See example_TrainClassifier.py

2) Segment structure. See example_segmentation_oneclassifier.py

Direct questions to nm.hansson@gmail.com 

