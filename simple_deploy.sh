#!/bin/bash
stack_name="cft-simple"
region="us-west-2"
deploy_profile="mine"

cd simple_cft
cf_file="cft.yaml"
tag_file="tags.json"
param_file="params.json"

capabilities="CAPABILITY_NAMED_IAM"

aws cloudformation get-template --region ${region} --profile ${deploy_profile} --stack-name ${stack_name} &> /dev/null
if [[ "$?" != "0" ]]; then
 echo "Stack $stack_name does not currently exist.";
    aws cloudformation create-stack --profile ${deploy_profile} --region ${region} --stack-name ${stack_name} --template-body file://${cf_file} --tags file://${tag_file} --capabilities ${capabilities} --parameters file://${param_file}
else
 echo "Stack $stack_name currently exists.";
    aws cloudformation update-stack --profile ${deploy_profile} --region ${region} --stack-name ${stack_name} --template-body file://${cf_file} --tags file://${tag_file} --capabilities ${capabilities} --parameters file://${param_file}
fi