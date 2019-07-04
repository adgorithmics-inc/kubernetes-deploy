FROM google/cloud-sdk:latest

WORKDIR /run/app

RUN printf "deb http://archive.debian.org/debian/ jessie main\ndeb-src http://archive.debian.org/debian/ jessie main\ndeb http://security.debian.org jessie/updates main\ndeb-src http://security.debian.org jessie/updates main" > /etc/apt/sources.list

RUN apt-get update && apt-get install -y python3-pip python3-dev \
    build-essential libssl-dev libffi-dev
    
COPY requirements.txt ./

RUN pip3 install -U setuptools --upgrade
RUN pip3 install -r requirements.txt

COPY . .
COPY ./run.sh /usr/local/bin

ENTRYPOINT ["run.sh"]
