# A lancer depuis la racine de ce dépôt :
#   docker build -f deploy/docker/Dockerfile -t ragifix-mcp .
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system ragifix-mcp && useradd --system --gid ragifix-mcp --create-home --home-dir /home/ragifix-mcp ragifix-mcp

WORKDIR /opt/ragifix-mcp

COPY . .

RUN pip install --no-cache-dir .

USER ragifix-mcp

EXPOSE 8422

# Par défaut (server.host=127.0.0.1 dans config.yaml), le serveur n'écoute
# que sur la boucle locale DU CONTAINER. Pour le rendre joignable depuis
# l'hôte ou un autre container, utiliser network_mode: host (voir
# deploy/docker/docker-compose.yml) plutôt qu'un mapping de port classique
# qui obligerait à passer host=0.0.0.0 — voir le README, section
# "Accès distant".
ENTRYPOINT ["ragifix-mcp"]
CMD ["--config", "/etc/ragifix/config.yaml"]
