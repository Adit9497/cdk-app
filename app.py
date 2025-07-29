#!/usr/bin/env python3
import aws_cdk as cdk
from cdk_app.cdk_app_stack import CdkAppStack

app = cdk.App()
stack = CdkAppStack(app, "MyAppStack")

cdk.CfnOutput(stack, "ApiEndpoint", value=stack.api_url_output)
app.synth()
