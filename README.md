# Christian AG Hindi Songs

Protected research database/API for building a verified Hindi Christian tune book from the AG Church songbook.

## Design

A Song is separate from its Recording candidates. A song may have several candidate tunes until manual verification. Recording credits are normalized through Artists and RecordingArtists so performers, worship groups, churches, composers and lyricists can be credited without guessing attribution.

Verification statuses: `candidate`, `likely`, `verified`, `rejected`.

Rejected recordings should normally be retained with `rejected_reason` so future research does not repeatedly rediscover a known wrong match.

## VPS install (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y python3-venv postgresql nginx
sudo -u postgres psql <<'SQL'
CREATE USER christiansongs WITH PASSWORD 'CHANGE_THIS_DATABASE_PASSWORD';
CREATE DATABASE christiansongs OWNER christiansongs;
SQL

sudo mkdir -p /opt/christian-ag-hindi-songs
sudo chown $USER:$USER /opt/christian-ag-hindi-songs
cd /opt/christian-ag-hindi-songs
git clone https://github.com/adeshsarwan/chiristian-ag-hindi-songs.git .
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Generate the API secret on the VPS (do not commit it):

```bash
openssl rand -hex 32
```

Edit `.env` and set the PostgreSQL password and generated `API_KEY`.

## systemd

Create `/etc/systemd/system/christiansongs.service`:

```ini
[Unit]
Description=Christian Songs API
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/christian-ag-hindi-songs
EnvironmentFile=/opt/christian-ag-hindi-songs/.env
ExecStart=/opt/christian-ag-hindi-songs/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8765
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo chown -R www-data:www-data /opt/christian-ag-hindi-songs
sudo systemctl daemon-reload
sudo systemctl enable --now christiansongs
curl http://127.0.0.1:8765/health
```

## Nginx

Example `/etc/nginx/sites-available/christiansongs.blazingtrail.in`:

```nginx
server {
    listen 80;
    server_name christiansongs.blazingtrail.in;

    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable it and use your normal TLS/Cloudflare setup before exposing the API publicly.

## Authentication

All `/api/*` endpoints require:

```http
Authorization: Bearer YOUR_API_KEY
```

`/health` is intentionally unauthenticated.

Example:

```bash
curl -H "Authorization: Bearer $API_KEY" https://christiansongs.blazingtrail.in/api/songs/P1
```

Do not put the API key in GitHub or client-side website JavaScript. The later MCP service should keep this credential server-side.

## Core endpoints

- `GET /api/songs`
- `GET /api/songs/{song_code}`
- `POST /api/songs`
- `PATCH /api/songs/{song_code}`
- `GET /api/songs/{song_code}/recordings`
- `POST /api/songs/{song_code}/recordings`
- `PATCH /api/recordings/{id}`
- `POST /api/songs/{song_code}/primary-recording/{id}`
- `GET /api/artists`
- `POST /api/artists`
- `POST /api/recordings/{id}/credits`
- `GET /api/songs/{song_code}/research`
- `POST /api/songs/{song_code}/research`

Interactive OpenAPI docs are available at `/docs`; because this is an administration API, consider restricting `/docs` at Nginx/Cloudflare once the MCP integration is established.

## Next phase

1. Deploy API and PostgreSQL on VPS.
2. Put it behind `https://christiansongs.blazingtrail.in`.
3. Confirm `/health` and authenticated `/api/songs` calls.
4. Build a narrow MCP layer with tools such as `get_song`, `search_songs`, `add_recording_candidate`, `add_credit`, `add_research`, `verify_recording`, and `set_primary_recording`.
5. Connect that MCP to ChatGPT using separate MCP authentication; the REST API key remains private between MCP and this API.
6. Seed P1-P10 and continue research in batches.
