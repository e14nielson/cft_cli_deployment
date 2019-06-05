import boto3
import argparse
import time


class DriftHandler(object):
    def __init__(self, stack_name, cf_client):
        self.client = cf_client
        self.stack_name = stack_name

    def find_stacks(self):
        """
        Finds all the related stacks
        :return: list of matching stacks
        """
        sub_stacks = self.client.list_stack_resources(StackName=self.stack_name)['StackResourceSummaries']
        stack_names = []
        for sub_stack in sub_stacks:
            stack_names.append(sub_stack['PhysicalResourceId'])
        stack_names.append(self.stack_name)
        return stack_names

    def detect_drift(self, stack_name):
        """
        Detects the drift status of the given stack
        :param stack_name: name of stack to detect
        :return: StackDriftStatus
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
        return detection_status_response['StackDriftStatus']


if __name__ == "__main__":
    """
    Takes arguments when run from the command line
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("StackName", help="")
    parser.add_argument("Region", help="")
    parser.add_argument("ProfileName", help="")
    args = parser.parse_args()

    session = boto3.Session(profile_name=args.ProfileName)
    cf = session.client('cloudformation', region_name=args.Region)

    # get a list of our stacks once deployment is complete
    dh = DriftHandler(args.StackName, cf)
    stack_list = dh.find_stacks()

    failed = False
    for stack in stack_list:
        # detect if a drift has occurred on this individual stack
        drift_status = dh.detect_drift(stack)
        message = 'Stack: {} - Drift Status: {}'.format(stack, drift_status)

        # todo do something with stack, drift_status
        # if drift status is not in sync, set failed flag
        if drift_status != 'IN_SYNC':
            failed = True
            print('**** WARNING ****, stack {} drift status: {}'.format(stack, drift_status))

    if failed:
        print('Stacks were detected to be out of sync, please address.')
        exit(-1)
    else:
        print('Successfully detected all stacks to be in sync.')

