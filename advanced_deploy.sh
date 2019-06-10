#!/usr/bin/env bash
stack_name="cft-advanced"
region="us-west-2"
package="templates/package-template.yaml"
templates_bucket="cft-deployments"
capabilities="CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND"
params="NamingPrefix=${stack_name} Email=someone@noreply.com"
tags="Name=${stack_name}"
profile="mine"

taskcat -c ci/taskcat.yml -l -P mine

echo "Detecting Drifts.."
python3 advanced_cft/handle_drift.py ${stack_name} ${region} ${profile}
if [[ "$?" != "0" ]]; then exit -1
else echo "No Drifts detected, continuing with deployment"
fi

echo ""
echo "Building deployment package ${package} for stack ${stack_name}"
aws cloudformation package --region ${region} --template-file templates/main.yaml --s3-bucket ${templates_bucket} --s3-prefix ${stack_name} --output-template-file ${package} --profile ${profile}

echo ""
echo "Deploying package ${package} for stack ${stack_name}"
aws cloudformation deploy --region ${region} --template-file ${package} --stack-name ${stack_name} --s3-bucket ${templates_bucket} --s3-prefix ${stack_name} --parameter-overrides ${params} --capabilities ${capabilities} --tags ${tags} --no-execute-changeset --profile ${profile}

rm -rf ${package}

echo ""
echo "Executing Change Set.."
python3 advanced_cft/handle_change_set.py ${stack_name} ${region} ${profile}