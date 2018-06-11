#!/usr/bin/env python
import os
import sys
import dicom
import subprocess
import csv
from collections import defaultdict

subject_num = '303'
PatCommentHardCode = 'PROOF' + subject_num + '_MRI_L_T2'
dirs = ['/scratch/mhansson/data/PROOF/PROOF/#_' + subject_num + '/LT/S0000002']

for d in dirs:
     dicom_files = []
     for root, dirs, files in os.walk(d):
         for name in files:
            f = os.path.join(root, name)
            ftype = subprocess.check_output(['file', '--mime-type', '-b', f]).decode('utf-8').strip()
            if ftype == 'application/dicom':
               dicom_files += [f]

    
for df in dicom_files:
    ds = dicom.read_file(df)
    PatientComments = 'Project: Proof_Study; Subject: PROOF' + subject_num +'; Session: ' + PatCommentHardCode
    print('{};{}'.format(PatientComments,df))
    ds.PatientComments = PatientComments
    ds.save_as(df)
                    
                     
