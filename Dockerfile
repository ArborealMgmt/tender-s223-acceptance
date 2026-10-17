FROM docker:dind@sha256:56e360024d7d35dac801b8fc87f869ccf5c89b88399dd266f7cfc1169690a86b
RUN apk add --no-cache python3
RUN mkdir -p /srv/s223 && printf 's223-private-service\n' > /srv/s223/fixture.txt
ENTRYPOINT []
EXPOSE 8080
CMD ["python3", "-m", "http.server", "8080", "--directory", "/srv/s223"]
