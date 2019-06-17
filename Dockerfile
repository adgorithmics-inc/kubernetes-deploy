FROM google/cloud-sdk:latest

WORKDIR /run/app

RUN apt-get update && apt-get install -y python3-pip

COPY requirements.txt ./

RUN pip3 install -r requirements.txt

COPY . .

CMD gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS; python deploy.py
