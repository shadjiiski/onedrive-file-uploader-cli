import argparse
import os
import time

import sys
import json

import requests
import msal

from abc import ABC, abstractmethod

AUTHORITY_FORMAT = "https://login.microsoftonline.com/{}"

DEFAULT_TENANT = "common"
DEFAULT_ENDPOINT = "https://graph.microsoft.com/v1.0/me"
DEFAULT_LOCATION = "/test-uploader-app"
DEFAULT_BLOCKS = 1

class AppContext:
    # https://docs.microsoft.com/en-us/onedrive/developer/rest-api/getting-started/app-registration?view=odsp-graph-online
    client_id = "enter-client-id-here"
    scope = ["Files.ReadWrite"] # Files.ReadWrite.AppFolder not supported on One Drive Bussiness...
    endpoint = "https://graph.microsoft.com/v1.0/me"
    authority = AUTHORITY_FORMAT.format(DEFAULT_TENANT)
    blocks = DEFAULT_BLOCKS
    access_token = None

class OneDriverUploader(ABC):

    @abstractmethod
    def upload(self, local_file, ctx: AppContext, remote_location=DEFAULT_LOCATION):
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
            return SimpleOneDriverUploader()
        else:
            return LargeFileOneDriverUploader()

class SimpleOneDriverUploader(OneDriverUploader):

    def test(self, local_file, ctx: AppContext, remote_location=DEFAULT_LOCATION):
        url = f"{ctx.endpoint}/drive/special/approot"
        headers = {"Authorization": f"Bearer {ctx.access_token}"}
        r = requests.get(url, headers=headers)
        self.dump_request_result(r)

    def upload(self, local_file, ctx: AppContext, remote_location=DEFAULT_LOCATION):
        headers = {"Authorization": f"Bearer {ctx.access_token}"}
        with open(local_file, mode='rb') as f:
            print(f"Starting upload for {f.name}...")
            sys.stdout.flush()
            url = f"{ctx.endpoint}/drive/special/approot:/{f.name}:/content"
            try:
                start_time = time.time()
                r = requests.put(url, data=f, headers=headers)
                self.dump_request_result(r)
                print(f"{f.name} was uploaded successfully in {time.time() - start_time} seconds!")
            except:
                print("Upload failed")
                raise

class LargeFileOneDriverUploader(OneDriverUploader):

    BLOCK_SIZE = 327680

    def upload(self, local_file, ctx: AppContext, remote_location=DEFAULT_LOCATION):
        chunk_size = self.BLOCK_SIZE * ctx.blocks
        total_size = os.path.getsize(local_file)
        total_chunks = total_size // chunk_size
        last_byte = total_size - 1

        headers = {"Authorization": f"Bearer {ctx.access_token}"}
        with open(local_file, mode='rb') as f:
            start_time = time.time()
            print(f"Creating upload session for {f.name}...")
            url = f"{ctx.endpoint}/drive/special/approot:/{f.name}:/createUploadSession"
            r = requests.post(url, headers=headers)
            self.dump_request_result(r)
            upload_url = r.json()["uploadUrl"]

            chunk_start = 0
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
                print(f"Sending {send_bytes} bytes: {send_range}")
                sys.stdout.flush()
                r = requests.put(upload_url, data=data, headers=headers)

                if r.status_code in [200, 201]:
                    print(f"{f.name} was uploaded successfully in {time.time() - start_time} seconds!")
                    break
                elif r.status_code != 202:
                    print("Unexpected response code...")
                    self.dump_request_result(r)

                    print("Terminating upload session")
                    r = requests.delete(upload_url)
                    self.dump_request_result(r)
                    raise ValueError("Upload failed")

                chunk_start = chunk_end + 1
        pass

class ApplicationEntrypoint:
    
    def user_input(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--tenant",
                default=DEFAULT_TENANT,
                help="MS Graph tenant")
        parser.add_argument("-e", "--endpoint",
                default=DEFAULT_ENDPOINT,
                help="Endpoint base URI for sending API requests")
        parser.add_argument("--file-blocks",
                type=int,
                default=DEFAULT_BLOCKS,
                help="Number of 320 KiB blocks to send per request for large file uploads")
        parser.add_argument("--access-token",
                help="Access token to use for the upload (may be skipped)")
        parser.add_argument("--print-tokens",
                action="store_true",
                help="Debug only: prints the obtained tokens")
        parser.add_argument("local_file",
                help="file to upload")
    
        args = parser.parse_args()

        if not os.path.isfile(args.local_file):
            raise ValueError(f"{args.local_file} is not an existing file")
        if args.file_blocks > 192 or args.file_blocks < 1:
            raise ValueError(f"Invalid value for --file-blocks: {args.file_blocks}. Must be between 1 and 192.")
        return args
    
    def get_msgraph_access_token(self, ctx: AppContext):
        app = msal.PublicClientApplication(ctx.client_id, authority=ctx.authority)
        print("Getting access token from AAD.")
        flow = app.initiate_device_flow(scopes=ctx.scope)
        if "user_code" not in flow:
            raise ValueError(f"Fail to create device flow. Err: {json.dumps(flow, indent=4)}")
        print(flow["message"])
        print("Press Enter after signing in from another device to proceed, CTRL+C to abort.")
        sys.stdout.flush()  # Some terminal needs this to ensure the message is shown
        input()
        result = app.acquire_token_by_device_flow(flow)
        # print(json.dumps(result))
        # TODO also handle refresh_token and maybe id_token? See above output for more details
        if not "access_token" in result:
            raise ValueError(f"Failed to obtain access_token, result is {json.dumps(result, indent=4)}")
        return result["access_token"]

    def run(self):
        ctx = AppContext()

        args = self.user_input()
        ctx.endpoint = args.endpoint
        ctx.authority = AUTHORITY_FORMAT.format(args.tenant)
        ctx.blocks = args.file_blocks
        local_file = args.local_file

        if args.access_token:
            ctx.access_token = args.access_token
        else:
            ctx.access_token = self.get_msgraph_access_token(ctx)
            if args.print_tokens:
                print(f"access token: {ctx.access_token}")

        uploader = OneDriverUploader.get_instance(local_file)
        uploader.upload(local_file, ctx)

if __name__ == "__main__":
    ApplicationEntrypoint().run()
