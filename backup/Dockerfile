FROM alpine:latest

RUN apk add --no-cache postgresql-client bash curl gettext

COPY backup.sh /backup.sh
COPY entrypoint.sh /entrypoint.sh
COPY crontab.txt /crontab.txt

RUN chmod +x /backup.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
