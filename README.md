# Falsifi - Refutation Bounty Platform

A Flask-based platform where users can post bounties on claims they want challenged, and earn rewards by providing quality refutations.

## Features

- Post bounties on claims/ideas you want challenged
- Submit refutations and earn rewards
- AI-powered quality screening
- User reputation system
- Leaderboard

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional)
export OPENAI_API_KEY="your-api-key"

# Run the app
python app.py
```

Visit http://localhost:5000

## Demo Accounts

- alice / alice@example.com
- bob / bob@example.com
- charlie / charlie@example.com
- demo_user / demo@example.com

## Deployment

This app can be deployed to Railway, Fly.io, Render, or any container platform.

### Environment Variables

- `SECRET_KEY` - Flask secret key
- `OPENAI_API_KEY` - OpenAI API key for AI adjudication (optional)
- `DATABASE_URL` - Database URL (defaults to SQLite)
- `PORT` - Port to run on (set automatically by most platforms)

## License

MIT
