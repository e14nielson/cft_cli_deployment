# CloudFormation Template Deployments

* simple_deploy.sh - deploys simple_cft/cft.yaml in a simple way
* advanced_deploy.sh - deploys simple_cft/cft.yaml in an advanced way
* simple_cft/cft.yaml - the actual cloudformation template to be deployed
* simple_cft/params.json - file that contains all parameters for cft.yaml
* simple_cft/tags.json - file that contains all tags for cft.yaml
* templates/main.yaml - parent template that will deploy simple_cft/cft.yaml as a child stack
* advanced_cft/handle_change_set.py - used by advanced_deply.sh to handle changesets and drift detection
* advanced_cft/handle_drift.py - used by advance_deploy.sh to detect any drifts before executing deployment
* ci - taskcat required files
