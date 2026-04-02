#Django libraries
from django.conf import settings

#Python
from datetime import datetime
from zoneinfo import ZoneInfo
import secrets
import json
import logging
import requests

#AWS
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

#app files
from voicewake.models import *
from voicewake.serializers import *



def custom_error(error_class:Exception, __name__context:str, dev_message="", user_message="")->Exception:

    #demo
    # try:
    #     raise custom_error(ValueError, __name__, "yo fix this", "hehe oops")
    # except ValueError as e:
    #     print(get_user_message_from_custom_error(e))
    #     raise custom_error(e, __name__, e)

    #some exceptions contain non-strings instead, so always ensure dev_message is str() so we can log the entire thing
    dev_message = str(dev_message)

    #for now, we only log errors that are meant for developers
    if dev_message != "":

        logger = None

        #determine whether to use local file or AWS CloudWatch

        #pass __name__ into __name__context, which returns strings such as voicewake.views.... from which __name__ was called
        #can specify __name__ that does not yet exist, which will be auto-created
        logger = logging.getLogger(__name__context)

        #log, with attention to logger's severity level
        #only log at equal or higher severity
        logger.exception(__name__context + " : " + dev_message)

    #pass {} into Exception as *args, which can later be retrieved with Exception.args[0]
    return error_class({
        "dev_message": dev_message,
        "user_message": user_message
    })

def get_user_message_from_custom_error(new_error:Exception)->str:

    try:
        return new_error.args[0]['user_message']
    except:
        return ""

def get_dev_message_from_custom_error(new_error:Exception)->str:

    try:
        return new_error.args[0]['dev_message']
    except:
        return ""


def get_datetime_now(to_string:bool=False):

    datetime_now = datetime.now().astimezone(tz=ZoneInfo('UTC'))

    if to_string is True:

        #exact format, which datetime.datetime and Django's models.DateTimeField uses
        #%f is microseconds
        return datetime_now.strftime('%Y-%m-%d %H:%M:%S.%f %z')
    
    return datetime_now

    #to get difference
        #minutes_passed = (get_datetime_now() - event_reply_queue.when_locked).total_seconds() / 60
        #hours_passed = (get_datetime_now() - event_reply_queue.when_locked).total_seconds() / 60 / 60



class S3PostWrapper:

    def __init__(
        self,
        is_ec2:bool,
        allowed_unprocessed_file_extensions:list,
        region_name:str,
        s3_audio_file_max_size_b:int,
        unprocessed_bucket_name:str,
        url_expiry_s:int=1000,
        key_exist_retries:int=4,
        post_max_attempts:int=10,
        aws_access_key_id:str='',
        aws_secret_access_key:str='',
    ):

        #process flow
            #frontend POSTs with CSRF token --> backend --> generate pre-signed S3 URL --> ...
            #... --> frontend POSTs to pre-signed S3 URL --> S3 returns 204/422 when done --> ...
            #... --> frontend POSTs to backend --> ...
            #... --> backend receives file info --> POSTs to Lambda via RequestResponse --> ...
            #... --> if Lambda ok, return 200, else delete file in S3 if found

        #policies, if possible
            #1 bucket to dump all unprocessed user files
                #auto-delete if file remains past x days
                #allow only PUT
                #allow only 1 file upload per pre-signed S3 URL
            #1 bucket for processed files
                #proper folder pathing
                #fully private

        #we use POST via generate_presigned_post(), instead of generate_presigned_url()
        #we can have better control over policies and criterias this way

        #passed values
        #os.environ[] always returns string, so we convert
        self.is_ec2 = is_ec2
        self.allowed_unprocessed_file_extensions = allowed_unprocessed_file_extensions
        self.unprocessed_bucket_name = unprocessed_bucket_name
        self.s3_audio_file_max_size_b = int(s3_audio_file_max_size_b)
        self.url_expiry_s = int(url_expiry_s)
        self.key_exist_retries = key_exist_retries

        #S3

        self.s3_client = None

        advanced_config = Config(
            retries={
                'max_attempts': post_max_attempts,
                'mode': 'standard'
            }
        )

        try:

            if is_ec2 is True:

                self.s3_client = boto3.client(
                    service_name='s3',
                    region_name=region_name,
                    config=advanced_config,
                )

            else:

                self.s3_client = boto3.client(
                    service_name='s3',
                    region_name=region_name,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    config=advanced_config,
                )

        except ClientError:

            raise custom_error(
                ValueError,
                __name__,
                dev_message='Could not create S3 boto client.',
                user_message='Upload is temporarily unavailable.'
            )


    def check_bucket_exists(self, bucket:str)->bool:

        try:

            #requires "s3:ListBucket" policy
            response = self.s3_client.head_bucket(
                Bucket=bucket,
            )

            if response['ResponseMetadata']['HTTPStatusCode'] != 200:

                raise ValueError('Expected 200 but received ' + str(response['ResponseMetadata']['HTTPStatusCode']))

            return True
        
        except ClientError as e:

            if e.response['ResponseMetadata']['HTTPStatusCode'] == 404:

                return False

            raise e


    def check_object_exists(self, key:str)->bool:

        try:

            #requires "s3:GetObject" and "s3:ListBucket" policy
            response = self.s3_client.head_object(
                Bucket=self.unprocessed_bucket_name,
                Key=key,
            )

            if response['ResponseMetadata']['HTTPStatusCode'] != 200:

                raise ValueError('Expected 200 but received ' + str(response['ResponseMetadata']['HTTPStatusCode']))

            return True

        except ClientError as e:

            if e.response['ResponseMetadata']['HTTPStatusCode'] == 404:

                return False

            raise e


    def generate_unprocessed_object_key(self, user_id:int, file_extension:str):

        if file_extension not in self.allowed_unprocessed_file_extensions:

            raise ValueError(
                file_extension + ' is invalid, must be one of: ' + str(self.allowed_unprocessed_file_extensions)
            )

        datetime_now = get_datetime_now()

        #determine early/first "folder"
        #important in the context of accurate settings + CloudFront origin to handle "/media/"
        #tests should ideally be done entirely in separate buckets, but can't afford 2 CloudFronts for now

        #no starting slash
        #.format() converts args into str for us
        #we want to set MEDIA_AWS_S3_START_PATH here, instead of determining via dev/prod at serializer
        #this helps to guarantee the separation between files created in dev and prod
        file_path = '{0}/audio_clips/year_{1}/month_{2}/day_{3}/user_id_{4}/'.format(
            settings.MEDIA_AWS_S3_START_PATH,
            datetime_now.strftime('%Y'),
            datetime_now.strftime('%m'),
            datetime_now.strftime('%d'),
            user_id,
        )

        #retry if full key exists

        for retry in range(0, self.key_exist_retries):

            #use secrets.token_hex() instead of AudioClips.id
            #ensures that all AudioClips have .audio_file
            file_key = file_path + secrets.token_hex(16) + '.' + file_extension

            if self.check_object_exists(file_key) is False:

                return file_key

        raise ValueError('Maximum retries reached on check_object_exists().')


    def generate_unprocessed_presigned_post_url(self, key:str, file_extension:str=''):

        #HTTP 422 on condition failure, will not upload
        #HTTP 204 on success
        #for file MimeType, e.g. allow only .mp3, must be done at bucket policy, not here
        #key will be available via upload_info['fields']['key']

        #if file_extension is not passed, determine from passed key
        #this happens when regenerating POST URL

        if len(file_extension) == 0:

            for unprocessed_file_extension in self.allowed_unprocessed_file_extensions:

                current_key_extension = key[
                    -len(unprocessed_file_extension):len(key)
                ]

                if current_key_extension == unprocessed_file_extension:

                    file_extension = unprocessed_file_extension
                    break

            #no match
            if len(file_extension) == 0:

                raise ValueError(
                    key + ' is not of ' + str(self.allowed_unprocessed_file_extensions)
                )

        elif file_extension not in self.allowed_unprocessed_file_extensions:

            raise ValueError(
                file_extension + ' is invalid, must be one of: ' + str(self.allowed_unprocessed_file_extensions)
            )

        conditions = [
            {'bucket': self.unprocessed_bucket_name},
            {'key': key},
            ["starts-with", "$Content-Type", f"audio/{file_extension}"],
            ["content-length-range", 1024, self.s3_audio_file_max_size_b],
        ]

        try:

            return self.s3_client.generate_presigned_post(
                Bucket=self.unprocessed_bucket_name,
                Key=key,
                Fields={"Content-Type": f"audio/{file_extension}"},
                Conditions=conditions,
                ExpiresIn=self.url_expiry_s
            )

        except ClientError as e:

            raise custom_error(
                ValueError,
                __name__,
                dev_message=f"Couldn't generate POST URL for key ({key}): {str(e)}",
                user_message='Upload is temporarily unavailable.'
            )


    @staticmethod
    def s3_post_upload(url, fields, local_file_path):

        with open(local_file_path, mode='rb') as object_file:

            object_file.seek(0)

            #must be 'file'
            #must be last field
            fields['file'] = object_file.read()

        #at Python, form fields are passed as files={}
        response = requests.post(
            url,
            files=fields
        )

        #always returns 204, regardless of whether file already exists in S3 or not
        #tested as of March 2024
        if response.status_code == 204:

            return

        print(response)
        raise ValueError(str(response.status_code) + ' is not 204')


    def delete_object(self, key:str):

        #requires "s3:DeleteObject" policy
        return self.s3_client.delete_object(
            Bucket=self.unprocessed_bucket_name,
            Key=key,
        )



class AWSLambdaWrapper:

    def __init__(
        self,
        is_ec2:bool,
        timeout_s:int=30,
        max_attempts:int=0,
        region_name:str='',
        aws_access_key_id:str='',
        aws_secret_access_key:str='',
    ):

        self.is_ec2 = is_ec2
        self.region_name = region_name

        #your_lambda --> Configuration --> General configuration --> Edit
        #the timeout value there has higher priority than here
        advanced_config = Config(
            retries={
                'max_attempts': max_attempts,
                'mode': 'standard'
            },
            read_timeout=timeout_s,
            connect_timeout=timeout_s,
        )

        try:

            if is_ec2 is True:

                self.client = boto3.client(
                    service_name='lambda',
                    region_name=region_name,
                    config=advanced_config,
                )

            else:

                self.client = boto3.client(
                    service_name='lambda',
                    region_name=region_name,
                    config=advanced_config,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                )

        except ClientError:

            raise


    def _invoke_lambda(self, function_name:str, payload:dict):

        #at Lambda, retrieve payload in lambda_handler via event.get('keyname')
        #be sure to standardise all Lambdas to return these at minimum:
            #{'lambda_status_code': int, 'lambda_message':str}

        payload = json.dumps(payload)
        payload = bytes(payload, encoding='utf-8')

        response = self.client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=payload
        )

        #get response

        #['Payload'] is StreamingBody object, so we use .read() to get bytes
        #StreamingBody object has no .seek(0), so .read() can only be used once
        #AWS Lambda serializes entire response to JSON
        response_data = response['Payload'].read()
        response_data = bytes(response_data).decode(encoding='utf-8')
        response_data = json.loads(response_data)

        return response_data


    #all params are for payload, and must match AWSLambdaNormaliseAudioClips.__init__()
    def invoke_normalise_audio_clips_lambda(
        self,
        s3_region_name:str='',
        unprocessed_object_key:str='',
        processed_object_key:str='',
        unprocessed_bucket_name:str='',
        processed_bucket_name:str='',
        is_ping:bool=False,
    ):

        #if you just want to check if lambda is ok, pass is_ping=True

        payload = {
            's3_region_name': s3_region_name,
            'unprocessed_object_key': unprocessed_object_key,
            'processed_object_key': processed_object_key,
            'unprocessed_bucket_name': unprocessed_bucket_name,
            'processed_bucket_name': processed_bucket_name,
            'is_ping': is_ping,
            'use_timer': settings.DEBUG,
        }

        return self._invoke_lambda(
            function_name=settings.AWS_LAMBDA_NORMALISE_FUNCTION_NAME,
            payload=payload
        )


