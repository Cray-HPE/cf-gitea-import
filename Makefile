NAME ?= cf-gitea-import
VERSION ?= $(shell cat .version)-local

all : image

image:
		docker build --pull ${DOCKER_ARGS} --tag '${NAME}:${VERSION}' .
