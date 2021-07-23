FROM python:3

RUN mkdir /opt/rsspy
WORKDIR /opt/rsspy

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

#COPY . .

ENTRYPOINT [ "python" ]