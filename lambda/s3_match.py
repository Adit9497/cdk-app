import boto3
import os
import json

s3 = boto3.client("s3")


def handler(event, context):
    bucket = os.environ["BUCKET_NAME"]
    CLOUDFRONT_DOMAIN = os.environ["CLOUDFRONT_DOMAIN"]
    response = s3.list_objects_v2(Bucket=bucket, Prefix="video/")
    videos = []
    if "Contents" in response:
        for obj in response["Contents"]:
            key = obj["Key"].lower()

            if key.endswith((".mp4", ".mov", ".avi", ".mkv")):
                key = obj["Key"].replace("video/", "")
                parts = key.split("_")
                print(parts)
                # Extract components
                client = parts[0]
                if "unannotated.mp4" in parts:
                    devicename = "_".join(parts[1:-3])
                    date = parts[-3]
                else:
                    devicename = "_".join(
                        parts[1:-2]
                    )  # everything between first and last two parts
                    date = parts[-2]
                print(client, devicename, date)
                videos.append(
                    {
                        "client": client,
                        "deviceName": devicename,
                        "date": date,
                        "name": os.path.basename(obj["Key"]),
                        "url": f"https://{CLOUDFRONT_DOMAIN}/video/{key}",
                        "last_modified": str(obj["LastModified"]),
                        "size": obj["Size"],
                    }
                )

    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,device",
            "Access-Control-Allow-Methods": "OPTIONS,GET,POST",
        },
        "body": json.dumps(videos),
    }
