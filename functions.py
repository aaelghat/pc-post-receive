import os
import boto3
import requests
import json
import time
from dotenv import load_dotenv
from pathlib import Path
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
analysis_url = "https://api.dolby.com/media/analyze"
transcode_url = "https://api.dolby.com/media/enhance"
enhance_url = "https://api.dolby.com/media/enhance"

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
        print(f'Full response body: {response.json()}')  # Print the entire response body
        return None


def check_processing_status(access_token, job_id, url):
    headers = {'Authorization': 'Bearer ' + access_token, 'Content-Type': 'application/json'}
    status_url = f"{url}?job_id={job_id}"  # Updated URL with job_id parameter
    print("Job status URL:", status_url)  # Print the job status URL
    while True:
        response = requests.get(status_url, headers=headers)
        print("Response code:", response.status_code)  # Print the response code
        print("Response text:", response.text)  # Print the response text
        print(f"Full response: {response.json()}")
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

def get_speech_segments(folder_path, invitation_number):
    speech_segments = {}
    for file_path in Path(folder_path).glob('*.wav'):
        file_name = file_path.stem
        # Skip files with the prefix db_
        if file_name.startswith("db_"):
            continue
        # Get analysis results
        analysis_results = get_analysis_results(invitation_number, file_name)
        if analysis_results:
            segments = []
            for segment in analysis_results.get('audio', {}).get('content', {}).get('speech', []):
                start_time = segment.get('start')
                duration = segment.get('duration')
                segments.append((start_time, duration))
            speech_segments[file_name] = segments
    return speech_segments


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

def get_analysis_results(invitation_number, file_name):
    # Define the URL for getting the analysis results
    url = f"https://api.dolby.com/media/analyze?job_id={invitation_number}_{file_name}"
    # Send a GET request to the URL
    response = requests.get(url, headers={'Authorization': 'Bearer ' + get_access_token()})
    # If the request was successful, return the results
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get analysis results for {file_name}. Response code: {response.status_code}")
        return None


def transcode_file(access_token, S3_BUCKET_NAME, invitation_number, file_name, start_time, duration):
    input_url = f"s3://{S3_BUCKET_NAME}/{invitation_number}/{file_name}.wav"
    output_url = input_url.replace(".wav", "_trimmed.wav")
    headers = {'Authorization': 'Bearer ' + access_token, 'Content-Type': 'application/json'}
    payload = {
        "input": input_url,
        "output": output_url,
        "segment": {
            "start": start_time,
            "duration": duration
        }
    }
    response = requests.post(transcode_url, headers=headers, json=payload)
    if response.status_code == 200:
        job_id = response.json().get('job_id')
        print(f'Successfully started transcoding job for {input_url}. Job ID: {job_id}.')
        return job_id
    else:
        print(f'Error starting transcoding job for {input_url}. Error Code: {response.status_code}')
        print(f'Error message: {response.text}')
        return None

def enhance_file(access_token, S3_BUCKET_NAME, invitation_number, file_name):
    input_url = f"s3://{S3_BUCKET_NAME}/{invitation_number}/{file_name}_trimmed.wav"
    output_url = input_url.replace("_trimmed.wav", "_enhanced.wav")
    headers = {'Authorization': 'Bearer ' + access_token, 'Content-Type': 'application/json'}
    payload = {
        "input": input_url,
        "output": output_url
    }
    response = requests.post(enhance_url, headers=headers, json=payload)
    if response.status_code == 200:
        job_id = response.json().get('job_id')
        print(f'Successfully started enhancement job for {input_url}. Job ID: {job_id}.')
        return job_id
    else:
        print(f'Error starting enhancement job for {input_url}. Error Code: {response.status_code}')
        print(f'Error message: {response.text}')
        return None

def download_enhanced_files(s3, S3_BUCKET_NAME, invitation_number, file_name):
    # Define the S3 key for the enhanced file
    s3_key = f"{invitation_number}/enhanced/{file_name}"
    # Define the local file path for the enhanced file
    local_file_path = f"P:/LR/Vintage-Phone-Orders/Post-Receive/{invitation_number}/enhanced/{file_name}"
    try:
        # Download the enhanced file from S3
        s3.download_file(S3_BUCKET_NAME, s3_key, local_file_path)
        print(f"Downloaded enhanced file to {local_file_path}")
    except NoCredentialsError:
        print("No AWS credentials were found.")
    except Exception as e:
        print(f"An error occurred while downloading the enhanced file: {e}")
