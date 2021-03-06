Containerized OneDrive uploader
===

This is a simple python script with no UI that can upload small and large files to OneDrive (Bussiness supported). It is designed to use a public client so it stores no client secret/certificate. It uses the device flow authentication method - you open a link in any browser on any device and input a code generated by the script.

The application will upload a specified file in its App directory in your OneDrive. It requires `Files.ReadWrite` privillege only because `Files.ReadWrite.AppFolder` is not yet supported on OneDrive Bussines.



Usage
---
You may need to install the dependencies first:
```
pip install -r src/requirements.txt
```

The the uploader can be used directly
```
python src/onedrive_uploader.py --help
python src/onedrive_uploader.py /path/to/my-file
```

Alternatively, it can be run from a container
```
make all
docker run -it --rm onedrive-uploader --help
docker run -it --rm -v /path/to/my-file:/data/my-file:ro onedrive-uploader /data/my-file
```

In both cases, check the help message for all available options. Also, this was developed over night, so check the sources if anything unclear :)
