# CI/CD Setup Guide for TravelMind

## Overview

This document explains the CI/CD pipeline setup for the TravelMind project using GitHub Actions and pre-commit hooks.

---

## Table of Contents

1. [GitHub Actions Workflows](#github-actions-workflows)
2. [Pre-commit Hooks Setup](#pre-commit-hooks-setup)
3. [Required Secrets](#required-secrets)
4. [Local Development](#local-development)
5. [Deployment Process](#deployment-process)
6. [Troubleshooting](#troubleshooting)

---

## GitHub Actions Workflows

### 1. CI Pipeline (`.github/workflows/ci.yml`)

**Triggers:** Push to `main` or `develop`, Pull Requests

**Jobs:**
- **Backend Tests** - Runs pytest with coverage on PostgreSQL
- **Frontend Tests** - Lints and builds React app
- **Security Scan** - Trivy vulnerability scanning + Safety check
- **Docker Build** - Tests Docker image builds
- **Integration Tests** - Runs full stack with docker-compose
- **Build Status** - Final status check

**Features:**
- ✅ Automated testing on every push/PR
- ✅ Code coverage reports uploaded to Codecov
- ✅ Security vulnerability scanning
- ✅ Docker build verification
- ✅ Full integration testing

### 2. Deployment Pipeline (`.github/workflows/deploy.yml`)

**Triggers:** Push to `main`, Tags (`v*`), Manual dispatch

**Jobs:**
- **Build & Push** - Builds Docker images and pushes to GitHub Container Registry
- **Deploy** - SSH deployment to production server
- **Notify** - Deployment status notification

**Features:**
- ✅ Automatic Docker image builds
- ✅ Semantic versioning support
- ✅ Production deployment
- ✅ Health checks

### 3. PR Checks (`.github/workflows/pr-checks.yml`)

**Triggers:** Pull Request events

**Jobs:**
- **Code Review** - Automated code review with Reviewdog
- **Security Check** - CodeQL security analysis
- **Coverage Check** - Test coverage comments on PR
- **Size Check** - Bundle size monitoring
- **PR Labeler** - Automatic PR labeling

**Features:**
- ✅ Automated code review feedback
- ✅ Security analysis
- ✅ Coverage reports in PR comments
- ✅ Bundle size tracking

---

## Pre-commit Hooks Setup

### Installation

1. **Install pre-commit:**
   ```bash
   pip install pre-commit
   ```

2. **Install hooks:**
   ```bash
   cd /path/to/TravelMind
   pre-commit install
   ```

3. **Run manually (optional):**
   ```bash
   pre-commit run --all-files
   ```

### Configured Hooks

**General:**
- Trailing whitespace removal
- End-of-file fixer
- YAML/JSON validation
- Large file detection
- Private key detection
- Merge conflict detection

**Python (Backend):**
- **Black** - Code formatter (line-length: 120)
- **Flake8** - Linter
- **isort** - Import sorting
- **Bandit** - Security linter

**JavaScript (Frontend):**
- **Prettier** - Code formatter
- **ESLint** - Linter with auto-fix

**Other:**
- **detect-secrets** - Prevents committing secrets
- **hadolint** - Dockerfile linting
- **markdownlint** - Markdown formatting

### Bypassing Hooks

**Skip all hooks:**
```bash
git commit --no-verify -m "message"
```

**Skip specific hook:**
```bash
SKIP=flake8 git commit -m "message"
```

---

## Required Secrets

Configure these in GitHub Settings → Secrets and Variables → Actions:

### For Deployment (`.github/workflows/deploy.yml`)

| Secret | Description | Example |
|--------|-------------|---------|
| `DEPLOY_HOST` | Production server hostname | `your-server.com` |
| `DEPLOY_USER` | SSH username | `ubuntu` |
| `DEPLOY_SSH_KEY` | Private SSH key for deployment | `-----BEGIN OPENSSH PRIVATE KEY-----...` |

### Optional Secrets

| Secret | Description | Used For |
|--------|-------------|----------|
| `CODECOV_TOKEN` | Codecov upload token | Coverage reports |
| `SLACK_WEBHOOK` | Slack notification URL | Deployment notifications |

### Setting Up SSH Key

1. **Generate SSH key pair:**
   ```bash
   ssh-keygen -t ed25519 -C "github-actions-travelmind" -f deploy_key
   ```

2. **Add public key to server:**
   ```bash
   ssh-copy-id -i deploy_key.pub user@your-server.com
   ```

3. **Add private key to GitHub Secrets:**
   - Go to GitHub repository → Settings → Secrets → New secret
   - Name: `DEPLOY_SSH_KEY`
   - Value: Contents of `deploy_key` (private key)

---

## Local Development

### Running Tests Locally

**Backend:**
```bash
cd backend
pytest tests/ -v --cov
```

**Frontend:**
```bash
cd frontend
npm test
```

### Running Pre-commit Checks Locally

**All checks:**
```bash
pre-commit run --all-files
```

**Specific check:**
```bash
pre-commit run black --all-files
pre-commit run flake8 --all-files
```

### Docker Build Locally

**Backend:**
```bash
docker build -t travelmind-backend:local ./backend
```

**Frontend:**
```bash
docker build -t travelmind-frontend:local ./frontend
```

**Full stack:**
```bash
docker-compose up --build
```

---

## Deployment Process

### Automatic Deployment (Recommended)

1. **Merge to main branch:**
   ```bash
   git checkout main
   git merge develop
   git push origin main
   ```

2. **GitHub Actions automatically:**
   - Runs all tests
   - Builds Docker images
   - Pushes to container registry
   - Deploys to production server

3. **Monitor deployment:**
   - Go to Actions tab in GitHub
   - Watch deployment workflow
   - Check logs for any issues

### Manual Deployment

1. **Trigger workflow manually:**
   - Go to Actions → Deploy to Production
   - Click "Run workflow"
   - Select branch → Run

2. **Or use deployment script:**
   ```bash
   ./scripts/deploy.sh  # Create this script
   ```

### Rollback

**Using Docker tags:**
```bash
# On production server
cd /path/to/travelmind
docker-compose pull travelmind-backend:v1.0.0  # Previous version
docker-compose up -d
```

**Using Git:**
```bash
git revert <commit-hash>
git push origin main
# CI/CD will auto-deploy reverted version
```

---

## Workflow Status Badges

Add these to your README.md:

```markdown
![CI](https://github.com/YOUR_USERNAME/TravelMind/workflows/CI%2FCD%20Pipeline/badge.svg)
![Deploy](https://github.com/YOUR_USERNAME/TravelMind/workflows/Deploy%20to%20Production/badge.svg)
[![codecov](https://codecov.io/gh/YOUR_USERNAME/TravelMind/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_USERNAME/TravelMind)
```

---

## Troubleshooting

### Tests Failing in CI but Pass Locally

**Problem:** Environment differences

**Solution:**
```bash
# Use same Python version as CI
pyenv install 3.11
pyenv local 3.11

# Use PostgreSQL like CI
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=test postgres:15-alpine
DATABASE_URL=postgresql://postgres:test@localhost:5432/test pytest
```

### Docker Build Fails

**Problem:** Build context too large

**Solution:** Add to `.dockerignore`:
```
node_modules
__pycache__
.git
*.pyc
.pytest_cache
coverage.xml
```

### Pre-commit Hook Takes Too Long

**Problem:** Running on too many files

**Solution:**
```bash
# Update specific hook to run only on staged files
# Edit .pre-commit-config.yaml
```

### Deployment Hangs

**Problem:** SSH connection issues

**Solution:**
1. Verify SSH key is correct in secrets
2. Check server firewall allows GitHub IPs
3. Test SSH connection manually:
   ```bash
   ssh -i deploy_key user@your-server.com
   ```

### Coverage Reports Not Appearing

**Problem:** Codecov token not set

**Solution:**
1. Sign up at codecov.io
2. Add `CODECOV_TOKEN` to GitHub secrets
3. Retry workflow

---

## Best Practices

### 1. Branch Protection Rules

Configure in GitHub Settings → Branches:
- ✅ Require pull request reviews
- ✅ Require status checks to pass
- ✅ Require branches to be up to date
- ✅ Require conversation resolution
- ✅ No force pushes
- ✅ No deletions

### 2. Commit Message Convention

Use conventional commits:
```
feat: add user authentication
fix: resolve database connection timeout
docs: update API documentation
test: add tests for trip endpoints
chore: update dependencies
```

### 3. PR Process

1. Create feature branch: `git checkout -b feature/new-feature`
2. Make changes and commit
3. Push and create PR
4. Wait for CI checks ✅
5. Request review
6. Merge after approval

### 4. Versioning

Use semantic versioning:
```bash
# Patch release (bug fixes)
git tag v1.0.1
git push origin v1.0.1

# Minor release (new features)
git tag v1.1.0
git push origin v1.1.0

# Major release (breaking changes)
git tag v2.0.0
git push origin v2.0.0
```

---

## Monitoring

### CI/CD Metrics to Track

1. **Build Time:** Target < 10 minutes
2. **Test Coverage:** Target > 80%
3. **Deployment Frequency:** Track daily/weekly
4. **Failure Rate:** Target < 5%
5. **Time to Recovery:** Target < 1 hour

### Recommended Tools

- **Sentry** - Error tracking
- **LogRocket** - Session replay
- **Datadog/New Relic** - APM monitoring
- **Better Uptime** - Uptime monitoring

---

## Cost Optimization

### GitHub Actions

- ✅ Use caching for dependencies
- ✅ Use matrix builds sparingly
- ✅ Cancel redundant workflows
- ✅ Use self-hosted runners for heavy workloads

### Docker Images

- ✅ Use multi-stage builds
- ✅ Minimize layers
- ✅ Use `.dockerignore`
- ✅ Cache npm/pip packages

---

## Security Considerations

1. **Never commit secrets** - Use GitHub Secrets
2. **Rotate SSH keys** - Every 90 days
3. **Review dependabot PRs** - Keep dependencies updated
4. **Enable branch protection** - Prevent direct pushes to main
5. **Use signed commits** - Optional but recommended

---

## Next Steps

1. ✅ Install pre-commit hooks
2. ✅ Configure GitHub Secrets
3. ✅ Set up branch protection
4. ✅ Add status badges to README
5. ✅ Test the pipeline with a PR
6. ✅ Configure deployment server
7. ✅ Set up monitoring tools

---

**Last Updated:** 2025-10-31
**Maintained by:** TravelMind Team
**Questions?** Open an issue on GitHub
