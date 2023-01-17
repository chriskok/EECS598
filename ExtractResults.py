import json
import sys
import boto3
import xmltodict
import csv

from os import path
from xml.dom.minidom import parseString
from my_secrets import my_secrets

f = open('results.json')
results = json.load(f)

print(results)

aws_access_key_id = my_secrets.get('aws_access_key_id')
aws_secret_access_key = my_secrets.get('aws_secret_access_key')

# By default, we use the free-to-use Sandbox
create_hits_in_live = False

environments = {
        "live": {
            "endpoint": "https://mturk-requester.us-east-1.amazonaws.com",
            "preview": "https://www.mturk.com/mturk/preview",
            "manage": "https://requester.mturk.com/mturk/manageHITs",
            "reward": "0.00"
        },
        "sandbox": {
            "endpoint": "https://mturk-requester-sandbox.us-east-1.amazonaws.com",
            "preview": "https://workersandbox.mturk.com/mturk/preview",
            "manage": "https://requestersandbox.mturk.com/mturk/manageHITs",
            "reward": "0.11"
        },
}
mturk_environment = environments["live"] if create_hits_in_live else environments["sandbox"]

# use profile if one was passed as an arg, otherwise
# profile_name = sys.argv[2] if len(sys.argv) >= 3 else None
# session = boto3.Session(profile_name=profile_name)
client = boto3.client(
    service_name='mturk',
    region_name='us-east-1',
    endpoint_url=mturk_environment['endpoint'],
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
)

write_header = False
if not path.exists('assignments.csv'): 
    write_header = True

with open('assignments.csv', 'a', newline='') as csvfile:
    fieldnames = ['AssignmentId', 'WorkerId', 'HITId', 'AutoApprovalTime', 'AcceptTime', 'SubmitTime', 'Answer']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    if(write_header): writer.writeheader()

    for item in results:
        
        # Get the status of the HIT
        hit = client.get_hit(HITId=item['hit_id'])
        item['status'] = hit['HIT']['HITStatus']
        # Get a list of the Assignments that have been submitted
        assignmentsList = client.list_assignments_for_hit(
            HITId=item['hit_id'],
            AssignmentStatuses=['Submitted', 'Approved'],
            MaxResults=10
        )
        assignments = assignmentsList['Assignments']
        item['assignments_submitted_count'] = len(assignments)
        answers = []
        for assignment in assignments:
        
            # Retreive the attributes for each Assignment
            worker_id = assignment['WorkerId']
            assignment_id = assignment['AssignmentId']
            
            # Retrieve the value submitted by the Worker from the XML
            answer_dict = xmltodict.parse(assignment['Answer'])
            print(assignment)

            answer = answer_dict['QuestionFormAnswers']['Answer']['FreeText']
            # answers.append(int(answer))
            
            # Approve the Assignment (if it hasn't been already)
            if assignment['AssignmentStatus'] == 'Submitted':
                client.approve_assignment(
                    AssignmentId=assignment_id,
                    OverrideRejection=False
                )

                writer.writerow({'AssignmentId': assignment['AssignmentId'], 
                                'WorkerId': assignment['WorkerId'], 
                                'HITId': assignment['HITId'],  
                                'AutoApprovalTime': assignment['AutoApprovalTime'],  
                                'AcceptTime': assignment['AcceptTime'],  
                                'SubmitTime': assignment['SubmitTime'],  
                                'Answer': int(answer)})