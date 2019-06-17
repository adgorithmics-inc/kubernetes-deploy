FROM google/cloud-sdk:latest

WORKDIR /run/app

RUN apt-get update && apt-get install -y python3-pip

COPY requirements.txt ./

RUN pip3 install -r requirements.txt

COPY . .
COPY ./run.sh /usr/local/bin
ENTRYPOINT ["run.sh"]
