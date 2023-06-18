import os
import boto3
import requests
import json
import time
from dotenv import load_dotenv
from botocore.exceptions import NoCredentialsError, BotoCoreError, ClientError

# Load environment variables from .env file
load_dotenv()

# Set your Dolby.io credentials
APP_KEY = os.getenv('APP_KEY')
APP_SECRET = os.getenv('APP_SECRET')

# Set your AWS credentials
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY')  # changed from AWS_ACCESS_KEY_ID
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY')  # changed from AWS_SECRET_ACCESS_KEY

# URLs
analysis_url = "https://api.dolby.com/media/analyze/speech"


# Initialize the S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY
)

S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')  # fetch from env variable

def get_access_token():
    payload = {'grant_type': 'client_credentials', 'expires_in': 1800}
    response = requests.post('https://api.dolby.io/v1/auth/token', data=payload, auth=requests.auth.HTTPBasicAuth(APP_KEY, APP_SECRET))
    body = json.loads(response.content)
    access_token = body['access_token']
    return access_token

def analyze_speech(access_token, S3_BUCKET_NAME, invitation_number, file_name):
    input_url = f"s3://{S3_BUCKET_NAME}/{invitation_number}/{file_name}.wav"
    headers = {'Authorization': 'Bearer ' + access_token, 'Content-Type': 'application/json'}
    payload = {
        "input": input_url,
        "output": input_url.replace(".wav", "_analysis.json")
    }
    response = requests.post(analysis_url, headers=headers, json=payload)
    if response.status_code == 200:
        job_id = response.json().get('job_id')
        print(f'Successfully started analysis job for {input_url}. Job ID: {job_id}.')
        return job_id
    else:
        print(f'Error starting analysis job for {input_url}. Error Code: {response.status_code}')
        print(f'Error message: {response.text}')
        return None

def check_processing_status(access_token, job_id, url):
    headers = {'Authorization': 'Bearer ' + access_token, 'Content-Type': 'application/json'}
    status_url = f"{url}?job_id={job_id}"  # Updated URL with job_id parameter
    print("Job status URL:", status_url)  # Print the job status URL
    while True:
        response = requests.get(status_url, headers=headers)
        print("Response code:", response.status_code)  # Print the response code
        print("Response text:", response.text)  # Print the response text
        if response.status_code == 200:
            status = response.json().get("status")
            if status == "Succeeded":
                print(f"Job {job_id} completed successfully.")
                return response.json()
            elif status == "Failed":
                print(f"Job {job_id} failed.")
                return None
            elif status == "In progress":
                print(f"Job {job_id} in progress. Status: {status}")
                time.sleep(5)
            elif status == "404" or status is None:
                print(f"Job {job_id} not found or status unknown.")
                print(f"Response: {response.json()}")
                return None
            else:
                print(f"Job {job_id} in an unexpected state. Status: {status}")
                return None
        else:
            print(f"Failed to retrieve job status for {job_id}.")
            return None




def upload_file_to_s3(file_path, s3_file_path):
    try:
        s3.upload_file(str(file_path), S3_BUCKET_NAME, s3_file_path)
        print(f"File uploaded to {s3_file_path}")
    except NoCredentialsError:
        print("No credentials to access S3")
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred while uploading the file: {e}")

def create_bucket_if_not_exists(bucket_name):
    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"Bucket {bucket_name} already exists.")
    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            print(f"Bucket {bucket_name} does not exist. Creating bucket.")
            try:
                s3.create_bucket(Bucket=bucket_name)
                print(f"Bucket {bucket_name} created successfully.")
            except BotoCoreError as e:
                print(f"Error creating bucket: {e}")
        else:
            print(f"Error accessing bucket: {e}")
