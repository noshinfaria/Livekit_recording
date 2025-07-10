import os
import boto3
from botocore.client import Config

def download_recordings(download_dir="recordings"):
    s3 = boto3.client(
        "s3",
        aws_access_key_id="LTaGZLxaCHuvzwwwQDTR",
        aws_secret_access_key="ZompCakVzM55vX0Ww0lFPEjwi3QmeDKkJQ7MS6tR",
        region_name="",  # leave blank if 'LA' doesn't work
        endpoint_url="https://u5r0.la1.idrivee2-97.com",
        config=Config(signature_version="s3v4")
    )

    bucket_name = "call-recording"

    # Create local folder if it doesn't exist
    os.makedirs(download_dir, exist_ok=True)

    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        contents = response.get("Contents", [])

        downloaded = []
        for obj in contents:
            key = obj["Key"]
            if key.endswith((".mp3", ".mp4", ".ogg")):
                local_path = os.path.join(download_dir, os.path.basename(key))
                s3.download_file(bucket_name, key, local_path)
                downloaded.append(local_path)

        print(f"Downloaded {len(downloaded)} files:")
        return downloaded

    except Exception as e:
        print(f"Error downloading recordings: {e}")
        return []

if __name__ == "__main__":
    downloaded_files = download_recordings()
    if downloaded_files:
        print("Downloaded files:")
        for file in downloaded_files:
            print(f"- {file}")
    else:
        print("No files were downloaded.")