import boto3
import os
import json

s3 = boto3.client("s3")


def handler(event, context):
    bucket = os.environ["BUCKET_NAME"]
    CLOUDFRONT_DOMAIN = os.environ["CLOUDFRONT_DOMAIN"]
    response = s3.list_objects_v2(Bucket=bucket, Prefix="vis_test/")
    pdf_evidance_response = s3.list_objects_v2(Bucket=bucket, Prefix="pdf_evidance/")
    list_pdf = []
    if "Contents" in pdf_evidance_response:
        for obj in pdf_evidance_response["Contents"]:
            key = obj["Key"].replace("pdf_evidance/", "")
            list_pdf.append(key)
    print(list_pdf)
    videos = []
    if "Contents" in response:
        for obj in response["Contents"]:
            key = obj["Key"].lower()

            if key.endswith((".mp4", ".mov", ".avi", ".mkv")):
                key = obj["Key"].replace("vis_test/", "")
                parts = key.split("_")
                # print(parts)
                # Extract components
                client = parts[0]
                devicename = "_".join(
                    parts[0:-2]
                )  # everything between first and last two parts
                date = parts[-2]
                # print(client, devicename, date)
                # Build video entry
                video_entry = {
                    "client": client,
                    "deviceName": devicename,
                    "date": date,
                    "name": os.path.basename(obj["Key"]),
                    "url": f"https://{CLOUDFRONT_DOMAIN}/vis_test/{key}",
                    "last_modified": str(obj["LastModified"]),
                    "size": obj["Size"],
                }

                pdf = key.split(".")[0] + ".pdf"
                if pdf in list_pdf:
                    video_entry["pdf_url"] = (
                        f"https://{CLOUDFRONT_DOMAIN}/pdf_evidance/{pdf}"
                    )
                else:
                    video_entry["pdf_url"] = None

                videos.append(video_entry)

    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,device",
            "Access-Control-Allow-Methods": "OPTIONS,GET,POST",
        },
        "body": json.dumps(videos),
    }
