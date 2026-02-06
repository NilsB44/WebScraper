FROM mcr.microsoft.com/devcontainers/python:3.12

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get -y install --no-install-recommends \
    git \
    curl \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*
