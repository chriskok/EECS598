import sys
import boto3
import json
import pandas as pd
from my_secrets import my_secrets

# By default, HITs are created in the free-to-use Sandbox
create_hits_in_live = False

aws_access_key_id = my_secrets.get('aws_access_key_id')
aws_secret_access_key = my_secrets.get('aws_secret_access_key')

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
# profile_name = sys.argv[1] if len(sys.argv) >= 2 else None
# session = boto3.Session(profile_name=profile_name)
client = boto3.client(
    service_name='mturk',
    region_name='us-east-1',
    endpoint_url=mturk_environment['endpoint'],
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
)

# Test that you can connect to the API by checking your account balance
user_balance = client.get_account_balance()

# In Sandbox this always returns $10,000. In live, it will be your actual balance.
print ("Your account balance is {}".format(user_balance['AvailableBalance']))



###########################################
#                READ DATA                #
###########################################
head_df = pd.read_csv('data/Corona_NLP_test.csv').head(5)
tweets = list(head_df['OriginalTweet'])

# The question we ask the workers is contained in this file.
html_layout = open('./index.html', 'r').read()
QUESTION_XML = """<HTMLQuestion xmlns="http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2011-11-11/HTMLQuestion.xsd">
        <HTMLContent><![CDATA[{}]]></HTMLContent>
        <FrameHeight>650</FrameHeight>
        </HTMLQuestion>"""
question_xml = QUESTION_XML.format(html_layout)

# Example of using qualification to restrict responses to Workers who have had
# at least 80% of their assignments approved. See:
# http://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_QualificationRequirementDataStructureArticle.html#ApiReference_QualificationType-IDs
worker_requirements = [{
    'QualificationTypeId': '000000000000000000L0',
    'Comparator': 'GreaterThanOrEqualTo',
    'IntegerValues': [80],
    'RequiredToPreview': True,
}]

TaskAttributes = {
    'MaxAssignments': 5,           
    # How long the task will be available on MTurk (1 hour)     
    'LifetimeInSeconds': 60*60,
    # How long Workers have to complete each item (10 minutes)
    'AssignmentDurationInSeconds': 60*10,
    # The reward you will offer Workers for each response
    'Reward': mturk_environment['reward'],                     
    'Title': 'Coronavirus Tweet Sentiment',
    'Keywords': 'sentiment, tweet, coronavirus, twitter, covid',
    'Description': 'Rate the sentiment of a coronavirus-related tweet',
    'QualificationRequirements': worker_requirements,
}



###########################################
#               CREATE HITS               #
###########################################

results = []
hit_type_id = ''
for tweet in tweets:
    response = client.create_hit(
        **TaskAttributes,
        Question=question_xml.replace('${content}',tweet)
    )
    hit_type_id = response['HIT']['HITTypeId']
    results.append({
        'tweet': tweet,
        'hit_id': response['HIT']['HITId']
    })
    
print("You can view the HITs here:")
print(mturk_environment['preview']+"?groupId={}".format(hit_type_id))

print ("\nAnd see results here:")
print (mturk_environment['manage'])

with open("results.json", "w") as final:
   json.dump(results, final)