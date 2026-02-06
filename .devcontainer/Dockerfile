FROM mcr.microsoft.com/devcontainers/python:3.12

# Install system dependencies for Playwright if needed (browsers are installed via postCreateCommand)
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive 
    && apt-get -y install --no-install-recommends 
    git 
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*
