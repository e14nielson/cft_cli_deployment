#!/usr/bin/env bash
stack_name="cft-advanced"
region="us-west-2"
package="package-template.yaml"
bucket="cft-deployments"
capabilities="CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND"
params="NamingPrefix=${stack_name} Email=someone@noreply.com"
tags="Name=${stack_name}"
splunkurl="none"
profile="mine"

cd advanced_cft
echo "Building deployment package ${package} for stack ${stack_name}"
aws cloudformation package --region ${region} --template-file main.yaml --s3-bucket ${bucket} --output-template-file ${package} --profile ${profile}
echo "Deploying package ${package} for stack ${stack_name}"
aws cloudformation deploy --region ${region} --template-file ${package} --stack-name ${stack_name} --s3-bucket ${bucket} --s3-prefix ${stack_name} --parameter-overrides ${params} --capabilities ${capabilities} --tags ${tags} --no-execute-changeset --profile ${profile}
echo "Handling Change Sets.."
python3 handle_change_set.py ${stack_name} ${region} ${profile} ${splunkurl}

rm -rf ${package}