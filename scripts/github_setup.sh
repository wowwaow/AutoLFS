#!/usr/bin/env bash

# GitHub Repository Setup Automation Script
# Version: 1.0
# Last Updated: 2025-05-31

set -euo pipefail
IFS=$'\n\t'

# Color definitions
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
REPO_OWNER="wowwaow"
REPO_NAME="AutoLFS"
REPO_DESCRIPTION="Automated LFS + BLFS + Gaming on LFS"
REPO_URL="https://github.com/$REPO_OWNER/$REPO_NAME"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Error handling
handle_error() {
    log_error "An error occurred on line $1"
    exit 1
}

trap 'handle_error $LINENO' ERR

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check for gh CLI
    if ! command -v gh &> /dev/null; then
        log_error "GitHub CLI (gh) is not installed. Please install it first."
        exit 1
    fi
    
    # Check for git
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed. Please install it first."
        exit 1
    fi
    
    # Check gh auth status
    if ! gh auth status &> /dev/null; then
        log_error "Not authenticated with GitHub. Please run 'gh auth login' first."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Create directory structure
create_directory_structure() {
    log_info "Creating directory structure..."
    
    mkdir -p .github/{workflows,ISSUE_TEMPLATE}
    mkdir -p docs/{_layouts,assets,css}
    mkdir -p Documentation/{API,Guides,Reference}
    
    touch .github/pull_request_template.md
    touch .github/ISSUE_TEMPLATE/{bug_report.md,feature_request.md}
    touch docs/{_config.yml,index.md}
    
    log_success "Directory structure created"
}

# Configure repository settings
configure_repository() {
    log_info "Configuring repository settings..."
    
    gh api -X PATCH "/repos/$REPO_OWNER/$REPO_NAME" \
        -f allow_squash_merge=true \
        -f allow_merge_commit=false \
        -f allow_rebase_merge=true \
        -f delete_branch_on_merge=true \
        -f has_issues=true \
        -f has_projects=true \
        -f has_wiki=true \
        -f has_downloads=true \
        -f has_discussions=true || log_warning "Some repository settings could not be configured"
    
    log_success "Repository settings configured"
}

# Create labels
create_labels() {
    log_info "Creating repository labels..."
    
    local labels=(
        "build-system|1D76DB|Build system changes"
        "lfs-core|D93F0B|Core LFS functionality"
        "automation|0E8A16|Automation features"
        "performance|FEF2C0|Performance improvements"
    )
    
    for label in "${labels[@]}"; do
        IFS='|' read -r name color description <<< "$label"
        gh label create "$name" --color "$color" --description "$description" || log_warning "Failed to create label: $name"
    done
    
    log_success "Labels created"
}

# Configure security features
configure_security() {
    log_info "Configuring security features..."
    
    gh api -X PUT "/repos/$REPO_OWNER/$REPO_NAME/vulnerability-alerts" || log_warning "Could not enable vulnerability alerts"
    gh api -X PUT "/repos/$REPO_OWNER/$REPO_NAME/automated-security-fixes" || log_warning "Could not enable automated security fixes"
    
    log_success "Security features configured"
}

# Create milestones
create_milestones() {
    log_info "Creating milestones..."
    
    local milestones=(
        "v1.0.0 - Initial Release|First stable release with core automation features"
        "v1.1.0 - Enhanced Build System|Improved build system with parallel processing and error recovery"
    )
    
    for milestone in "${milestones[@]}"; do
        IFS='|' read -r title description <<< "$milestone"
        gh api -X POST "/repos/$REPO_OWNER/$REPO_NAME/milestones" \
            -f title="$title" \
            -f description="$description" \
            -f state="open" || log_warning "Failed to create milestone: $title"
    done
    
    log_success "Milestones created"
}

# Verify setup
verify_setup() {
    log_info "Verifying setup..."
    
    local verified=true
    
    # Check workflows
    if ! gh workflow list &> /dev/null; then
        log_warning "No workflows found"
        verified=false
    fi
    
    # Check labels
    if ! gh label list &> /dev/null; then
        log_warning "No labels found"
        verified=false
    fi
    
    # Check security alerts
    if ! gh api "/repos/$REPO_OWNER/$REPO_NAME/vulnerability-alerts" &> /dev/null; then
        log_warning "Security alerts not properly configured"
        verified=false
    fi
    
    if [ "$verified" = true ]; then
        log_success "Setup verification completed successfully"
    else
        log_warning "Setup verification completed with warnings"
    fi
}

# Main setup function
main() {
    log_info "Starting GitHub repository setup for $REPO_OWNER/$REPO_NAME"
    
    check_prerequisites
    create_directory_structure
    configure_repository
    create_labels
    configure_security
    create_milestones
    verify_setup
    
    log_success "Setup completed successfully"
    log_info "Please complete manual configuration steps as outlined in the setup guide:"
    log_info "Documentation/Git Documentation/SETUP_GUIDE.md"
}

# Execute main function
main "$@"

