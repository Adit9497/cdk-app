import boto3
import logging
import json
from boto3.dynamodb.conditions import Key


def handler(event, context):
    """
    AWS Lambda handler to fetch data from DynamoDB for a given device.

    Args:
        event (dict): The event dict, expects 'device_name' key.
        context: Lambda context (unused).

    Returns:
        dict: Result with 'graph_folder' or error message.
    """
    device_name = event["queryStringParameters"].get("device_name")
    print(device_name)
    if not device_name:
        logging.error("Missing 'device_name' in event")
        {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": {"graph_folder": "None"},
        }

        # return {"error": "Missing 'device_name' in event"}
    try:
        logging.info(f"Device name: {device_name}")
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table("DeviceInformation")

        response = table.query(KeyConditionExpression=Key("DeviceName").eq(device_name))

        items = response.get("Items", [])
        if not items:
            logging.warning(f"No data found for device: {device_name}")
            return {"error": f"No data found for device: {device_name}"}
        graph_folder = items[0].get("Python Map", {}).get("graph_folder")
        print(graph_folder)
        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"graph_folder": graph_folder}),
        }
    except Exception as e:
        logging.error(f"Error querying DynamoDB: {e}")
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": {"error": str(e)},
        }
