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

Similar to docker and docker-compose, you will need to install, clone the repository and create a `secrets.json`.

[Install or Enable Podman](https://podman.io/getting-started/installation).

[Install Podman Compose](https://github.com/containers/podman-compose).

If you have SELinux, you may need to temporarily add `:Z` to the base volumes in the docker-compose.yml. It will look like `.:/app/:Z`. You may also need to use `sudo` for your podman-compose commands.

The rest of the steps are also similar. You will want to replace the word `docker` with `podman`. You will need to add one step before migrating:
```sh
$ podman-compose up -d
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
$ podman-compose run --rm test
```
