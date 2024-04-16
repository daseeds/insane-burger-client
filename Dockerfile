FROM python:3.12

COPY requirements.txt .

COPY files/etc/apt/ /etc/apt/

# install base system
RUN apt-key add /etc/apt/keys/raspi.key && \
  apt-get update && \
  pip3 install rpi-gpio && \
  pip3 install requests

RUN pip install -r requirements.txt

COPY . .

# runtime setup
ARG VERSION
ENV DOCKER_RPI_GPIO_VERSION ${VERSION}

ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /usr/lib/python3/dist-packages

CMD ["python", "./src/app.py"]
