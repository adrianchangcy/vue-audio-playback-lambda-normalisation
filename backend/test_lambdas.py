#Django
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

#apps
from voicewake.services import *
from django.conf import settings

#these involve AWS in one way or another
#for test cases with Redis, only way to guarantee cache isolation have unique target_user for every test case
#cannot chain first+next+last attempts in one single test case, because we're also testing how cache is guaranteed to exist at all attempts
@override_settings(
    DEBUG=True,
    CELERY_TASK_ALWAYS_EAGER=True,
)
class Core_NormaliseAudioClips_TestCase(TestCase):

    @classmethod
    def setUpTestData(cls):

        cls.users = []

        for x in range(0, 6):

            current_user = get_user_model().objects.create_user(
                username='useR'+str(x),
                email='user'+str(x)+'@gmail.com',
            )

            current_user = get_user_model().objects.get(username_lowercase="user"+str(x))

            current_user.is_active = True
            current_user.save()

            cls.users.append(current_user)

        #local file paths
        cls.shorter_audio_file_full_path = os.path.join(
            settings.BASE_DIR,
            'voicewake/tests/file_samples/audio_ok_10s.webm'
        )
        cls.longer_audio_file_full_path = os.path.join(
            settings.BASE_DIR,
            'voicewake/tests/file_samples/audio_ok_120s.webm'
        )
        cls.faulty_audio_file_full_path_0 = os.path.join(
            settings.BASE_DIR,
            'voicewake/tests/file_samples/txt_as_fake_webm.webm'
        )
        cls.faulty_audio_file_full_path_1 = os.path.join(
            settings.BASE_DIR,
            'voicewake/tests/file_samples/audio_not_mp3.wav'
        )

        #files
        with open(cls.shorter_audio_file_full_path, 'rb') as file_stream:
            cls.shorter_audio_clip_audio_file=SimpleUploadedFile('sample_audio_file.webm', file_stream.read(), 'audio/webm')

        #objects in s3 should exist before starting tests

        #unprocessed/processed object keys in S3
        cls.unprocessed_object_key = 'test/audio_ok_10s.webm'
        cls.processed_object_key = 'test/audio_ok_10s.mp3'

        #ensure test files exist in s3 before we run tests
        cls._prepare_s3_unprocessed_audio_file(
            unprocessed_object_key=cls.unprocessed_object_key,
            file_extension='webm',
            local_file_path=cls.shorter_audio_file_full_path
        )

        #ensure faulty file exists
        cls.faulty_audio_file_unprocessed_object_key_0 = 'test/text_as_fake_webm.webm'
        cls.faulty_audio_file_unprocessed_object_key_1 = 'test/audio_not_mp3.wav'

        cls._prepare_s3_unprocessed_audio_file(
            unprocessed_object_key=cls.faulty_audio_file_unprocessed_object_key_0,
            file_extension='webm',
            local_file_path=cls.faulty_audio_file_full_path_0
        )


    @staticmethod
    def _prepare_s3_unprocessed_audio_file(
        unprocessed_object_key:str,
        file_extension:str,
        local_file_path:str,
        force_upload:bool=False,
    ):

        s3_wrapper_class = S3PostWrapper(
            is_ec2=False,
            allowed_unprocessed_file_extensions=settings.AUDIO_CLIP_UNPROCESSED_FILE_EXTENSIONS,
            region_name=settings.AWS_S3_REGION_NAME,
            unprocessed_bucket_name=settings.AWS_S3_UGC_UNPROCESSED_BUCKET_NAME,
            s3_audio_file_max_size_b=settings.AWS_S3_AUDIO_FILE_MAX_SIZE_B,
            url_expiry_s=settings.AWS_S3_UPLOAD_URL_EXPIRY_S,
            aws_access_key_id=settings.AWS_S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
        )

        if force_upload is False:

            object_exists = s3_wrapper_class.check_object_exists(key=unprocessed_object_key)

            if object_exists is True:

                print(unprocessed_object_key + ' exists. Continuing...')
                return

        #upload

        upload_info = s3_wrapper_class.generate_unprocessed_presigned_post_url(
            key=unprocessed_object_key,
            file_extension=file_extension,
        )

        S3PostWrapper.s3_post_upload(
            url=upload_info['url'],
            fields=upload_info['fields'],
            local_file_path=local_file_path,
        )


    def test_lambda_normalise_audio_clips_ok(self):

        #swap the unprocessed test file in s3 here
        # self._prepare_s3_unprocessed_audio_file(
        #     unprocessed_object_key=self.unprocessed_object_key,
        #     file_extension='webm',
        #     local_file_path=self.shorter_audio_file_full_path,
        #     force_upload=True
        # )

        lambda_wrapper = AWSLambdaWrapper(
            is_ec2=False,
            timeout_s=settings.AWS_LAMBDA_NORMALISE_TIMEOUT_S,
            region_name=settings.AWS_LAMBDA_REGION_NAME,
            aws_access_key_id=settings.AWS_LAMBDA_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_LAMBDA_SECRET_ACCESS_KEY,
        )

        lambda_response_data = lambda_wrapper.invoke_normalise_audio_clips_lambda(
            s3_region_name=settings.AWS_S3_REGION_NAME,
            unprocessed_object_key=self.unprocessed_object_key,
            processed_object_key=self.processed_object_key,
            unprocessed_bucket_name=settings.AWS_S3_UGC_UNPROCESSED_BUCKET_NAME,
            processed_bucket_name=settings.AWS_S3_MEDIA_BUCKET_NAME,
        )

        print(lambda_response_data)

        #optimisation notes
            #normalisation is the only truly expensive step
                #e.g.:
                    #sample A (10s, 168kb, 128mb memory)
                        # {
                        #     'retrieve_unprocessed_audio_file': 0.561773,
                        #     'prepare_info_before_normalise': 0.060362,
                        #     'normalise_and_overwrite_audio_file': 9.418502,
                        #     'get_duration_after_normalise': 0.078297,
                        #     'get_peaks_by_buckets': 0.541153,
                        #     'store_processed_audio_file': 0.619966
                        # }
                        #cold start test case duration: 27s
                        #warm start test case duration: 16s
                    #sample B (120s, 1.85mb, 512mb memory)
                        # {
                        #     'retrieve_unprocessed_audio_file': 0.254644,
                        #     'prepare_info_before_normalise': 0.54729,
                        #     'normalise_and_overwrite_audio_file': 25.239503,
                        #     'get_duration_after_normalise': 0.024484,
                        #     'get_peaks_by_buckets': 1.093865,
                        #     'store_processed_audio_file': 0.265412
                        # }
                        #cold start test case duration: 35s
                        #warm start test case duration: 32s
            #memory results for processing 10s and maximum 120s:
                #tested with 3 tries
                    #on memory change, first try is always slower, and 2nd and 3rd are almost the same
                #128mb
                    #168kb: 9s normalise, cold 27s, warm 16s
                    #1.85mb: >60s, timed out
                #512mb
                    #168kb: 2.5s normalise, cold 11s, warm 8s
                    #1.85mb: 25s normalise, cold 35s, warm 32s
                #1024mb
                    #168kb: 1.4s normalise, cold 8s, warm 6s
                    #1.85mb: 12s normalise, cold 20s, warm 18s
                #1536mb
                    #168kb: 0.9s normalise, cold 7s, warm 6s
                    #1.85mb: 8s normalise, cold 15s, warm 13s
                #conclusion
                    #not urgent
                    #1536mb memory at 3*512mb took 8s instead of 6s to normalise
                    #1024mb is the winner

