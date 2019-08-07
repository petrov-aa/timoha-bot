FROM python:3.6-alpine

COPY ./src /app
WORKDIR /app
RUN pip install -r requirements.txt
EXPOSE 443

COPY ./entrypoint.sh /run.sh
RUN chmod u+x /run.sh

CMD ["/run.sh"]
