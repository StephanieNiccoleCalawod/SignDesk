import os
import urllib.request

# Define the target directory where images should be saved
target_dir = r"c:\Users\Ideapad\OneDrive\Desktop\SignDesk\assets\reference"
os.makedirs(target_dir, exist_ok=True)

# Base URL pattern for the ASL alphabet reference images
base_url = "https://alphabetizer.flap.tv/lists/images/Sign_Language_{}.jpg"

# Loop through each letter A-Z and retrieve the image
for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    url = base_url.format(letter)
    dest_path = os.path.join(target_dir, f"Sign_Language_{letter}.jpg")
    print(f"Downloading {url} to {dest_path}...")
    try:
        urllib.request.urlretrieve(url, dest_path)
    except Exception as e:
        print(f"Error downloading {letter}: {e}")
        
print("Download complete.")
