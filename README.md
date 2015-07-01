# Coda [![Build Status](https://travis-ci.org/unt-libraries/coda.svg?branch=master)](https://travis-ci.org/unt-libraries/coda)


## Developing
To take advantage of the dev environment that is already configured, you need to have Docker(>= 1.3) and Docker Compose installed.

Install [Docker](https://docs.docker.com/installation/)

Install Docker Compose
```sh
$ pip install docker-compose
```

Clone the repository.
```sh
$ git clone https://github.com/unt-libraries/coda.git
$ cd coda
```

Start the app and run the migrations.
```sh
# start the app
$ docker-compose up -d
```

The code is in a volume that is shared between your workstation and the coda container, which means any edits you make on your workstation will also be reflected in the Docker container. No need to rebuild the container to pick up changes in the code.

However, if the requirements files change, it is important that you rebuild the coda image for those packages to be installed. This is something that could happen when switching between feature branches, or when pulling updates from the remote.

```sh
# stop the app
$ docker-compose stop

# remove the coda container
$ docker-compose rm coda

# rebuild the coda container
$ docker-compose build coda

# start the app
$ docker-compose up -d
```
