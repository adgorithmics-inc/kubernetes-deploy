FROM python:3.7-stretch

WORKDIR /run/app

RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add - && apt-get update -y && apt-get install google-cloud-sdk -y

COPY requirements.txt ./

RUN pip install -r requirements.txt

COPY . .
COPY ./run.sh /usr/local/bin

ENTRYPOINT ["run.sh"]
