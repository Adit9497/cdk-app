import boto3

# import os (removed as it is not accessed)
import json
import logging
from botocore.exceptions import ClientError
import psycopg2

# from psycopg2.errorcodes import UNIQUE_VIOLATION (removed as it is not accessed)
# from psycopg2 import errors (removed as it is not accessed)

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_ssm_parameter(
    *,
    parameter_name: str,
    with_decryption: bool = True,
    region_name: str = "ca-central-1",
):
    """
    Retrieve a parameter from AWS Systems Manager Parameter Store.

    :param parameter_name: The name or path of the parameter to retrieve
    :param with_decryption: Whether to decrypt the parameter (default is True)
    :return: The parameter value, or None if an error occurs
    """
    ssm = boto3.client(
        "ssm",
        region_name=region_name,
    )
    logger.info(f"Attempting to retrieve parameter: {parameter_name}")
    try:
        response = ssm.get_parameter(
            Name=parameter_name, WithDecryption=with_decryption
        )
        logger.info("Successfully received parameters")
        return response["Parameter"]["Value"]
    except ClientError as e:
        logger.error(f"ClientError when retrieving parameter {parameter_name}: {e}")
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error when retrieving parameter {parameter_name}: {e}"
        )
        return None


client = boto3.client("rds-data")
parameters_string = get_ssm_parameter(parameter_name="/rds/credentials")

if parameters_string is None:
    raise Exception("error getting SSM params")
if parameters_string is not None:
    credentials = json.loads(parameters_string)

port = credentials.get("port", 5432)
database = credentials.get("database", "postgres")
host = credentials.get("host")
user = credentials.get("user")
password = credentials.get("password")


def get_all_data():

    conn = psycopg2.connect(
        host=host,  # Connect to the local forwarded port
        port=port,
        dbname=database,
        user=user,
        password=password,
    )
    cur = conn.cursor()

    # handles empty or whitespace-only strings
    cur.execute(
        """select client_alias, device_alias, device_name, client_number from device_information where client_alias is not null and status in ('Active')"""
    )
    result = {}

    rds_response = cur.fetchall()
    for row in rds_response:
        client_alias = row[0]
        device_alias = row[1]
        device_name = row[2]
        client_number = row[3]

        # Skip if any required field is missing
        if not all([client_alias, device_name]):
            continue
        elif not device_alias:
            device_alias = device_name

        # Create nested dictionary structure
        if client_alias not in result:
            result[client_alias] = {}

        result[client_alias][device_alias] = {
            "device_name": device_name,
            "client_number": client_number,
        }
    cur.close()
    conn.close()
    # ssh_process.terminate()
    return result


def handler(event, context):  # event and context are required by AWS Lambda
    # _ = event  # Explicitly ignore unused parameter
    # _ = context  # Explicitly ignore unused parameter

    result = json.dumps(get_all_data())
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",  # Allow requests from any origin
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent",
            "Access-Control-Allow-Methods": "OPTIONS,GET",
        },
        "body": result,
    }
