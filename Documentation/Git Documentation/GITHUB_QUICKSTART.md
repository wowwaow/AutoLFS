# GitHub Quick Reference Guide

## 🚀 Quick Start

### First-Time Setup

```bash
# Clone repository
git clone https://github.com/wowwaow/AutoLFS.git
cd AutoLFS

# Set up your identity
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# Add upstream remote
git remote add upstream https://github.com/wowwaow/AutoLFS.git
```

## 📋 Common Commands

### Daily Operations

```bash
# Get latest changes
git fetch origin
git pull origin main

# Create new branch
git checkout -b feature/your-feature

# Stage and commit changes
git add .                   # Stage all changes
git add file1.txt file2.txt # Stage specific files
git commit -m "feat: add new feature"

# Push changes
git push origin feature/your-feature
```

### Branch Management

```bash
# List branches
git branch -a              # List all branches
git branch -v             # List branches with last commit

# Switch branches
git checkout main
git checkout -b new-branch

# Update branch from main
git checkout your-branch
git rebase main

# Delete branch
git branch -d branch-name  # Local delete
git push origin --delete branch-name  # Remote delete
```

## 🔄 Common Workflows

### 1. Starting New Work

```bash
# Update main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/new-feature
```

### 2. Submitting Changes

```bash
# Update your branch
git fetch upstream
git rebase upstream/main

# Stage and commit
git add .
git commit -m "type(scope): description"

# Push changes
git push origin feature/new-feature
```

### 3. Updating Pull Request

```bash
# After making requested changes
git add .
git commit -m "fix: address review comments"
git push origin feature/new-feature
```

## 🛠️ Troubleshooting

### Common Issues

1. **Merge Conflicts**
   ```bash
   # Approach 1: Rebase
   git fetch upstream
   git rebase upstream/main
   # Fix conflicts in files
   git add .
   git rebase --continue

   # Approach 2: Merge
   git merge upstream/main
   # Fix conflicts
   git add .
   git commit -m "fix: resolve merge conflicts"
   ```

2. **Wrong Branch**
   ```bash
   # Save changes
   git stash

   # Switch to correct branch
   git checkout correct-branch
   git stash pop
   ```

3. **Undo Last Commit**
   ```bash
   # Undo commit but keep changes
   git reset --soft HEAD^

   # Undo commit and discard changes
   git reset --hard HEAD^
   ```

## 📝 Commit Messages

### Format

```
type(scope): subject

[optional body]

[optional footer]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Tests
- `chore`: Maintenance

## 🚨 Emergency Procedures

### 1. Revert Last Push

```bash
# Revert last commit
git revert HEAD
git push origin your-branch
```

### 2. Reset to Clean State

```bash
# Hard reset to remote
git fetch origin
git reset --hard origin/main
```

### 3. Recover Deleted Work

```bash
# List recent commits
git reflog

# Recover to specific point
git checkout -b recovery-branch hash
```

## 🔍 Useful Commands

### Status and Inspection

```bash
# Status overview
git status

# Commit history
git log --oneline --graph

# File history
git log -p filename

# Change comparison
git diff main...your-branch
```

### Maintenance

```bash
# Clean untracked files
git clean -n  # Dry run
git clean -fd # Force clean

# Prune old branches
git remote prune origin
```

## 🎯 Best Practices

1. **Before Starting Work**
   ```bash
   git pull origin main
   git checkout -b feature/specific-name
   ```

2. **Before Submitting PR**
   ```bash
   git fetch upstream
   git rebase upstream/main
   git push origin feature/specific-name
   ```

3. **Regular Maintenance**
   ```bash
   # Update remotes
   git fetch --all
   git remote prune origin

   # Clean local branches
   git branch --merged | egrep -v "(^\*|main|dev)" | xargs git branch -d
   ```

## 🆘 Quick Help

### Common Error Solutions

1. **Permission Denied**
   ```bash
   # Check remote URL
   git remote -v
   
   # Update to SSH if needed
   git remote set-url origin git@github.com:wowwaow/AutoLFS.git
   ```

2. **Rejected Push**
   ```bash
   git pull origin main
   git rebase main
   git push origin your-branch
   ```

3. **Dirty Working Directory**
   ```bash
   # Stash changes
   git stash
   
   # Perform operation
   
   # Restore changes
   git stash pop
   ```

## 📚 Additional Resources

- [Full Documentation](GITHUB_INTEGRATION.md)
- [Git Documentation](https://git-scm.com/doc)
- [GitHub Guides](https://guides.github.com)
- [GitHub CLI Manual](https://cli.github.com/manual)

---

**Note**: For more detailed information, refer to the complete [GitHub Integration Documentation](GITHUB_INTEGRATION.md).

