#!/usr/bin/python

# get info from dicom tag for all dicoms on root path


import os
import sys
import dicom
import subprocess

root_path = "/archive/mhansson/PROOF/#_1"

outcsvfilepath = '/scratch/mhansson/'

savetocsv = True

dirs = [os.path.join(root_path, d) for d in os.listdir(root_path)]

for d in dirs:
    dicom_files = []
    i = 0
    for root, dirs, files in os.walk(d):
        for name in files:
            f = os.path.join(root, name)
            ftype = subprocess.check_output(['file', '--mime-type', '-b', f]).decode('utf-8').strip()
            if ftype == 'application/dicom':
                i += 1
                dicom_files += [f]
            if i > 5:
                break


    PatientList = set()
    PatientInfo = tuple()

    for df in dicom_files:
        ds = dicom.read_file(df)
        try:
            PatientInfo = (ds.PatientID, 
                           ds.PatientName, 
                           ds.AcquisitionDate, 
                           ds.ImageComments,
                          # ds.RequestedProcedureDescription,
                          # ds.PerformedProcedureStepDescription,
                          # ds.RequestAttributeSequence,
                          # ds.ProcedureCodeSequence,
                          # ds.SeriesDescription,
                          # ds.ProtocolName,
                          # left_right_info,
                           ds.Modality)
            PatientList.add(PatientInfo)
        except AttributeError as excp:
            pass


if savetocsv:

    f = open(outcsvfilepath + 'out.csv','w')
    f.write('PatientID;PatientName;AcquisitionDate;ds.Modality\n')

    for  pat_info in PatientList:
            for info in pat_info:
                f.write(info)
                f.write(';')
            f.write('\n')

    f.close()

else:

    for  pat_info in PatientList:
           for info in pat_info:
               sys.stdout.write(info)
               sys.stdout.write(';')
               sys.stdout.write('\n')
               sys.stdout.flush()
	
