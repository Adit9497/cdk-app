import json
import boto3
import os
import datetime as dt


def get_next_friday(date):
    """
    Get the next Friday from the given date.

    Args:
        date (str): The input date in the format 'YYYY-MM-DD'.

    Returns:
        str: The next Friday's date in the format 'YYYY-MM-DD'.
    """
    tz_dt = dt.datetime.strptime(date, "%Y-%m-%d")

    if tz_dt.weekday() != 4:
        days_since_friday = (4 - tz_dt.weekday() + 7) % 7
        next_friday = tz_dt + dt.timedelta(days=days_since_friday)
        formatted_date = next_friday.strftime("%Y-%m-%d")
    else:
        formatted_date = tz_dt.strftime("%Y-%m-%d")

    return formatted_date


def handler(event, context):
    s3 = boto3.client("s3")

    # Load from environment variables
    s3_bucket = os.environ.get("S3_BUCKET", "vendor-analysis-webapp-production")
    output_prefix = os.environ.get("OUTPUT_PREFIX", "output/")
    models_bucket = os.environ.get("MODELS_BUCKET", "graph-pilot")
    models_prefix = os.environ.get("MODELS_PREFIX", "models/")

    # Extract parameters
    params = event.get("queryStringParameters") or {}
    device = params.get("device_name")
    client_number = params.get("ClientNumber")
    date = params.get("Date")
    # date = get_next_friday(date)

    if not device or not date:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Device and Date are required"}),
        }

    client_no = device.split("_")[-1]
    device = f"client-{client_number}_device-os{client_no}"

    csv_name = f"{device}_date-{date}_disposal.csv"
    csv_key = f"{output_prefix}client-{client_number}/{csv_name}"

    try:
        s3.head_object(Bucket=s3_bucket, Key=csv_key)
        csv_exists = True
    except s3.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            csv_exists = False
        else:
            raise

    # List models
    s3_models = boto3.client("s3")
    models = []
    paginator = s3_models.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=models_bucket, Prefix=models_prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith((".pt", ".onnx", ".h5", ".engine")):
                models.append(os.path.basename(key))

    # Options to return
    options = ["Logs"] + models
    if csv_exists:
        options.append("Analysis Data")

    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,device",
            "Access-Control-Allow-Methods": "OPTIONS,GET,POST",
        },
        "body": json.dumps({"options": options, "csv": [csv_exists, csv_key]}),
    }
