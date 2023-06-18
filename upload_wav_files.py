000import sys
import os
import subprocess
from dotenv import load_dotenv
from pathlib import Path
analysis_url = "https://api.dolby.com/media/analyze/speech"
from functions import get_access_token, analyze_speech, check_processing_status, upload_file_to_s3, create_bucket_if_not_exists

# Load environment variables from .env file
load_dotenv()

print("APP_KEY:", os.getenv('APP_KEY'))
print("APP_SECRET:", os.getenv('APP_SECRET'))
print("AWS_ACCESS_KEY_ID:", os.getenv('AWS_ACCESS_KEY_ID'))
print("AWS_SECRET_ACCESS_KEY:", os.getenv('AWS_SECRET_ACCESS_KEY'))


# Get invitation_number from arguments if provided, else prompt the user
invitation_number = sys.argv[1] if len(sys.argv) > 1 else input("Enter invitation number: ")

# Define folder path
folder_path = fr"P:\LR\Vintage-Phone-Orders\Post-Receive\{invitation_number}"

# Check if S3 bucket exists, if not create it
S3_BUCKET_NAME = "lifeonrecord-sound-enhancement"  # Add this line
create_bucket_if_not_exists(S3_BUCKET_NAME)

# Process all WAV files in the folder
jobs = []
for file_path in Path(folder_path).glob('*.wav'):
    file_name = file_path.stem

    # Skip files with the prefix db_
    if file_name.startswith("db_"):
        continue

    print(f"Processing {file_name}...")

    # Upload input file to Amazon S3 bucket
    upload_file_to_s3(file_path, f'{invitation_number}/{file_name}.wav')

    # Start analyze job
    access_token = get_access_token()  # Add this line
    job_id = analyze_speech(access_token, S3_BUCKET_NAME, invitation_number, file_name)  # Modify this line
    if job_id:
        jobs.append(job_id)

# Wait for all analysis jobs to complete
access_token = get_access_token()  # Add this line
for job_id in jobs:
    check_processing_status(access_token, job_id, analysis_url)  # Modify this line

# Call next script at the end
subprocess.run(["python", "enhance_wav_files.py", str(invitation_number)])
