#!/usr/bin/python

# Obtain urls for the PROOF study for a given timepoint and laterality for de3d and WATS scans 

# usage python extract_scans_seriesdescrip.py [timepoint] [laterality]
# timepoint = 0,12,30,78
# laterality = R,L

import xnat
import sys
import re

xnathost = 'http://bigr-rad-xnat.erasmusmc.nl'
project = 'Proof_Study'
hand = sys.argv[2]

for nr in range(1,408):
    
    subject = 'PROOF{:03d}'.format(nr)

    experiment = subject + '_MRI_' + hand + '_T' + str(sys.argv[1])
    with xnat.connect(xnathost) as connection:
        try:
        	xnat_project = connection.projects[project]
        	xnat_subject = xnat_project.subjects[subject]
        	xnat_experiment = xnat_subject.experiments[experiment]
        	for xnat_scan in xnat_experiment.scans.values():
            		
                         
                        if 'de3d' in xnat_scan.series_description or 'WATS' in xnat_scan.series_description:
              			tmp = re.search('\((.*?)\)',str(xnat_scan)).group(1)
                                print('\'' + experiment + '\':' + '\'xnat://bigr-rad-xnat.erasmusmc.nl/' +
                                'data/archive/projects/' + project + '/subjects/' + subject +
                                '/experiments/' + experiment + '/scans/' + tmp +
                                '/resources/DICOM?insecure=true' + '\',')
	except:
		continue
	

