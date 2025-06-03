FROM cr.weaviate.io/semitechnologies/weaviate:1.30.6
RUN apt update && apt install -y curl 
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 8080
EXPOSE 50051
ENTRYPOINT ["/entrypoint.sh"]
