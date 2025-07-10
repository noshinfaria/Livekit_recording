import boto3
from botocore.client import Config

def get_recordings():
    s3 = boto3.client(
        "s3",
        aws_access_key_id="LTaGZLxaCHuvzwwwQDTR",
        aws_secret_access_key="ZompCakVzM55vX0Ww0lFPEjwi3QmeDKkJQ7MS6tR",
        region_name="",  # use "" if 'LA' doesn't work
        endpoint_url="https://u5r0.la1.idrivee2-97.com",
        config=Config(signature_version="s3v4")
    )

    bucket_name = "call-recording"

    try:
        response = s3.list_objects_v2(Bucket=bucket_name)

        recordings = []
        for obj in response.get("Contents", []):
            key = obj["Key"]
            if key.endswith((".mp3", ".mp4", ".ogg")):
                recordings.append(key)

        return recordings

    except Exception as e:
        print(f"Error retrieving recordings: {e}")
        return []


if __name__ == "__main__":
    recordings = get_recordings()
    print("Recordings found:")
    for file in recordings:
        print(f"- {file}")
