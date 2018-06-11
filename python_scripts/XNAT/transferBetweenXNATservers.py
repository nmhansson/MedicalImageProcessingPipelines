#First download xnat subjects from one xnat server 
#and store in zipped format locally.
#
#Next upload the subjects to other xnat server.
#
import os
import xnat

#directory in which to locally store subjects 
temp_dir = '/scratch/mhansson/trash_dir'

# start subject and end subject number
start = 0
end = 326

study_name_origin = 'Proof_Study'
study_name_dest = 'Proof_Study'

origin_xnat = 'http://bigr-rad-xnat.erasmusmc.nl'
destination_xnat = 'http://10.191.20.128'

session_archives = []

#download
with xnat.connect(origin_xnat) as session_rad:
    project = session_rad.projects[study_name_origin]

    for nr in range(start, end):
        subject = 'PROOF{:03d}'.format(nr)

        if subject not in project.subjects:
            print('Cannot find {}'.format(subject))
            continue

        subject = project.subjects[subject]
        # Process subject
        print('Processing subject: {}'.format(subject.label))
        for experiment in subject.experiments.values():
            filepath = os.path.join(temp_dir, experiment.label + '.zip')
            print('Downloading experiment {} to {}'.format(experiment.label, filepath))
            experiment.download(filepath)
            session_archives.append(filepath)

#upload
with xnat.connect(destination_xnat) as session_sandbox:
    for filepath in session_archives:
        print('Importing {} into target XNAT'.format(filepath))
        session_sandbox.services.import_(filepath, project=study_name_dest)
        
        # delete subject locally
        print('Removing {}'.format(filepath))
        os.remove(filepath)
