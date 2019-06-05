import json
import boto3
import argparse
import time


class ChangeSetHandler(object):
    def __init__(self, stack_name, cf_client):
        self.client = cf_client
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

    def wait(self, interval):
        """
        wait for change set to execute
        :param interval: amount of time to sleep each time
        :return: stack_status
        """
        while True:
            time.sleep(interval)
            status = self.client.describe_stacks(StackName=self.stack_name)['Stacks'][0]['StackStatus']

            if status == 'CREATE_COMPLETE' or \
                    status == 'UPDATE_COMPLETE' or \
                    status == 'ROLLBACK_COMPLETE' or \
                    status == 'UPDATE_ROLLBACK_COMPLETE':
                return status


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

    # get the latest change set name and details
    ch = ChangeSetHandler(args.StackName, cf)
    change_set_name, change_set_details = ch.get_latest_change_set_details()

    # execute change set identified from above
    response = ch.execute_change_set(change_set_name)
    response_code = response['ResponseMetadata']['HTTPStatusCode']
    change_set_details['ResponseCode'] = response_code
    if response_code == 200:
        print('Executed Latest Change Set Successfully..')
    else:
        print(json.dumps(response, indent=4, sort_keys=True, default=str))

    stack_status = ch.wait(30)

    # todo do something with change_set_name, change_set_details, stack_status

    print('Stack: {} completed with Status: {}'.format(args.StackName, stack_status))
    # print('Resources found for this stack are: {}'.format(stack_list))
    if stack_status == 'ROLLBACK_COMPLETE' or stack_status == 'UPDATE_ROLLBACK_COMPLETE':
        print('Stack deployment was not successful')
        exit(-1)
