import json
import logging
import uuid

import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

user_table = boto3.resource('dynamodb').Table('userTable')
schedule_table = boto3.resource('dynamodb').Table('scheduleTable')


def batch_get_schedule(schedule_id_list):
    try:
        response = boto3.resource('dynamodb').batch_get_item(
            RequestItems={
                "scheduleTable": {
                    "Keys": list(map(lambda schedule_id: {"scheduleId": schedule_id}, schedule_id_list)),
                    "AttributesToGet": [
                        "scheduleId",
                        "scheduleTitle",
                        "targetArea",
                        "scheduleType"
                    ]
                }
            }
        )

        if "Responses" in response and len(response["UnprocessedKeys"]) == 0:
            return True, response["Responses"]
        return False, {
            'statusCode': 400,
            'body': json.dumps({
                "code": 400,
                "msg": "can not get schedule attributes"
            })
        }
    except Exception as e:
        logger.error(e)
        return False, {
            'statusCode': 400,
            'body': json.dumps({
                "code": 400,
                "msg": "schedule id doesn't exist"
            })
        }


def get_target_user(user_id):
    try:
        response = user_table.get_item(
            Key={
                "userId": user_id
            }
        )

        if "Item" in response and len(response["Item"]) != 0:
            # logger.debug(json.dumps(response, indent=2))
            return True, response
        return False, {
            'statusCode': 400,
            'body': json.dumps({
                "code": 400,
                "msg": "user can not be revised"
            })
        }
    except Exception as e:
        return False, {
            'statusCode': 400,
            'body': json.dumps({
                "code": 400,
                "msg": "user id doesn't exist"
            })
        }


def get_schedule_list(user_id, page_size=20, page_no=0):
    succ, response = get_target_user(user_id)
    if not succ:
        return response
    user_info = response["Item"]
    if "editableSchedules" not in user_info or len(
            user_info["editableSchedules"]) == 0:
        return {
            'statusCode': 200,
            'body': json.dumps([])
        }
    page_start = page_no * page_size
    page_end = min((page_no + 1) * page_size,
                   len(user_info["editableSchedules"]))
    schedule_id_list = user_info["editableSchedules"][page_start: page_end]
    succ, response = batch_get_schedule(schedule_id_list)
    if not succ:
        return response
    schedule_list = response["scheduleTable"]
    return {
        'statusCode': 200,
        'body': json.dumps(schedule_list)
    }


def create_schedule_in_db(schedule):
    try:
        schedule_table.put_item(Item=schedule)
        return True, None
    except Exception as e:
        return False, {
            'statusCode': 400,
            'body': json.dumps({
                "code": 400,
                "msg": str(e)
            })
        }


def create_schedule(user_id, target_area="", schedule_title=""):
    # generate schedule id
    schedule_id = "sche-" + str(uuid.uuid1())

    succ, response = get_target_user(user_id)
    if not succ:
        return response
    user_info = response["Item"]
    if schedule_title == "":
        schedule_title = user_info["userName"] + ": " + schedule_id
    schedule = {
        "scheduleId": schedule_id,
        "scheduleTitle": schedule_title,
        "targetArea": target_area,
        "ownerId": user_info["userId"],
        "editorIds": [],
        "scheduleType": "PRESELECT",
        "scheduleContent": dict()
    }
    succ, response = create_schedule_in_db(schedule)
    if not succ:
        return response
    return {
        'statusCode': 200,
        'body': json.dumps({
            "code": 200,
            "msg": json.dumps(schedule)
        })
    }


def lambda_handler(event, context):
    try:
        if event["httpMethod"].upper() == "GET":
            logger.info("event={}".format(json.dumps(event)))
            if "pageSize" not in event["queryStringParameters"]:
                page_size = 20
            else:
                page_size = event["queryStringParameters"]["pageSize"]
            if "pageNo" not in event["queryStringParameters"]:
                page_no = 0
            else:
                page_no = event["queryStringParameters"]["pageNo"]
            if "userId" not in event["queryStringParameters"]:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        "code": 400,
                        "msg": "missing user id"
                    })
                }
            else:
                user_id = event["queryStringParameters"]["userId"]
            return get_schedule_list(user_id, page_size=page_size, page_no=page_no)
        if event["httpMethod"].upper() == "POST":
            logger.info("event={}".format(json.dumps(event)))
            if "userId" not in event["queryStringParameters"]:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        "code": 400,
                        "msg": "missing user id"
                    })
                }
            else:
                user_id = event["queryStringParameters"]["userId"]
            if "targetArea" not in event["queryStringParameters"]:
                target_area = ""
            else:
                target_area = event["queryStringParameters"]["targetArea"]
            if "scheduleTitle" not in event["queryStringParameters"]:
                schedule_title = ""
            else:
                schedule_title = event["queryStringParameters"]["scheduleTitle"]
            return create_schedule(schedule_title=schedule_title, user_id=user_id, target_area=target_area)
    except Exception as e:
        return {
            'statusCode': 400,
            'body': json.dumps({
                "code": 400,
                "msg": "missing required parameters!"
            })
        }


if __name__ == '__main__':
    # get_test_event = {
    #     "resource": "/schedule/",
    #     "path": "/schedule/",
    #     "httpMethod": "GET",
    #     "queryStringParameters": {
    #         "pageSize": 20,
    #         "pageNo": 0,
    #         "userId": "test-editor"
    #     },
    #     "multiValueQueryStringParameters": {
    #         "pageSize": [
    #             20
    #         ],
    #         "pageNo": [
    #             0
    #         ],
    #         "userId": [
    #             "userId"
    #         ]
    #     },
    #     "pathParameters": {}
    # }
    # handler_response = lambda_handler(get_test_event, None)
    # print(json.dumps(handler_response, indent=2))
    post_test_event = {
        "resource": "/schedule/",
        "path": "/schedule/",
        "httpMethod": "POST",
        "queryStringParameters": {
            "targetArea": "New York",
            "userId": "test-editor"
        },
        "multiValueQueryStringParameters": {
            "targetArea": [
                "New York"
            ],
            "userId": [
                "test-editor"
            ],
        },
        "pathParameters": {}
    }
    handler_response = lambda_handler(post_test_event, None)
    print(json.dumps(handler_response, indent=2))
