# Dockerfile and support scripts for Daily Storage Reports Readme


## Installation Steps

### 1. Install Docker
See:
*   Linux: http://docs.docker.com/linux/started/
*   Mac: http://docs.docker.com/mac/started/
### 2. Create config.json
```shell
cp ../config.json ./config.json
```
After copying the config.json template to the same directory as the Dockerfile, edit the config file with the setting for your environment

### 3. Run Docker Build

```shell
cd <dir with docker file>
docker build -t daily_storage_reports .
```

### 4. Run the container

Just run

```shell
docker run -d -p 8080:8080 daily_storage_reports
```

### 5. Connect to WebUI

Your docker host will now be listening on port 8080.

http://[docker_host]:8080

