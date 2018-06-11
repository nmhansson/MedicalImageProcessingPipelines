import os
import xnat

temp_dir = '/scratch/mhansson/trash_dir'
start = 1
end = 3

session_archives = []

with xnat.connect('https://xnat.bmia.nl') as session_rad:
    project = session_rad.projects['Proof_Study']

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

with xnat.connect('https://xnat-acc.bmia.nl') as session_sandbox:
    for filepath in session_archives:
        print('Importing {} into target XNAT'.format(filepath))
        session_sandbox.services.import_(filepath, project='qibproof')
        
        print('Removing {}'.format(filepath))
        os.remove(filepath)
