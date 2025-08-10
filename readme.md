This repository contains LiveKit integration to record calls using LiveKit Egress, with scripts to create storage buckets, store recordings, list them, and download them.
Currently supports MinIO for storage, with utility files for managing and retrieving recordings.

**Files**
- create_bucket_and_store_minio.py: create bucket using room name if it's not available already, then store recording.
- agent_call_recording.py.bak: backup file; it doesn't contain any unique feature right now.
- agent_initial.py: record call and store it in bucket
- create_bucket_and_store(IDrive).py: Doesn't work as Idrive doesn't provide access to create bucket from this file
- download_recording.py: This file contain a get function to download all the recordings from bucket and store them in a /recording folder.
- get_recording.py: only return all the recordings name stored in bucket.
