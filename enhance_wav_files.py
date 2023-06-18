import sys
import subprocess
from functions import get_speech_segments
from dotenv import load_dotenv
from functions import get_access_token, transcode_file, enhance_file, check_processing_status, get_analysis_results

# Load environment variables from .env file
load_dotenv()

# Get invitation_number from arguments if provided, else prompt the user
invitation_number = sys.argv[1] if len(sys.argv) > 1 else input("Enter invitation number: ")

# Define folder path
folder_path = fr"P:\LR\Vintage-Phone-Orders\Post-Receive\{invitation_number}"

# Get all speech segments
speech_segments = get_speech_segments(folder_path, invitation_number)

# Start enhancement jobs
jobs = []
access_token = get_access_token()
for file_name, segments in speech_segments.items():
    for segment in segments:
        start_time, duration = segment
        # Skip non-speech segments longer than 2 seconds
        if duration > 2:
            continue
        # Transcode the file
        job_id = transcode_file(access_token, S3_BUCKET_NAME, invitation_number, file_name, start_time, duration)
        if job_id:
            jobs.append(job_id)

# Wait for all transcoding jobs to complete
for job_id in jobs:
    check_processing_status(access_token, job_id, transcode_url)

# Start enhancement jobs
jobs = []
for file_name in speech_segments.keys():
    job_id = enhance_file(access_token, S3_BUCKET_NAME, invitation_number, file_name)
    if job_id:
        jobs.append(job_id)

# Wait for all enhancement jobs to complete
for job_id in jobs:
    check_processing_status(access_token, job_id, enhance_url)

# Call next script at the end
subprocess.run(["python", "download_enhanced_files.py", str(invitation_number)])

