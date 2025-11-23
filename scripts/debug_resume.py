import libtorrent as lt
import os

print(f"Libtorrent version: {lt.version}")

params = lt.add_torrent_params()
params.save_path = "."

# Create dummy resume data
resume_dict = {"file-format": "libtorrent resume file", "file-version": 1, "info-hash": "1234"*10}
bencoded_data = lt.bencode(resume_dict)

print(f"Bencoded data type: {type(bencoded_data)}")

try:
    print("Attempting to set params.resume_data = bencoded_data")
    params.resume_data = bencoded_data
    print("Success!")
except Exception as e:
    print(f"Failed to set params.resume_data: {e}")

try:
    print("Attempting to use lt.read_resume_data")
    p2 = lt.read_resume_data(bencoded_data)
    print(f"Success! p2 type: {type(p2)}")
except Exception as e:
    print(f"Failed to use lt.read_resume_data: {e}")
