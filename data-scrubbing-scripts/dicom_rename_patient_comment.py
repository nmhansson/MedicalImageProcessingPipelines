#!/usr/bin/env python

# Authors: Adriaan Versteeg and Mattias Hansson

# Copyright 2011-2017 Biomedical Imaging Group Rotterdam, Departments of
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
                                 
# Uses a csv file to write the PatientComments field for all dicoms (which can be identified by the csv file) in a study folder.

import os
import sys
import dicom
import subprocess
import csv
from collections import defaultdict

debug = False
# load csv naming file
csv_file_path = '/home/mhansson/data_cleaning_scripts/example_study.csv'
num_dcm_renamed = 0
num_rows_csv = 0
num_obs = 0
with open(csv_file_path, 'rbU') as count_file:
        csv_reader = csv.reader(count_file)
        for row in csv_reader:
                num_rows_csv += 1
naming = defaultdict(list)

# create naming vector from csv file, which contains the PatientsComments field (row[20] in this case). The naming vector is used to find the session in the study folder, and
# then write the PatientsComments field in the related dicom. 
with open(csv_file_path, 'rU') as csvfile:
    csv_data = csv.reader(csvfile, delimiter=',', quotechar='|')
    next(csv_data, None)  # skip the headers
    for row in csv_data:
        #          0   1     2     3       4            5           6                 7               8                  9             10            11           12           13 
	#date =  (pID,Name,AqDate,ImCom,ProtocolName,SeriesDescr,StudyDescr,PerformedProcStepDesc,RETIREDStudyCom,RequestProcDescr,RequestAttsSeq,ProcCodeSeq,ReqProcCodeSeq,PROOF066_MRI_X_TX    
        date = (row[2],row[3],row[4],row[5],row[6],row[7],row[8],row[9],row[10],row[11],row[12],row[13],row[14],row[20])         
#                  0     1      2      3      4      5      6      7      8       9       10       11     12      13    
        naming[row[1]].append(date)

root_path = "/scratch/mhansson/data/PROOF/PROOF"

for d in dirs:
     dicom_files = []
     subject_id =  d.split('#_', 1)[1]
     subject_id_string = str(subject_id).zfill(3)
     if subject_id not in naming.keys():
         print('skipping ID:{}'.format(subject_id))
     else: # if subject_id_string in naming
        for root, dirs, files in os.walk(d):
            for name in files:
                f = os.path.join(root, name)
                ftype = subprocess.check_output(['file', '--mime-type', '-b', f]).decode('utf-8').strip()
                if ftype == 'application/dicom':
                    dicom_files += [f]

        PatientList = set()
        PatientInfo = tuple()

        for df in dicom_files:
           ds = dicom.read_file(df)
           try:
               ImComments = ds.ImageComments
           except:
               ImComments = ""
           try:
               ProtocolName = ds.ProtocolName
           except:
               ProtocolName = ""
           try:
               SeriesDescription =  ds.SeriesDescription
           except:
               SeriesDescription = ""  
           try:
               StudyDescription = ds.StudyDescription
           except:
               StudyDescription = ""
           try:
               PerformedProcedureStepDescription = ds.PerformedProcedureStepDescription
           except:
               PerformedProcedureStepDescription = ""
           try:
               RETIREDStudyComments = ds.RETIREDStudyComments
           except:
               RETIREDStudyComments = ""
           try: 
               RequestedProcedureDescription = ds.RequestedProcedureDescription
           except:
               RequestedProcedureDescription = ""

           if 'RequestAttributesSequence' in ds:
               try:
                  if len(ds.RequestAttributesSequence[0].ScheduledProcedureStepDescription) > 0:
                     RequestAttributesSequence = ds.RequestAttributesSequence[0].ScheduledProcedureStepDescription
                  else:
                     RequestAttributesSequence = ""
               except:
                     RequestAttributesSequence = ""
           else:
               RequestAttributesSequence = ""

           if 'ProcedureCodeSequence' in ds:
               try:
                 if len(ds.ProcedureCodeSequence[0].CodeMeaning) > 0:
                    ProcedureCodeSequence = ds.ProcedureCodeSequence[0].CodeMeaning
                 else:
                    ProcedureCodeSequence = ""
               except:
                    ProcedureCodeSequence = ""                                                                                                                                   
           else:
                ProcedureCodeSequence = ""      

           if 'RequestedProcedureCodeSequence' in ds:
                try:
                  if len(ds.RequestedProcedureCodeSequence[0].CodeMeaning) > 0:
                     RequestedProcedureCodeSequence = ds.RequestedProcedureCodeSequence[0].CodeMeaning
                  else:
                     RequestedProcedureCodeSequence = ""
                except:
                     RequestedProcedureCodeSequence = ""
           else:
                RequestedProcedureCodeSequence = ""

           try:
                #print('got here 1')
                if ds.Modality == 'MR':
                   num_dcm_renamed += 1
                PatientInfo = (ds.PatientID,                       #0
                               ds.PatientName,                     #1
                               ds.AcquisitionDate,                 #2
                               ImComments,                         #3
                               ProtocolName,                       #4
                               SeriesDescription,                  #5
                               StudyDescription,                   #6 
                               PerformedProcedureStepDescription,  #7 
                               RETIREDStudyComments,               #8   
                               RequestedProcedureDescription,      #9
                               RequestAttributesSequence,          #10 
                               ProcedureCodeSequence,              #11
                               RequestedProcedureCodeSequence,     #12
                               ds.Modality)                        #13 
                       
                for date in naming[subject_id]:
                    bool1 = (PatientInfo[0]==date[0])
                    bool2 = (PatientInfo[1]==date[1])
                    bool3 = (PatientInfo[2]==date[2])
                    bool4 = (PatientInfo[3]==date[3])
                    bool5 = (PatientInfo[4]==date[4])
                    bool6 = (PatientInfo[5]==date[5])
                    bool7 = (PatientInfo[6]==date[6])
                    bool8 = (PatientInfo[7]==date[7])
                    bool9 = (PatientInfo[8]==date[8])
                    bool10 = (PatientInfo[9]==date[9])
                    bool11 = (PatientInfo[10]==date[10])
                    bool12 = (PatientInfo[11]==date[11])
                    bool13 = (PatientInfo[12]==date[12])
        
                    if bool1 and bool2  and bool3  and bool4 and \
                       bool5 and bool6  and bool7  and bool8 and \
                       bool9 and bool10 and bool11 and bool12 and bool13 :
                        
                        PatientComments = 'Project: Proof_Study; Subject: PROOF' + subject_id_string +'; Session: ' + date[13]
                        print('{};{};{};{};{}'.format(subject_id,PatientInfo[2],PatientInfo[3],PatientComments,df))
                        ds.PatientComments = PatientComments
			ds.save_as(df)
                        break
                     
           except AttributeError as excp:
                pass
            
        if debug:
            print("#PatientList {}".format(len(PatientList)))
            print("#PatientInfo {}".format(len(PatientInfo)))
