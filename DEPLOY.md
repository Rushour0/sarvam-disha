# Deploying Disha on Coolify

The box already runs Coolify 4.1.2 with a Traefik proxy and a Cloudflare tunnel
in front of it, so Disha is added as one more resource rather than as a new
stack. Amazon Linux 2023, 2 vCPU, 7.6 GiB RAM, ~8 GiB disk free.

## What gets deployed

`docker-compose.yml` declares four services built from one image:

| service | role | ingress |
| --- | --- | --- |
| `qdrant` | vector store for the KB and per-case memory | none |
| `indexer` | one-shot; embeds the KB then exits | none |
| `agent` | LiveKit worker, dials out to LiveKit Cloud | none |
| `api` | case API and the tree/scholarship endpoints | none |
| `web` | Next.js app; proxies the API at /api/disha | cloudflared |

Only the web app is reachable from outside. The API has no domain on purpose:
`/cases` returns every student's phone number and the verbatim quotes that
triggered a wellbeing flag, so it is reached only through the web container on
the internal network. `/counsellor` and `/api/disha/cases` sit behind basic
auth that returns 503 when `DISHA_COUNSELLOR_PASSWORD` is unset — a missing
secret fails closed rather than serving that data.

The agent holds an outbound connection to LiveKit Cloud and never accepts
inbound traffic, so it gets no route and no exposed port.

## Two things that will waste an afternoon

**The box is Graviton (aarch64).** Images built on standard amd64 runners fail
every pull with `no matching manifest for linux/arm64/v8`. The build job runs
on `ubuntu-24.04-arm` with `platforms: linux/arm64` for that reason.

**cloudflared must be attached to this stack's network.** It routes by Docker
service name, and Coolify gives each resource its own network, so a hostname
pointing at `http://sarvam-web:3000` fails with `no such host` until:

    docker network connect <resource-uuid-network> cloudflared

The symptom looks like an application crash, not a DNS problem.

## Its own Qdrant, deliberately

The box already runs a Qdrant — but it belongs to the **ludexel** Coolify
project (`qdrant-l13czjln5erto7eg94e4dcti`). During development Disha indexed
into it, which means student conversation memory currently sits inside an
unrelated product's volume, under that project's backup and retention policy,
and would be deleted by anyone redeploying ludexel.

The compose file declares a separate `qdrant` service with its own named
volume. After the first deploy, drop the stray collections from the ludexel
instance:

    for c in disha_handbook disha_careers disha_scholarships; do
      curl -s -X DELETE localhost:6333/collections/$c
    done
    # plus any disha_conversation_* / disha_person_* from test calls
    curl -s localhost:6333/collections | grep -o 'disha_[a-z_0-9]*'

## Steps

1. **Push the repo** somewhere Coolify can reach (GitHub app or deploy key).
   Coolify builds from git; it does not build from a local directory.

2. **New resource → Docker Compose**, point it at this repo and
   `docker-compose.yml`. Pick the same server the other stacks run on.

3. **Set the environment variables** in the Coolify UI. None of these are in the
   repo and none should be:

   ```
   LIVEKIT_URL          wss://<your-project>.livekit.cloud
   LIVEKIT_API_KEY
   LIVEKIT_API_SECRET
   SARVAM_API_KEY
   OPENAI_API_KEY
   DISHA_LLM            optional, default openai/gpt-4.1-mini
   ```

   Coolify generates `SERVICE_FQDN_API_8090` itself — leave it alone.

4. **Deploy.** First build takes a few minutes: it installs the LiveKit plugins
   and prefetches the Silero VAD weights so the first call does not pay for the
   download as dead air.

5. **Verify** before pointing the web app at it:

   ```
   curl -fsS https://<api-domain>/health
   curl -fsS https://<api-domain>/tree | head -c 200
   docker logs -f $(docker ps --filter name=agent --format '{{.Names}}' | head -1)
   ```

   The agent log should end with a registered-worker line. The indexer container
   should have exited 0 — check it with `docker ps -a`.

6. **Point the web app at the API.** The front end is on Vercel; set its API
   base URL to the Coolify domain and redeploy.

## Re-indexing after a KB change

The indexer runs on every deploy, and `scripts/index_kb.py` drops and rebuilds
the static collections, so a redeploy is the re-index. To do it without a
deploy:

    docker compose run --rm indexer

## Resource notes

- The image is one build shared by three services; Coolify builds it once.
- Disk is the tight constraint at ~8 GiB free. The image is roughly 1.5 GiB
  because of torch inside the Silero plugin. Prune old images after a few
  deploys: `docker image prune -a --filter "until=168h"`.
- 2 vCPU is enough for a demo but is shared with the ludexel stack and Coolify
  itself. One concurrent call is comfortable; several are not tested.

## Not covered here

- The `scripts/deploy-ec2.sh` rsync path still exists and deploys the same code
  bare-metal to `~/disha`. Once Coolify is live, retire it rather than leaving
  two deployment routes that can disagree about which code is running.
- No backup is configured for either named volume. `disha-cases` holds the only
  copy of every student's saved constraints and notes.
