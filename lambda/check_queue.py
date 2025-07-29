import json
import boto3
import os
import random

sqs = boto3.client("sqs")
ec2 = boto3.client("ec2")

QUEUE_URL = os.environ["QUEUE_URL"]
QUEUE_URL_2 = os.environ["QUEUE_URL_2"]
INSTANCE_ID = os.environ["INSTANCE_ID"]


def handler(event, context):
    try:
        print("Received event:", json.dumps(event))

        # 1. Extract query parameters
        params = event.get("queryStringParameters") or {}

        annotated = params.get("Annotated", "true").lower() == "true"
        name = params.get("Device", "default_client_default_device")
        start_time = params.get("Start_Time", "00:00:00")
        end_time = params.get("End_Time", random.randint(1, 100000000))
        date = params.get("Date", "12-01-2025")
        email = params.get("Email", None)
        api_test_model = params.get("api_test_model", "false").lower() == "true"
        client_number = params.get("clientNumber", None)
        # Parse selected models (comma-separated, max 4, distinct)
        selected_models_param = params.get("selected_models", "")
        optimize_report = params.get("optimize_report", "false").lower() == "true"
        model_list = list(
            {m.strip() for m in selected_models_param.split(",") if m.strip()}
        )
        # if len(model_list) > 4:
        #     raise ValueError("You can select a maximum of 4 distinct models.")
        # model1, model2, model3, model4 = (model_list + [None]*4)[:4]
        if len(model_list) == 0:
            api_test_model = "false"
        # 2. Parse client and device
        if not name:
            raise ValueError("Missing 'Device' parameter")
        parts = name.split("_")
        client = parts[0]
        device = name

        # 3. Parse optional body for POST
        form_data = {}
        if event.get("body"):
            try:
                form_data = json.loads(event["body"])
            except Exception:
                print("Invalid JSON body; ignoring.")

        # 4. Merge final payload
        transformed_data = {
            "Client": client,
            "Device": device,
            "Client Number": client_number,
            "Date": date,
            "Start Time": start_time,
            "End Time": end_time,
            "Video Name": form_data.get("Video Name", ""),
            "FPS": float(form_data.get("FPS", 10.0)),
            "Delete Decrypted Images": form_data.get("Delete Decrypted Images", "No"),
            "Run Inference": form_data.get("Run Inference", "No"),
            "Graph": form_data.get("Graph", ""),
            "Network": form_data.get("Network", ""),
            "OID Network": form_data.get("OID Network", "No"),
            "Fixed BBOX": form_data.get("Fixed BBOX", ["No", []]),
            "Hybrid Encryption": form_data.get("Hybrid Encryption", "Yes"),
            "Zipped Folder": form_data.get("Zipped Folder", False),
            "Fullday Video": form_data.get("Fullday Video", True),
            "Annotated": annotated,
            "Email": email,
            "api_test_model": api_test_model,
            "Model": model_list,
            "optimize_report": optimize_report,
        }
        if "Analysis Data" in model_list:
            response = sqs.get_queue_attributes(
                QueueUrl=QUEUE_URL_2,
                AttributeNames=[
                    "ApproximateNumberOfMessages",
                    "ApproximateNumberOfMessagesNotVisible",
                ],
            )

        # 5. Get SQS Queue status
        else:
            response = sqs.get_queue_attributes(
                QueueUrl=QUEUE_URL,
                AttributeNames=[
                    "ApproximateNumberOfMessages",
                    "ApproximateNumberOfMessagesNotVisible",
                ],
            )

        # 6. EC2 startup logic
        ec2_state = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
        instance_state = ec2_state["Reservations"][0]["Instances"][0]["State"]["Name"]
        if "Analysis Data" not in model_list:
            if instance_state == "stopped":

                ec2.start_instances(InstanceIds=[INSTANCE_ID])
                ec2_action = "EC2 instance starting."
            else:

                ec2_action = f"EC2 instance already {instance_state}."

            # 7. Send to SQS
            print("Sending to SQS:", transformed_data)
        if "Analysis Data" not in model_list:
            sqs.send_message(
                QueueUrl=QUEUE_URL,
                MessageBody=json.dumps(transformed_data),
                MessageGroupId=str(random.randint(1, 100000000)),
            )
        else:
            sqs.send_message(
                QueueUrl=QUEUE_URL_2,
                MessageBody=json.dumps(transformed_data),
            )
            ec2_action = "Not needed"

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps(
                {
                    "message": "Form received and processed.",
                    "ec2_status": ec2_action,
                    "ApproximateNumberOfMessages (Visible)": response["Attributes"][
                        "ApproximateNumberOfMessages"
                    ],
                    "ApproximateNumberOfMessagesNotVisible (In-Flight)": response[
                        "Attributes"
                    ]["ApproximateNumberOfMessagesNotVisible"],
                    "Form": transformed_data,
                }
            ),
        }

    except Exception as e:
        print("Error:", str(e))
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }
