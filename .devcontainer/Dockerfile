FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    openjdk-17-jdk-headless python3 python3-venv git curl ca-certificates jq make shellcheck \
    rsync unzip zip openssl && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
