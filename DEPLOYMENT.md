# Falsifi Deployment Information

## Current Deployment (Temporary Tunnel)

**Public URL:** https://7b902068e1defe3d-170-64-152-220.serveousercontent.com

**Status:** ✅ LIVE and WORKING

### Verified Working Features:
- ✅ Home page with featured bounties
- ✅ Bounties listing page
- ✅ Leaderboard
- ✅ API endpoints (/api/bounties)
- ✅ User authentication (login/logout)
- ✅ All sample data loaded (4 bounties, 2 refutations)

### Demo Accounts Available:
- Username: `alice` (5000 points)
- Username: `bob` (3000 points)
- Username: `charlie` (2000 points)
- Username: `demo_user` (1000 points)

**Note:** To log in, just enter any of these usernames (no password required in MVP).

---

## Setup Notes

### Local Development:
```bash
cd /home/vec/clawd/projects/falsifi
pip install -r requirements.txt
python app.py
# Visit http://localhost:5000
```

### Environment Variables:
- `SECRET_KEY` - Flask session secret (auto-generated in deployment)
- `OPENAI_API_KEY` - Optional, for AI adjudication features
- `DATABASE_URL` - Defaults to SQLite
- `PORT` - Server port (default: 5000)

### Files Created for Deployment:
- `Procfile` - For Heroku/Railway
- `runtime.txt` - Python version specification
- `Dockerfile` - Container deployment
- `render.yaml` - Render.com blueprint
- `templates/` - All HTML templates (created)
- `static/css/style.css` - Complete styling

---

## Permanent Deployment Options

### Option 1: Railway.app (Recommended)
1. Visit https://railway.app
2. Sign up with GitHub
3. Create new project → Deploy from GitHub repo
4. Push this code to a GitHub repository first:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/falsifi.git
   git push -u origin master
   ```
5. Set environment variables in Railway dashboard:
   - `SECRET_KEY` (generate random string)
   - `OPENAI_API_KEY` (optional)

### Option 2: Render.com
1. Push code to GitHub
2. Visit https://render.com
3. Click "New Web Service"
4. Connect GitHub repo
5. Blueprint is already configured in `render.yaml`

### Option 3: Fly.io
1. Install flyctl: `curl -L https://fly.io/install.sh | sh`
2. `flyctl auth login`
3. `flyctl launch` (in project directory)
4. `flyctl deploy`

---

## Important Notes

### Current Tunnel Limitations:
- The current serveo.net tunnel is temporary
- URL will change if the SSH tunnel disconnects
- For a permanent URL, use one of the deployment options above

### Database Persistence:
- Currently using SQLite
- Database file: `falsifi.db`
- Sample data auto-populates on first run

### AI Adjudication:
- Requires `OPENAI_API_KEY` environment variable
- Without it, uses fallback heuristic scoring
- AI features work with GPT-4o-mini for cost efficiency

---

## Project Structure
```
/home/vec/clawd/projects/falsifi/
├── app.py              # Main Flask application
├── models.py           # Database models
├── ai_adjudicator.py   # AI scoring logic
├── requirements.txt    # Python dependencies
├── Procfile           # Deployment config
├── Dockerfile         # Container config
├── render.yaml        # Render.com config
├── templates/         # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── bounties.html
│   └── ... (7 more)
└── static/css/
    └── style.css      # App styling
```

---

## Maintenance

To restart the local server:
```bash
cd /home/vec/clawd/projects/falsifi
pkill -f gunicorn  # Stop existing server
SECRET_KEY=falsifi-deploy-secret-key PORT=5000 gunicorn --bind 0.0.0.0:5000 --workers 1 app:app
```

To recreate the tunnel:
```bash
ssh -o StrictHostKeyChecking=no -R 80:localhost:5000 serveo.net
```
