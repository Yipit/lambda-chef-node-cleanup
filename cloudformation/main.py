import troposphere.awslambda
import troposphere.events
import troposphere.iam
from troposphere import Template, Ref, Parameter
from troposphere.events import Target


template = Template()

lambda_role = template.add_resource(troposphere.iam.Role(
    "ChefNodeCleanUpLambdaRole",
    Path='/',
    AssumeRolePolicyDocument={
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "sts:AssumeRole",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Effect": "Allow",
                "Sid": ""
            }
        ]
    },
    Policies=[
        troposphere.iam.Policy(
            PolicyName='CloudwatchEventsPolicy',
            PolicyDocument={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents"
                        ],
                        "Resource": "*"
                    }
                ]
            }
        )
    ]
))


bucket = Parameter('S3Bucket', Type='String', Description='S3 bucket to store clean up code')
template.add_parameter(bucket)
key = Parameter('S3Key', Type='String', Default='chef_cleanup.zip', Description='S3 key name to save clean up code (ZIP file)')
template.add_parameter(key)

lambda_function = template.add_resource(troposphere.awslambda.Function(
    "ChefCleanUpLambda",
    S3Bucket=Ref(bucket),
    S3Key=Ref(key),
    Role=troposphere.GetAtt(lambda_role, 'Arn'),
    Handler="main.handle",
    Description="Automatically delete nodes from Chef Server on termination",
    MemorySize=128,
    Runtime="python2.7",
    Timeout=5,
))

instance_termination_event_rule = template.add_resource(troposphere.events.Rule(
    "InstanceTerminationEventRule",
    DependsOn=lambda_role.title,
    EventPattern={
        "source": ["aws.ec2"],
        "detail-type": ["EC2 Instance State-change Notification"],
        "detail": {
            "state": ["terminated"]
        }
    },
    Description="Trigger the chef_node_cleanup Lambda when an instance terminates",
    Targets=[
        Target(Arn= troposphere.GetAtt(lambda_function, "Arn"), Id="TerminateInstanceLambdaFunction1")
    ],
))

lambda_permission = template.add_resource(troposphere.awslambda.Permission(
    "ChefCleanUpLambdaPermission",
    Action="lambda:InvokeFunction",
    FunctionName=Ref(lambda_function),
    Principal="events.amazonaws.com",
    SourceArn=troposphere.GetAtt(instance_termination_event_rule, 'Arn'),
))

print template.to_json()