# Coda [![Build Status](https://github.com/unt-libraries/coda/actions/workflow/test.yml/badge.svg?branch=master)](https://github.com/unt-libraries/coda/actions)


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

Create a `secrets.json`.
```sh
$ cp secrets.json.template secrets.json
```

Warm up the MariaDB database. This only needs to be done when the database container doesn't exist yet. This will take ~15 seconds once the image has been pulled.
```sh
$ docker-compose up -d db
```

Start the app and run the migrations.
```sh
# run the migrations
$ docker-compose run --rm manage migrate

# start the app
$ docker-compose up -d app

# Optional: add a superuser in order to log in to the admin interface
$ docker-compose run --rm manage createsuperuser
```

The app should now be viewable at the default location of localhost:8787.

The code is in a volume that is shared between your workstation and the coda container, which means any edits you make on your workstation will also be reflected in the Docker container. No need to rebuild the container to pick up changes in the code.

However, if the requirements files change, it is important that you rebuild the images for those packages to be installed. This is something that could happen when switching between feature branches, or when pulling updates from the remote.

```sh
# stop the app
$ docker-compose stop

# remove the app container
$ docker-compose rm app test manage

# rebuild the app, manage, and test containers
$ docker-compose build 

# start the app
$ docker-compose up -d app
```

#### Developing with Podman and Podman-Compose

[Install or Enable Podman](https://podman.io/getting-started/installation).

[Install Podman Compose](https://github.com/containers/podman-compose).
```sh
$ sudo dnf install podman-compose
```

Clone the repository.
```sh
$ git clone https://github.com/unt-libraries/coda.git
$ cd coda
```

Warm up the database. 
```sh
$ sudo podman-compose up -d db
```

Start the app and run the migrations.
```sh
$ sudo podman-compose up -d

$ sudo podman-compose run --rm web ./manage.py migrate

$ sudo podman-compose run --rm web ./manage.py createsuperuser
```

To check the app after you have completed the migrations.
```sh
$ sudo podman-compose up -d app
```

## Running the tests

The db container must already be running, or the tests will probably
fail on the first run since the database needs time to warm up.

```sh
# On the initial run or if the schema changes
$ docker-compose run --rm test --create-db

# Subsequent runs
$ docker-compose run --rm test 
```

For podman
```sh
$ sudo podman-compose run --rm test
```
