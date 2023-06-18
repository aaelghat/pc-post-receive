import sys
from functions import download_enhanced_files

# Load environment variables from .env file
load_dotenv()

# Get invitation_number from arguments if provided, else prompt the user
invitation_number = sys.argv[1] if len(sys.argv) > 1 else input("Enter invitation number: ")

# Define folder path
folder_path = fr"P:\LR\Vintage-Phone-Orders\Post-Receive\{invitation_number}"

# Download enhanced files
download_enhanced_files(folder_path, invitation_number)
