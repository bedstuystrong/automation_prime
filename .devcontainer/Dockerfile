# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.152.1/containers/python-3/.devcontainer/base.Dockerfile

# [Choice] Python version: 3, 3.9, 3.8, 3.7, 3.6
ARG VARIANT="3"
FROM mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT}

# [Option] Install Node.js
ARG INSTALL_NODE="true"
ARG NODE_VERSION="lts/*"
RUN if [ "${INSTALL_NODE}" = "true" ]; then su vscode -c "source /usr/local/share/nvm/nvm.sh && nvm install ${NODE_VERSION} 2>&1"; fi

# Install apt-add-repository
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y --no-install-recommends install software-properties-common

# Install gh CLI
RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-key adv --keyserver keyserver.ubuntu.com --recv-key C99B11DEB97541F0 \
    && apt-add-repository https://cli.github.com/packages \
    && apt-get update \
    && apt-get -y --no-install-recommends install gh

# Install gcloud SDK
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" \
    | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - \
    && apt-get update -y \
    && apt-get -y --no-install-recommends install google-cloud-sdk \
    && apt-get -y --only-upgrade install google-cloud-sdk-firestore-emulator google-cloud-sdk-skaffold google-cloud-sdk-app-engine-python google-cloud-sdk-spanner-emulator google-cloud-sdk-app-engine-java google-cloud-sdk google-cloud-sdk-kubectl-oidc google-cloud-sdk-anthos-auth google-cloud-sdk-cbt google-cloud-sdk-pubsub-emulator google-cloud-sdk-app-engine-grpc google-cloud-sdk-cloud-build-local google-cloud-sdk-kpt google-cloud-sdk-config-connector google-cloud-sdk-app-engine-go kubectl google-cloud-sdk-bigtable-emulator google-cloud-sdk-datastore-emulator google-cloud-sdk-kind google-cloud-sdk-minikube google-cloud-sdk-datalab google-cloud-sdk-app-engine-python-extras


COPY requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp

# [Optional] Uncomment this line to install global node packages.
# RUN su vscode -c "source /usr/local/share/nvm/nvm.sh && npm install -g <your-package-here>" 2>&1
