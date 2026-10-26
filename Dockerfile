FROM debian:trixie-slim

# create non-root user
RUN useradd -m -s /bin/bash app

# install system dependencies
RUN apt-get update && apt-get install -y \
    bash \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# install supercronic (container-native cron)
# latest releases available at https://github.com/aptible/supercronic/releases

ENV SUPERCRONIC_URL=https://github.com/aptible/supercronic/releases/download/v0.2.42/supercronic-linux-amd64 \
    SUPERCRONIC_SHA1SUM=b444932b81583b7860849f59fdb921217572ece2 \
    SUPERCRONIC=supercronic-linux-amd64

RUN curl -fsSLO "$SUPERCRONIC_URL" \
    && echo "${SUPERCRONIC_SHA1SUM}  ${SUPERCRONIC}" | sha1sum -c - \
    && chmod +x "$SUPERCRONIC" \
    && mv "$SUPERCRONIC" "/usr/local/bin/${SUPERCRONIC}" \
    && ln -s "/usr/local/bin/${SUPERCRONIC}" /usr/local/bin/supercronic

# switch to app user
USER app
WORKDIR /home/app

# setup ~/.local/bin
RUN mkdir -p /home/app/.local/bin
ENV PATH="/home/app/.local/bin:$PATH"

# install uv for python script execution (as app user)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# install lifx CLI from this repo
COPY --chown=app:app lifx.py /home/app/.local/bin/lifx.py
RUN chmod +x /home/app/.local/bin/lifx.py

# pre-install lifx dependencies by running help
RUN lifx.py --help

# run supercronic as the main process
# -inotify reloads the schedule automatically when the crontab file changes
CMD ["supercronic", "-inotify", "/lifx/crontab"]
