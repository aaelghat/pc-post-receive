from dotenv import load_dotenv
from functions import download_enhanced_files
from pathlib import Path

load_dotenv()

folder_path = Path("enhanced_files")

invitation_number = input("Enter invitation number: ")

for file_path in folder_path.glob('*.wav'):
    file_name = file_path.stem
    download_enhanced_file(folder_path, invitation_number, file_name)
