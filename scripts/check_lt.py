import libtorrent as lt
import os
import sys

print(f"Libtorrent version: {lt.version}")

# Create a dummy resume data to test serialization
params = lt.add_torrent_params()
params.save_path = "."
# In 2.0+, we can't easily create a populated add_torrent_params without a torrent
# But we can check if write_resume_data exists
if hasattr(lt, 'write_resume_data'):
    print("Has lt.write_resume_data")
    try:
        data = lt.write_resume_data(params)
        print(f"write_resume_data type: {type(data)}")
        encoded = lt.bencode(data)
        print(f"Bencoded length: {len(encoded)}")
    except Exception as e:
        print(f"Error in write_resume_data: {e}")

# Check save_resume_data_alert
print(f"Has save_resume_data_alert: {hasattr(lt, 'save_resume_data_alert')}")
