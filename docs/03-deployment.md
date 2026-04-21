# Deployment (VPS)

This guide walks through setting up a fresh VPS to run TriviaQuiz. It assumes basic command-line familiarity but no prior Docker experience.

---

## What you will end up with

| What | How you access it |
|---|---|
| TriviaQuiz app | `http://your-vps-ip:5600` (direct) or `https://yourdomain.com` (with reverse proxy) |

---

## Prerequisites

Before you start, make sure you have:

1. **A VPS** running Ubuntu 22.04 or 24.04 LTS. Any provider works (Hetzner, DigitalOcean, Linode, etc.). 1 vCPU / 1 GB RAM is the minimum; 2 vCPU / 2 GB RAM is comfortable.
2. **A domain name** with an A record pointing to your VPS's public IP. DNS changes can take up to 24 hours to propagate — create the record before you start.
3. **SSH access** to the VPS as `root` (or a user with `sudo`).
4. **This repository** either cloned from GitHub or transferred to the VPS.

---

## Step 1 — First login and system update

Connect to your VPS:

```bash
ssh root@your-vps-ip
```

Update all installed packages:

```bash
apt update && apt upgrade -y
apt install -y git curl ufw
```

---

## Step 2 — Create a non-root user (recommended)

Running everything as `root` is risky. Create a dedicated user instead:

```bash
adduser deploy
usermod -aG sudo deploy
```

Copy your SSH key so you can log in as this user (run this on your **local machine**):

```bash
ssh-copy-id deploy@your-vps-ip
```

From now on, SSH into the server as `deploy`. All remaining steps are run as `deploy`.

### Harden SSH (optional but recommended)

Once you can log in with your key, disable password authentication:

```bash
sudo nano /etc/ssh/sshd_config
```

Set:

```
PasswordAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
```

```bash
sudo systemctl restart sshd
```

> **Before doing this:** verify you can log in with your key in a second terminal. If you lock yourself out, use your VPS provider's rescue console.

---

## Step 3 — Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker deploy
```

**Log out and back in** for the group change to take effect, then verify:

```bash
docker run hello-world
```

---

## Step 4 — Configure the firewall

```bash
sudo ufw allow OpenSSH      # do this FIRST or you will lock yourself out
sudo ufw allow 80/tcp       # HTTP — needed if using a reverse proxy with TLS
sudo ufw allow 443/tcp      # HTTPS — needed if using a reverse proxy with TLS
sudo ufw enable
```

Check the status:

```bash
sudo ufw status
```

---

## Step 5 — Clone the repository

```bash
cd ~
git clone https://github.com/your-org/TriviaQuiz.git
cd TriviaQuiz
```

---

## Step 6 — Create and configure the environment file

```bash
cp docker/app.env.example .env
nano .env
```

Change the following values — **do not skip any of these**:

| Variable | What to set |
|---|---|
| `SECRET_KEY` | A long random string: `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | A strong password: `openssl rand -hex 16` |
| `MINIO_SECRET_KEY` | A strong password: `openssl rand -hex 16` |
| `POSTGRES_AUTO_CREATE` | Leave at `0` — use Alembic migrations |
| `SMTP_ENABLED` | `1` to send real emails |
| `SMTP_HOST` | Your SMTP server (e.g. `smtp.gmail.com`) |
| `SMTP_PORT` | `587` for STARTTLS, `465` for SSL |
| `SMTP_USER` | SMTP login username |
| `SMTP_PASSWORD` | SMTP login password |
| `SMTP_FROM` | Sender address (e.g. `noreply@yourdomain.com`) |
| `APP_BASE_URL` | `https://yourdomain.com` (used in email links) |

> **Never commit your production `.env` file to version control.**

---

## Step 7 — Deploy the application

```bash
docker compose -f docker/docker-compose.yml --env-file .env up -d --build
```

Watch the containers come up:

```bash
docker compose -f docker/docker-compose.yml --env-file .env ps
```

Wait until all services show `healthy` or `running`.

---

## Step 8 — Run database migrations

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head
```

You should see output ending with something like:

```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, create core tables
```

---

## Step 9 — Create the first admin user

```bash
docker compose -f docker/docker-compose.yml --env-file .env run --rm app \
  python scripts/ensure_admin.py \
  --username admin \
  --email you@yourdomain.com \
  --password "choose-a-strong-password"
```

---

## Step 10 — Verify the app is working

The app is now running on port 5600. To serve it publicly with HTTPS, configure a reverse proxy (e.g. Caddy, nginx) on the host to forward ports 80/443 to the app container on port 5600.

Check the health endpoint:

```bash
curl http://localhost:5600/health
```

Expected response: `{"status": "ok"}`

---

## Ongoing operations

### Updating the application

```bash
cd ~/TriviaQuiz
git pull
docker compose -f docker/docker-compose.yml --env-file .env build
docker compose -f docker/docker-compose.yml --env-file .env up -d
docker compose -f docker/docker-compose.yml --env-file .env run --rm app alembic upgrade head
```

The migration command is safe to run even when there are no new migrations.

### Viewing logs

```bash
# All services
docker compose -f docker/docker-compose.yml --env-file .env logs -f

# Just the app
docker compose -f docker/docker-compose.yml --env-file .env logs -f app
```

### Checking container health

```bash
docker compose -f docker/docker-compose.yml --env-file .env ps
```

All services should show `healthy` or `running`.

### Stopping and starting

```bash
# Stop (data is safe in volumes)
docker compose -f docker/docker-compose.yml --env-file .env stop

# Start again
docker compose -f docker/docker-compose.yml --env-file .env up -d
```

### Backups

See `docs/05-backups-and-restore.md` for instructions on backing up and restoring the Postgres database and MinIO media store.

---

## Port reference

| Port | Service | Accessible from |
|---|---|---|
| 22 | SSH | Internet |
| 80/443 | Reverse proxy (configured separately) | Internet |
| 5432 | Postgres | Docker internal network only |
| 9000 | MinIO API | Docker internal network only |
| 9001 | MinIO admin console | Docker internal network only |
| 5600 | Gunicorn/Flask | Docker internal network only |

Ports marked "Docker internal network only" are never exposed to the host or internet. The reverse proxy is not included in docker-compose and must be set up on the host.

---

## Automated deployment (CI/CD)

The repository includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that runs tests and deploys automatically on every push to `main`.

Required GitHub repository secrets:

| Secret | Value |
|---|---|
| `VPS_SSH_KEY` | Private SSH key for the deploy user |
| `VPS_HOST` | VPS IP address or hostname |
| `VPS_USER` | SSH username (e.g. `deploy`) |

To generate a dedicated key pair for GitHub Actions (run on your local machine):

```bash
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions_vps -N ""
ssh-copy-id -i ~/.ssh/github_actions_vps.pub deploy@your-vps-ip
```

Copy the private key content into the `VPS_SSH_KEY` secret:

```bash
cat ~/.ssh/github_actions_vps
```
