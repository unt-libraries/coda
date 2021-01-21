#!/bin/bash
while ! nc -z db 3306; do echo "waiting for mariadb..."; sleep 3; done
