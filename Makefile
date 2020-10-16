docker-image:
	docker build -t onedrive-uploader:latest .

all: docker-image
