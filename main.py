"""
This script processes GKE cluster upgrade-related notifications
"""
# =============================================================================
# Imports
# =============================================================================
import os
import base64
import requests
import logging
import google.cloud.logging


def process_gke_notification_event(event, slack_channel):
    if "data" in event:
        # Shared Variables
        cluster = event["attributes"]["cluster_name"]
        cluster_resource = event["attributes"]["payload"]["resourceType"]
        location = event["attributes"]["cluster_location"]
        message = base64.b64decode(event["data"]).decode("utf-8")
        project = event["attributes"]["project_id"]

        # UpgradeEvent
        if "UpgradeEvent" in event["attributes"]["type_url"]:
            current_version = event["attributes"]["payload"]["currentVersion"]
            start_time = event["attributes"]["payload"]["operationStartTime"]
            target_version = event["attributes"]["payload"]["targetVersion"]
            title = "GKE Cluster Upgrade Notification :zap:"
            slack_data = {
                "username": "GKE Notifications",
                "icon_emoji": ":kubernetes:",
                "channel": slack_channel,
                "attachments": [
                    {
                        "color": "#9733EE",
                        "fields": [
                            {"title": title},
                            {
                                "title": "Project ID",
                                "value": project,
                                "short": "false",
                            },
                            {
                                "title": "Cluster",
                                "value": cluster,
                                "short": "false",
                            },
                            {
                                "title": "Location",
                                "value": location,
                                "short": "false",
                            },
                            {
                                "title": "Update Type",
                                "value": cluster_resource,
                                "short": "false",
                            },
                            {
                                "title": "Current Version",
                                "value": current_version,
                                "short": "false",
                            },
                            {
                                "title": "Target Version",
                                "value": target_version,
                                "short": "false",
                            },
                            {
                                "title": "Start Time",
                                "value": start_time,
                                "short": "false",
                            },
                            {
                                "title": "Details",
                                "value": message,
                                "short": "false",
                            },
                        ],
                    }
                ],
            }
            return slack_data
        else:
            logging.info(f"Skipping event {event['attributes']['type_url']}")
    else:
        logging.info("No event was passed into the function. Exiting.")


def send_notification_to_slack(event, context):
    """Background Cloud Function to be triggered by Pub/Sub.
    For sample messages refer to the json inputs in tests.
    """

    # Sending logs only when running in GCP and skipping it for local
    if os.getenv('CLOUD_LOGGING_ENABLED') == 'yes':
        client = google.cloud.logging.Client()
        client.setup_logging()

    try:
        logging.info("Incoming messageId {} published at {}".format(
            context.event_id, context.timestamp)
                     )

        slack_webhook_url = os.environ['SLACK_WEBHOOK_URL']
        slack_channel = os.environ['SLACK_NOTIFICATION_CHANNEL']

        # Print the event at the beginning for easier debug.
        logging.info("Event was passed into function and will be processed.")
        logging.info(event)

        slack_data = process_gke_notification_event(event, slack_channel)
        response = requests.post(slack_webhook_url, json=slack_data)

        if response.status_code != 200:
            logging.error(f"Failed to send the notification to slack \
                          '{response.status_code, response.text}'")
            logging.debug(response.request.json)
            raise Exception(response.status_code, response.text)
        else:
            logging.info("GKE Upgrade notification is successfully processed")
            return response
    except Exception as exception:
        logging.error(f"Failed to process the GKE upgrade event '{event}'")
        logging.error(exception)


# local development test configuration
if __name__ == "__main__":
    # os.environ['SLACK_WEBHOOK_URL'] = "slack-webhook-url"
    # os.environ['SLACK_NOTIFICATION_CHANNEL'] = "@marcel"
    os.environ['CLOUD_LOGGING_ENABLED'] = "false"

    upgrade_notification_event = {
        "@type": "type.googleapis.com/google.pubsub.v1.PubsubMessage",
        "attributes": {
            "cluster_location": "europe-west2",
            "cluster_name": "sandbox-gke-cluster",
            "payload": {
                'currentVersion': '1.21.5-gke.1802',
                'operation': 'operation-1645107677624-ab05d433',
                'operationStartTime': '2022-02-17T14:21:17.624225580Z',
                'resourceType': 'MASTER',
                'targetVersion': '1.21.6-gke.1500'},
            "project_id": "4325342324",
            "type_url":
                "type.googleapis.com/google.container.v1beta1.UpgradeEvent"
        },
        "data": "VGhpcyBpcyBhIHRlc3Qgbm90aWZpY2F0aW9uCg=="
    }

    class Context(object):
        pass

    context1 = Context()
    context1.event_id = '4111677166000558'
    context1.timestamp = '2022-02-17T14:21:18.801Z'
    send_notification_to_slack(upgrade_notification_event, context1)
