import json
import boto3
import argparse
import ssl
import time
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


class Splunker(object):
    def __init__(self, url, stack_name, region, profile):
        self.stack_name = stack_name
        self.region = region
        self.profile = profile
        self.url = url
        if self.url != 'none':
            self.secret = self.get_secret('DataSplunkToken')

    def get_secret(self, secret_name):
        """
        Get secret from secrets manager
        :param secret_name: name of the secret
        :return:
        """
        session = boto3.Session(profile_name=self.profile)
        client = session.client(service_name='secretsmanager', region_name=self.region)
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        kvp = get_secret_value_response['SecretString']
        print('Retrieved secret for {}'.format(secret_name))
        return json.loads(kvp)[secret_name]

    def send_message(self, url, message, headers):
        """
        send an http message
        :param url: endpoint
        :param message: payload
        :param headers: headers
        :return:
        """
        req = Request(url, data=message.encode('utf-8'), headers=headers)
        gcontext = ssl.SSLContext()
        try:
            response = urlopen(req, context=gcontext)
            res = response.read()
            print('Message posted {}'.format(res))
        except HTTPError as e:
            print("Request failed: %d %s", e.code, e.reason)
        except URLError as e:
            print("Server connection failed: %s", e.reason)

    def send_splunk_message(self, message, sourcetype_suffix):
        """
        Send a message to splunk
        :param message: payload
        :param sourcetype_suffix: suffix to use for the sourcetype
        :return:
        """
        if self.url == 'none':
            print('url is empty, unable send message')
            return

        sourcetype = '{}.{}'.format(self.stack_name, sourcetype_suffix)
        print('Sending Splunk message to sourcetype {} - message {}'.format(sourcetype, message))

        splunk_message = {
            'sourcetype': sourcetype,
            'event': message
        }
        headers = {
            'Authorization': 'Splunk {}'.format(self.secret)
        }
        self.send_message(self.url, json.dumps(splunk_message, indent=4, sort_keys=True, default=str), headers)


class ChangeSetHandler(object):
    def __init__(self, stack_name, region, profile):
        session = boto3.Session(profile_name=profile)
        self.client = session.client('cloudformation', region_name=region)
        self.stack_name = stack_name

    def get_latest_change_set_details(self):
        """
        Get the latest change set name and details
        :return: ChangeSetName, details response
        """
        change_sets = self.client.list_change_sets(StackName=self.stack_name)
        change_set_count = len(change_sets['Summaries'])
        print('Discovered {} change set(s)'.format(change_set_count))
        latest_change_set = change_sets['Summaries'][change_set_count - 1]

        return latest_change_set['ChangeSetName'], self.client.describe_change_set(
            ChangeSetName=latest_change_set['ChangeSetName'],
            StackName=self.stack_name,
        )

    def execute_change_set(self, name):
        """
        execute the change set
        :param name: name of the change set
        :return: response
        """
        return self.client.execute_change_set(
            ChangeSetName=name,
            StackName=self.stack_name
        )


class DriftHandler(object):
    def __init__(self, stack_name, region, profile):
        session = boto3.Session(profile_name=profile)
        self.client = session.client('cloudformation', region_name=region)
        self.stack_name = stack_name

    def find_stacks(self):
        """
        Finds all the related stacks
        :return: list of matching stacks
        """
        complete = False
        status = ''
        while not complete:
            time.sleep(30)
            status = self.client.describe_stacks(StackName=self.stack_name)['Stacks'][0]['StackStatus']

            if status == 'CREATE_COMPLETE' or status == 'UPDATE_COMPLETE':
                complete = True
            elif status == 'ROLLBACK_COMPLETE' or status == 'UPDATE_ROLLBACK_COMPLETE':
                return status, []

        sub_stacks = self.client.list_stack_resources(StackName=self.stack_name)['StackResourceSummaries']
        stack_names = []
        for sub_stack in sub_stacks:
            # 'arn:aws:cloudformation:us-west-2:477772436619:stack/descanso-dev-us-west-2-APIStack-1GV3T2Z2PWIOP/bb18fe30-668d-11e9-ace8-02741f3dee14'
            stack_names.append(sub_stack['PhysicalResourceId'])
        stack_names.append(self.stack_name)
        return status, stack_names

    def detect_drift(self, stack_name):
        """
        Detects the drift status of the given stack
        :param stack_name: name of stack to detect
        :return: DetectionStatus, StackDriftStatus
        """
        stacks = self.client.describe_stacks(StackName=stack_name)['Stacks']
        status = stacks[0]['StackStatus']
        while status == 'UPDATE_IN_PROGRESS' or \
                status == 'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS':
            time.sleep(5)
            status = self.client.describe_stacks(StackName=stack_name)['Stacks'][0]['StackStatus']
        drift_id = self.client.detect_stack_drift(StackName=stack_name)['StackDriftDetectionId']
        detection_status_response = self.client.describe_stack_drift_detection_status(StackDriftDetectionId=drift_id)
        while detection_status_response['DetectionStatus'] == 'DETECTION_IN_PROGRESS':
            time.sleep(5)
            detection_status_response = self.client.describe_stack_drift_detection_status(StackDriftDetectionId=drift_id)
        return detection_status_response['DetectionStatus'], detection_status_response['StackDriftStatus']


if __name__ == "__main__":
    """
    Takes arguments when run from the command line
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("StackName", help="")
    parser.add_argument("Region", help="")
    parser.add_argument("ProfileName", help="")
    parser.add_argument("SplunkUrl", help="")
    args = parser.parse_args()

    # get the latest change set name and details
    ch = ChangeSetHandler(args.StackName, args.Region, args.ProfileName)
    change_set_name, change_set_details = ch.get_latest_change_set_details()

    # execute change set identified from above
    response = ch.execute_change_set(change_set_name)
    response_code = response['ResponseMetadata']['HTTPStatusCode']
    change_set_details['ResponseCode'] = response_code
    if response_code == 200:
        print('Executed Latest Change Set Successfully..')
    else:
        print(json.dumps(response, indent=4, sort_keys=True, default=str))

    # send change set details to Splunk
    sh = Splunker(args.SplunkUrl, args.StackName, args.Region, args.ProfileName)
    sh.send_splunk_message(change_set_details, 'changeset')

    # get a list of our stacks once deployment is complete
    dh = DriftHandler(args.StackName, args.Region, args.ProfileName)
    stack_status, stack_list = dh.find_stacks()

    print('Stack: {} completed with Status: {}'.format(args.StackName, stack_status))
    print('Resources found for this stack are: {}'.format(stack_list))
    if stack_status == 'ROLLBACK_COMPLETE' or stack_status == 'UPDATE_ROLLBACK_COMPLETE':
        print('Stack deployment was not successful')
        exit(-1)

    failed = False
    for stack in stack_list:
        # detect if a drift has occurred on this individual stack
        detection_status, drift_status = dh.detect_drift(stack)
        message = 'Stack: {} - Drift Status: {}'.format(stack, drift_status)

        # send drift status to Splunk
        sh.send_splunk_message(message, 'drift')

        # if drift status is not in sync, set failed flag
        if drift_status != 'IN_SYNC':
            failed = True
            print('**** WARNING ****, stack {} out of drift: {}'.format(stack, response))

    if failed:
        print('Stacks were detected to be out of sync, please address.')
        exit(-1)
    else:
        print('Successfully detected all stacks to be in sync.')
        exit(0)

