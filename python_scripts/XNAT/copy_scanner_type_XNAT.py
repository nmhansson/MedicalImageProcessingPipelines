#!/usr/bin/env python 

# Copy scanner name from study residing on one XNAT server to another


import os
import xnat

temp_dir = '/scratch/mhansson/trash_dir'
start = 2
end = 408

session_archives = []
#experiment_scanner = {}
experiment_model = {}
experiment_manufacturer = {}

with xnat.connect('http://bigr-rad-xnat.erasmusmc.nl') as session_rad:
    project = session_rad.projects['Proof_Study']

    for nr in range(start, end):
        subjectname = 'PROOF{:03d}'.format(nr)
        print(subjectname)
        if subjectname not in project.subjects:
            print('Cannot find {}'.format(subjectname))
            continue

        subject = project.subjects[subjectname]
        # Process subject
        print('Processing subject: {}'.format(subject.label))
        for experiment in subject.experiments.values():
            
            print(experiment)
            experiment_model[experiment.label] = experiment.scanner.model
            print(experiment.scanner.model)
            experiment_manufacturer[experiment.label] = experiment.scanner.manufacturer
            print(experiment.scanner.manufacturer)

with xnat.connect('https://xnat-acc.bmia.nl') as session_acc:
    project_acc = session_acc.projects['qibproof']  
    
    for nr in range(start, end):
        name = 'PROOF{:03d}'.format(nr)
        #print(project_acc.subjects)
        try:
           subject = project_acc.subjects[name]
        except KeyError:
            print('Cannot find {}'.format(subject))
            continue
        else:
           for experiment in subject.experiments.values():
               
               if 'QIB' in experiment.label:
                    continue
               else:
                    experiment.scanner.model = experiment_model[experiment.label] 
                    experiment.scanner.manufacturer = experiment_manufacturer[experiment.label] 
           
    
    
    
    
    
    
