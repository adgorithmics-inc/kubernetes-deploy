FROM python:3.6-stretch

WORKDIR /run/app

RUN apt-get update && apt-get install -y \
    apt-transport-https \
    curl

RUN curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -; \
    echo "deb https://apt.kubernetes.io/ kubernetes-xenial main" | tee -a /etc/apt/sources.list.d/kubernetes.list

RUN apt-get update && apt-get install -y \
    kubectl

COPY requirements.txt ./

RUN pip3 install -r requirements.txt

COPY . .
