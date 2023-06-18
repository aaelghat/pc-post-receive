import sys
import subprocess
from functions import get_access_token, analyze_speech, check_processing_status, get_speech_segments, start_enhancement_jobs

# Load environment variables from .env file
load_dotenv()

# Get invitation_number from arguments if provided, else prompt the user
invitation_number = sys.argv[1] if len(sys.argv) > 1 else input("Enter invitation number: ")

# Define folder path
folder_path = fr"P:\LR\Vintage-Phone-Orders\Post-Receive\{invitation_number}"

# Get all speech segments
speech_segments = get_speech_segments(folder_path, invitation_number)

# Start enhancement jobs
jobs = start_enhancement_jobs(speech_segments, invitation_number)

# Wait for all enhancement jobs to complete
for job_id in jobs:
    check_processing_status(job_id)

# Call next script at the end
subprocess.run(["python", "download_enhanced_files.py", str(invitation_number)])
