import os
import time
import sys
import requests
from abc import ABC, abstractmethod
from app_context import AppContext

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

class OneDriveUploader(ABC):

    def __init__(self):
        retry_strategy = Retry(
            total=5,
            backoff_factor=2.0,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = TimeoutHTTPAdapter(max_retries=retry_strategy)
        self.http = requests.Session()
        self.http.mount("https://", adapter)
        self.http.mount("http://", adapter)


    @abstractmethod
    def upload(self, local_file, ctx: AppContext):
        pass

    def dump_request_result(self, r):
        print("---------- Response -------------")
        if r.status_code:
            print(f"Status code: {r.status_code}")
        if r.headers:
            print("Response headers:")
            for k,v in r.headers.items():
                print(f"{k}: {v}")
        if r.json():
            print(f"Response body: {r.json()}")
        print("---------------------------------")

    @classmethod
    def get_instance(cls, local_file):
        if os.path.getsize(local_file) < 4100000:
            return SimpleOneDriveUploader()
        else:
            return LargeFileOneDriveUploader()

class SimpleOneDriveUploader(OneDriveUploader):

    def upload(self, local_file, ctx: AppContext):
        headers = {"Authorization": f"Bearer {ctx.access_token}"}
        with open(local_file, mode='rb') as f:
            print(f"Starting upload for {f.name}...")
            sys.stdout.flush()
            url = f"{ctx.endpoint}/drive/special/approot:/{os.path.basename(f.name)}:/content"
            try:
                start_time = time.time()
                r = self.http.put(url, data=f, headers=headers)
                self.dump_request_result(r)
                print(f"{f.name} was uploaded successfully in {time.time() - start_time} seconds!")
            except:
                print("Upload failed")
                raise

class LargeFileOneDriveUploader(OneDriveUploader):

    BLOCK_SIZE = 327680

    def upload(self, local_file, ctx: AppContext):
        chunk_size = self.BLOCK_SIZE * ctx.blocks
        total_size = os.path.getsize(local_file)
        total_chunks = total_size // chunk_size
        last_byte = total_size - 1

        headers = {"Authorization": f"Bearer {ctx.access_token}"}
        with open(local_file, mode='rb') as f:
            start_time = time.time()
            print(f"Creating upload session for {f.name}...")
            url = f"{ctx.endpoint}/drive/special/approot:/{os.path.basename(f.name)}:/createUploadSession"
            r = self.http.post(url, headers=headers)
            self.dump_request_result(r)
            upload_url = r.json()["uploadUrl"]

            chunk_start = 0
            try:
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        print("no more data to read, breaking. Shouldn't get here...")
                        break
                    chunk_end = chunk_start + chunk_size - 1
                    if chunk_end > last_byte:
                        chunk_end = last_byte

                    send_range = f"bytes {chunk_start}-{chunk_end}/{total_size}"
                    send_bytes = chunk_end - chunk_start + 1
                    headers = {
                        "Content-Length":f"{send_bytes}",
                        "Content-Range": send_range
                    }
                    done_percentage = round(100 * chunk_start / total_size, 2)
                    print(f"{done_percentage}% done. Sending {send_bytes} bytes: {send_range}")
                    sys.stdout.flush()
                    r = self.http.put(upload_url, data=data, headers=headers)

                    if r.status_code in [200, 201]:
                        print(f"{f.name} was uploaded successfully in {time.time() - start_time} seconds!")
                        break
                    elif r.status_code != 202:
                        print("Unexpected response code...")
                        self.dump_request_result(r)
                        raise ValueError("Upload failed: unexpected status code")

                    chunk_start = chunk_end + 1
            except:
                print("An error occurred, terminating upload session")
                r = http.delete(upload_url)
                self.dump_request_result(r)
                raise

class TimeoutHTTPAdapter(HTTPAdapter):

    DEFAULT_TIMEOUT = 60

    def __init__(self, *args, **kwargs):
        self.timeout = self.DEFAULT_TIMEOUT
        if "timeout" in kwargs:
            self.timeout = kwargs["timeout"]
            del kwargs["timeout"]
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout
        return super().send(request, **kwargs)
