# Complete GitHub Setup Guide

This guide provides step-by-step instructions for setting up and configuring the AutoLFS GitHub repository, including both automated and manual steps.

## Table of Contents

1. [Initial Setup](#initial-setup)
2. [Repository Configuration](#repository-configuration)
3. [Security Setup](#security-setup)
4. [GitHub Pages](#github-pages)
5. [Automation](#automation)
6. [Manual Configurations](#manual-configurations)

## Initial Setup

### 1. Repository Creation

```bash
# Create local repository
git init
git add .
git commit -m "Initial commit"

# Create GitHub repository
gh repo create wowwaow/AutoLFS --public --description "Automated LFS + BLFS + Gaming on LFS"
git remote add origin https://github.com/wowwaow/AutoLFS.git
git push -u origin main
```

### 2. Basic Structure Setup

```bash
# Create essential directories
mkdir -p .github/{workflows,ISSUE_TEMPLATE}
mkdir -p docs
mkdir -p Documentation/{API,Guides,Reference}

# Create template files
touch .github/pull_request_template.md
touch .github/ISSUE_TEMPLATE/{bug_report.md,feature_request.md}
```

## Repository Configuration

### 1. GitHub Settings (Manual Steps)

Access: `https://github.com/wowwaow/AutoLFS/settings`

#### Features to Enable:
- [x] Issues
- [x] Projects
- [x] Discussions
- [x] Wiki
- [x] Sponsorships

#### Branch Protection Rules:
1. Go to Settings → Branches → Branch protection rules
2. Click "Add rule"
3. Configure:
   ```
   Branch name pattern: main
   Require pull request reviews: ✓
   Required approving reviews: 1
   Dismiss stale pull request approvals: ✓
   Require status checks to pass: ✓
   Require branches to be up to date: ✓
   Include administrators: ✓
   Allow force pushes: ✗
   Allow deletions: ✗
   ```

### 2. Automated Configurations

```bash
# Configure repository settings
gh api -X PATCH /repos/wowwaow/AutoLFS \
  -f allow_squash_merge=true \
  -f allow_merge_commit=false \
  -f allow_rebase_merge=true \
  -f delete_branch_on_merge=true

# Create labels
gh label create "build-system" --color 1D76DB --description "Build system changes"
gh label create "lfs-core" --color D93F0B --description "Core LFS functionality"
gh label create "automation" --color 0E8A16 --description "Automation features"
gh label create "performance" --color FEF2C0 --description "Performance improvements"
```

## Security Setup

### 1. Automated Security Features

```bash
# Enable security features
gh api -X PUT /repos/wowwaow/AutoLFS/vulnerability-alerts
gh api -X PUT /repos/wowwaow/AutoLFS/automated-security-fixes
```

### 2. Manual Security Settings

1. Go to Settings → Security
2. Enable:
   - [x] Dependabot alerts
   - [x] Dependabot security updates
   - [x] Code scanning
   - [x] Secret scanning
   - [x] Push protection

## GitHub Pages

### 1. Documentation Setup

```bash
# Set up documentation structure
mkdir -p docs/{_layouts,assets,css}
touch docs/_config.yml
touch docs/index.md

# Configure Jekyll
# Content in _config.yml:
theme: jekyll-theme-cayman
title: AutoLFS Documentation
description: Automated Linux From Scratch Build System
```

### 2. Manual GitHub Pages Activation

1. Go to Settings → Pages
2. Configure:
   - Source: Deploy from a branch
   - Branch: main
   - Folder: /docs
   - Click Save

## Automation

### 1. GitHub Actions Setup

```bash
# Create workflow files
cat > .github/workflows/system-logs.yml << 'EOF'
name: System Logs Automation
on:
  schedule:
    - cron: '0 0 * * *'
...
EOF

cat > .github/workflows/maintenance.yml << 'EOF'
name: System Maintenance
on:
  schedule:
    - cron: '0 2 * * 0'
...
EOF
```

### 2. Project Board Setup

1. Go to Projects tab
2. Create new project:
   - Template: Automated kanban
   - Name: AutoLFS Development
   - Columns:
     * To Do
     * In Progress
     * Review
     * Done

## Manual Configurations

### 1. Discussions Setup

1. Go to Settings → Features
2. Enable Discussions
3. Set up categories:
   - Announcements 📢
   - Ideas 💡
   - Q&A ❓
   - Show and tell 🙌
   - General 💬

### 2. Environment Setup

1. Go to Settings → Environments
2. Create environments:
   - Production
   - Staging
   - Development
3. Configure environment protection rules

### 3. Secrets Configuration

1. Go to Settings → Secrets and variables
2. Add repository secrets:
   - DOCKER_TOKEN
   - DEPLOY_KEY
   - CI_TOKEN

## Post-Setup Verification

### 1. Check Automated Features

```bash
# Verify workflows
gh workflow list

# Check security alerts
gh api /repos/wowwaow/AutoLFS/vulnerability-alerts

# Verify labels
gh label list
```

### 2. Manual Verification

1. Review branch protection:
   - Try direct push to main (should fail)
   - Create PR (should require review)

2. Check GitHub Pages:
   - Visit https://wowwaow.github.io/AutoLFS
   - Verify documentation rendering

3. Verify automations:
   - Create test issue (check automation)
   - Create test PR (check automation)
   - Check Dependabot alerts

## Maintenance

### Regular Tasks

1. Review and update workflows monthly
2. Check and update dependencies weekly
3. Review security alerts daily
4. Update documentation as needed

### Documentation Updates

1. Keep setup guide current
2. Update API documentation
3. Maintain user guides
4. Review and update templates

## Troubleshooting

### Common Issues

1. **Workflow Failures**
   ```bash
   gh run list --limit 10
   gh run view <run-id>
   ```

2. **Permission Issues**
   - Check repository roles
   - Verify workflow permissions
   - Review environment access

3. **Documentation Problems**
   - Verify Jekyll build
   - Check markdown formatting
   - Validate links

## Support

For assistance with setup:
1. Create issue in repository
2. Join discussions
3. Contact maintainers

---

**Note**: Keep this guide updated as repository configurations change. Last updated: 2025-05-31

