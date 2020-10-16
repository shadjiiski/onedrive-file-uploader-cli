import argparse
import os
import sys
import json
import requests
import msal

from onedrive_uploaders import OneDriveUploader
from app_context import AppContext

DEFAULT_BLOCKS = 100

class ApplicationEntrypoint:
    
    def user_input(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-t", "--tenant",
                help="MS Graph tenant")
        parser.add_argument("-e", "--endpoint",
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
        if args.endpoint:
            ctx.endpoint = args.endpoint
        if args.tenant:
            ctx.set_tenant(args.tenant)

        ctx.blocks = args.file_blocks
        local_file = args.local_file

        if args.access_token:
            ctx.access_token = args.access_token
        else:
            ctx.access_token = self.get_msgraph_access_token(ctx)
            if args.print_tokens:
                print(f"access token: {ctx.access_token}")

        uploader = OneDriveUploader.get_instance(local_file)
        uploader.upload(local_file, ctx)

if __name__ == "__main__":
    ApplicationEntrypoint().run()
