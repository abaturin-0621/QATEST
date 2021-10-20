FROM ubuntu:20.04 AS builder

RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y unzip \
    curl && \
    mkdir /opt/oracle && \
    cd /opt/oracle && \
    curl -O https://rpm.colvir.ru/distro/instantclient-basic-linux.x64-19.8.0.0.0dbru.zip && \
    curl -O https://rpm.colvir.ru/distro/instantclient-sqlplus-linux.x64-19.8.0.0.0dbru.zip && \
    unzip instantclient-basic-linux.x64-19.8.0.0.0dbru.zip && \
    unzip instantclient-sqlplus-linux.x64-19.8.0.0.0dbru.zip && \
    rm instantclient-basic-linux.x64-19.8.0.0.0dbru.zip && \
    rm instantclient-sqlplus-linux.x64-19.8.0.0.0dbru.zip && \
    rm -rf /var/lib/apt/lists/*

# # # # # # # # DF: 2-nd stage

FROM apache/airflow:2.1.0
USER root

# Install dependenses
RUN apt-get update && apt-get install -y nano libaio1 openjdk-11-jdk ant && \
    rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME
ENV JAVA_HOME /usr/lib/jvm/java-11-openjdk-amd64/
RUN export JAVA_HOME

# Install Oracle client
COPY --from=builder /opt/oracle/ /opt/oracle
RUN echo 'export PATH="$PATH:/opt/oracle/instantclient_19_8"' >> ~/.bashrc && \
    echo 'export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/opt/oracle/instantclient_19_8"' >> ~/.bashrc && \
    echo /opt/oracle/instantclient_19_8 > /etc/ld.so.conf.d/oracle-instantclient.conf && \
    ldconfig

# Install 
COPY dags/ /opt/airflow/dags/
COPY libs/ /opt/airflow/libs/
COPY requirements.txt /opt/airflow/requirements.txt
# RUN cd libs && python setup.py sdist && cd ..

# Airflow stuff
USER airflow
WORKDIR /opt/airflow

# Pip installs (remake with requirements.txt when it`s ready)
RUN pip install -r requirements.txt
# RUN pip install /opt/airflow/libs/dist/sdh-0.0.0.tar.gz

# Error with updated pip: https://github.com/pypa/pip/issues/10151 (disable for now)
# pip install --upgrade pip