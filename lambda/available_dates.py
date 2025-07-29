import boto3
import os
from collections import defaultdict
import json
from datetime import datetime, timedelta

s3 = boto3.client("s3")
global dates
dates = defaultdict(list)


def get_dates(device_name):

    global dates
    end_date = datetime(datetime.now().year, 1, 1)
    start_date = datetime.now()
    delta = timedelta(days=1)

    current_date = start_date
    while current_date >= end_date:
        date = current_date.strftime("%Y-%m-%d")
        date_ad = current_date + delta
        date_ad = date_ad.strftime("%Y-%m-%d")
        client_name = device_name.split("_")[0]
        prefix = f"{client_name}-raw-data/{device_name}/{date}/all_frames/all_frames/"
        # print(prefix)
        response = s3.list_objects_v2(Bucket=f"{client_name}-pilot", Prefix=prefix)
        # print(response)
        if "Contents" in response:
            total_size = sum(obj["Size"] for obj in response["Contents"])
            # print(total_size)
            if total_size > 20 * 1024 * 1024:  # 20MB in bytes
                # print(f"Folder size for date {date} ,{client_alias} exceeds 20MB: {total_size / (1024 * 1024):.2f} MB")
                dates[device_name].append(date_ad)

                if len(dates[device_name]) > 10:
                    return dates[device_name]
        # print(f"Folder size for date {date} ,{client_alias} exceeds 20MB: {total_size / (1024 * 1024):.2f} MB")
        current_date -= delta
    return dates[device_name]


def handler(event, context):
    # print(event,event.headers["device"])

    device = event["queryStringParameters"].get("Device")  # Parse the JSON string
    # device = body["device"]
    print(device)
    date_list = get_dates(device)
    date_list = json.dumps(sorted(date_list, reverse=True)[:10])
    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": date_list,
    }
