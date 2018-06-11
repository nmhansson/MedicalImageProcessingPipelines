#!/usr/bin/env python

# Produces a text with dicom fields separated by ;
# First field is the subject number (it is assumed that each
# subject in study has one folder called #_1 etc.
# typical usage: nohup python parse_dicoms.py > example_study.csv &


import os
import sys
import dicom
import subprocess
import functools
import operator

def concatenate(sequence):
    return functools.reduce(operator.add,sequence)
num_dcms = 0 
debug = True

# root_path = path to study directory
root_path = "/scratch/mhansson/data/PROOF/PROOF"

dirs = [os.path.join(root_path, d) for d in os.listdir(root_path)]

for d in dirs:
    dicom_files = []

    for root, dirs, files in os.walk(d):
        i = 0
        for name in files:
            f = os.path.join(root, name)
            ftype = subprocess.check_output(['file', '--mime-type', '-b', f]).decode('utf-8').strip()
            if ftype == 'application/dicom':
               i += 1
               dicom_files += [f]
            

    PatientList = set()
    PatientInfo = tuple()

    for df in dicom_files:
        ds = dicom.read_file(df)
        left_right_info = list()
        for tag in ('ImageComments', 'ProtocolName','SeriesDescription',
                    'StudyDescription',
                    'PerformedProcedureStepDescription',
                    'RETIREDStudyComments','RequestedProcedureDescription'): 
            if tag in ds:
                left_right_info = left_right_info + [ds.data_element(tag).value]
            else:
                left_right_info = left_right_info + [""] 
    
        # Remaining fields are subfields and so are treated as special cases (may be better way to handle this...)            
        if 'RequestAttributesSequence' in ds:  
            try:
                if len(ds.RequestAttributesSequence[0].ScheduledProcedureStepDescription) > 0:
                
                   left_right_info = left_right_info + [ds.RequestAttributesSequence[0].ScheduledProcedureStepDescription]
                else: 
                   left_right_info = left_right_info + [""]
            except:
                   left_right_info = left_right_info + [""]
                   
        else:
            left_right_info = left_right_info + [""] 
        
        if 'ProcedureCodeSequence' in ds: 
            try:
                if len(ds.ProcedureCodeSequence[0].CodeMeaning) > 0:
                   left_right_info = left_right_info + [ds.ProcedureCodeSequence[0].CodeMeaning]
                else:
                   left_right_info = left_right_info + [""]
            except:
                   left_right_info = left_right_info + [""]
                   
        else:
            left_right_info = left_right_info + [""] 
      
        if 'RequestedProcedureCodeSequence' in ds:
            try:
                if len(ds.RequestedProcedureCodeSequence[0].CodeMeaning) > 0:
                    left_right_info = left_right_info + [ds.RequestedProcedureCodeSequence[0].CodeMeaning]
                else:
                    left_right_info = left_right_info + [""]
            except:
                    left_right_info = left_right_info + [""]
                
        else:                                                           
             left_right_info = left_right_info + [""] 
        
        left_right_info = ';'.join(left_right_info)    
        
        try:
           if ds.Modality == 'MR':
              num_dcms += 1
        
           PatientInfo = (ds.PatientID, 
                          ds.PatientName, 
                          ds.AcquisitionDate, 
                          left_right_info,
                          ds.Modality)
           PatientList.add(PatientInfo)
           
        except AttributeError as excp:
           pass
           
    
    subject_id =  d.split('#_', 1)[1]
    for  pat_info in PatientList:
        sys.stdout.write(subject_id)
        sys.stdout.write(';')
	for info in pat_info:
	    sys.stdout.write(info)
            sys.stdout.write(';')
        sys.stdout.write('\n')
        sys.stdout.flush()

