from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_sqs as sqs,
)
import os
import dotenv

dotenv.load_dotenv()
from constructs import Construct


class CdkAppStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        queue = sqs.Queue(
            self,
            "MyFifoQueue",
            queue_name="MyFifoQueue.fifo",
            fifo=True,
            content_based_deduplication=True,
        )

        queue2 = sqs.Queue(
            self,
            "S3_orin_queue",
            queue_name="S3_orin_queue",
            fifo=False,
        )

        check_queue_fn = _lambda.Function(
            self,
            "CheckQueueLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="check_queue.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "QUEUE_URL": queue.queue_url,
                "INSTANCE_ID": os.environ.get("EC2_INSTANCE_ID", ""),
            },
        )
        dynamodb_fn = _lambda.Function(
            self,
            "DynamoDbLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="dynamodb_fn.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "DYNAMODB_TABLE": os.environ.get("DYNAMODB_TABLE", ""),
            },
        )

        dynamodb_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:PutItem",
                    "dynamodb:GetItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Scan",
                    "dynamodb:Query",
                ],
                resources=[
                    f"arn:aws:dynamodb:{os.environ.get('AWS_REGION', '*')}:{os.environ.get('AWS_ACCOUNT_ID', '*')}:table/{os.environ.get('DYNAMODB_TABLE', '*')}"
                ],
            )
        )
        available_dates = _lambda.Function(
            self,
            "AvailableDates",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="available_dates.handler",
            code=_lambda.Code.from_asset("lambda"),
        )
        check_models = _lambda.Function(
            self,
            "CheckModelLog",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="check_models.handler",
            code=_lambda.Code.from_asset("lambda"),
        )

        queue.grant_consume_messages(check_queue_fn)

        check_models.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:ListBucket", "s3:GetObject"],
                resources=["*"],
            )
        )

        query_rds_fn = _lambda.Function(
            self,
            "QueryRdsLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="query_rds.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "DB_SECRET": os.environ.get("RDS_SECRET_ARN", ""),
                "DB_RESOURCE_ARN": os.environ.get("RDS_RESOURCE_ARN", ""),
                "DB_NAME": os.environ.get("DATABASE_NAME", ""),
            },
        )

        s3_match_fn = _lambda.Function(
            self,
            "S3MatchLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="s3_match.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "BUCKET_NAME": os.environ.get("S3_BUCKET_NAME", ""),
                "CLOUDFRONT_DOMAIN": os.environ.get("CLOUDFRONT_DOMAIN", ""),
            },
        )

        s3_full_test = _lambda.Function(
            self,
            "S3FullTestLambda",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="s3_full_test.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={
                "BUCKET_NAME": os.environ.get("S3_BUCKET_NAME", ""),
                "CLOUDFRONT_DOMAIN": os.environ.get("CLOUDFRONT_DOMAIN", ""),
            },
        )

        check_queue_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "sqs:GetQueueAttributes",
                    "ec2:StartInstances",
                    "ec2:StopInstances",
                    "ec2:DescribeInstances",
                    "sqs:SendMessage",
                ],
                resources=["*"],
            )
        )

        s3_policy = iam.PolicyStatement(
            actions=["s3:ListBucket", "s3:GetObject"],
            resources=[
                "arn:aws:s3:::*-pilot",  # List access to any -pilot bucket
                "arn:aws:s3:::*-pilot/*",  # Read access to objects inside
            ],
        )

        available_dates.add_to_role_policy(s3_policy)

        query_rds_fn.add_to_role_policy(
            iam.PolicyStatement(actions=["rds-data:ExecuteStatement"], resources=["*"])
        )

        s3_match_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:ListBucket"],
                resources=[f"arn:aws:s3:::{'<your-bucket-name>'}"],
            )
        )

        s3_full_test.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:ListBucket", "s3:GetObject"],
                resources=[f"arn:aws:s3:::{os.environ.get('S3_BUCKET_NAME', '')}"],
            )
        )

        api = apigw.RestApi(
            self,
            "AppApi",
            rest_api_name="AppApi",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
            ),
        )

        api.root.add_resource("checkqueue").add_method(
            "GET", apigw.LambdaIntegration(check_queue_fn)
        )
        api.root.add_resource("queryrds").add_method(
            "GET", apigw.LambdaIntegration(query_rds_fn)
        )
        api.root.add_resource("s3match").add_method(
            "GET", apigw.LambdaIntegration(s3_match_fn)
        )
        api.root.add_resource("availabledates").add_method(
            "GET", apigw.LambdaIntegration(available_dates)
        )
        api.root.add_resource("s3testreport").add_method(
            "GET", apigw.LambdaIntegration(s3_full_test)
        )
        api.root.add_resource("checkmodel").add_method(
            "GET", apigw.LambdaIntegration(check_models)
        )

        api.root.add_resource("dynamodbfn").add_method(
            "GET", apigw.LambdaIntegration(dynamodb_fn)
        )

        self.api_url_output = api.url
