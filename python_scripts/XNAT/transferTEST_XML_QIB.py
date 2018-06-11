import os
import xnat

session_archives = ['\home\mhansson\QIBSessionInstance_PROOF001_L_T0.zip']

with xnat.connect('http://10.191.20.128') as session_sandbox:
        for filepath in session_archives:
             print('Importing {} into target XNAT'.format(filepath))
             session_sandbox.services.import_(filepath, project='Proof_Study')

             
