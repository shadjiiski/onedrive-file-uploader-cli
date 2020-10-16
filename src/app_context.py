import os
import json

APP_PROPERTIES_FILE = "app-properties.json"
AUTHORITY_FORMAT = "https://login.microsoftonline.com/{}"
DEFAULT_TENANT = "common"

class AppContext:

    def __init__(self):
        self.scope = ["Files.ReadWrite"] # Files.ReadWrite.AppFolder not supported on One Drive Bussiness...
        self.endpoint = "https://graph.microsoft.com/v1.0/me"
        self.set_tenant(DEFAULT_TENANT)
        self.blocks = 1
        self.access_token = None

        script_dir = os.path.dirname(os.path.realpath(__file__))
        props_abs_file = os.path.join(script_dir, APP_PROPERTIES_FILE)
        if os.path.isfile(props_abs_file):
            with open(props_abs_file) as f:
                props = json.loads(f.read())
                # https://docs.microsoft.com/en-us/onedrive/developer/rest-api/getting-started/app-registration?view=odsp-graph-online
                if "client_id" in props:
                    self.client_id = props["client_id"]

                if "tenant_id" in props:
                    self.authority = AUTHORITY_FORMAT.format(props["tenant_id"])

    def set_tenant(self, tenant):
        self.authority = AUTHORITY_FORMAT.format(tenant)
