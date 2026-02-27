FROM continuumio/miniconda3

LABEL MAINTAINER="Nate Matteson <natem@scripps.edu>"

RUN git clone https://github.com/watronfire/lone_pine.git /app

WORKDIR "/app"

RUN conda install -c bioconda --file requirements.txt

CMD [ "gunicorn", "--workers=5", "--threads=1", "-b 0.0.0.0:8000", "app:server"]