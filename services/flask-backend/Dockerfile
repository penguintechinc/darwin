# Flask Backend Dockerfile
# Multi-stage build: Builder stage for Python dependencies, Runtime stage for Flask app

FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    curl \
    pkg-config \
    libicu-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Python linting/security tools in venv
RUN pip install --no-cache-dir \
    flake8==7.1.1 \
    black==24.10.0 \
    isort==5.13.2 \
    mypy==1.14.0 \
    bandit==1.8.0 \
    safety==3.2.11 \
    pylint==3.3.3 \
    pyright==1.1.390 \
    ruff==0.9.2 \
    pip-licenses==5.0.0 \
    scancode-toolkit==32.3.0

# Production stage - lean runtime for Flask application
FROM python:3.13-slim AS runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    wget \
    git \
    ca-certificates \
    gnupg \
    lsb-release \
    apt-transport-https \
    unzip \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user early
RUN useradd --create-home --shell /bin/bash appuser

# ============================================================================
# Git CLI Tools (gh and glab)
# NOTE: Development and CI/CD tools should be in CI/CD pipelines, not runtime container
# ============================================================================

# COMMENTED OUT: GitHub CLI (gh) - Not needed for runtime Flask container
# Install GitHub CLI (gh)
# RUN mkdir -p /etc/apt/keyrings && \
#     wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null && \
#     chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && \
#     echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
#     apt-get update && \
#     apt-get install -y gh && \
#     rm -rf /var/lib/apt/lists/*

# Install GitLab CLI (glab) - Commented out due to download issues
# RUN curl -sSL https://gitlab.com/gitlab-org/cli/-/releases/download/v1.47.0/glab_1.47.0_Linux_x86_64.tar.gz | \
#     tar -xz -C /tmp && \
#     mv /tmp/bin/glab /usr/local/bin/ && \
#     chmod +x /usr/local/bin/glab && \
#     rm -rf /tmp/bin

# ============================================================================
# Node.js and JavaScript/TypeScript Linters
# NOTE: Development tools should be in CI/CD pipelines or separate containers, not runtime
# ============================================================================

# COMMENTED OUT: Node.js and JavaScript tooling - Not needed for Python Flask runtime
# Install Node.js 20.x LTS
# RUN mkdir -p /etc/apt/keyrings && \
#     curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | \
#     gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
#     echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | \
#     tee /etc/apt/sources.list.d/nodesource.list && \
#     apt-get update && \
#     apt-get install -y nodejs && \
#     rm -rf /var/lib/apt/lists/*

# Install JavaScript/TypeScript linters globally
# RUN npm install -g \
#     eslint@9.17.0 \
#     @typescript-eslint/parser@8.18.2 \
#     @typescript-eslint/eslint-plugin@8.18.2 \
#     prettier@3.4.2 \
#     typescript@5.7.2

# ============================================================================
# Go and Go Linters
# NOTE: Go tooling should be in CI/CD pipelines or separate build containers
# ============================================================================

# COMMENTED OUT: Go toolchain and linters - Not needed for Python Flask runtime
# Install Go 1.24
# RUN wget -qO- https://go.dev/dl/go1.24.2.linux-amd64.tar.gz | \
#     tar -C /usr/local -xzf -
# ENV PATH="/usr/local/go/bin:/root/go/bin:${PATH}"
# ENV GOPATH="/root/go"

# Install golangci-lint (comprehensive Go linter suite)
# RUN curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | \
#     sh -s -- -b /usr/local/bin v1.62.2

# Install gosec (Go security scanner)
# RUN go install github.com/securego/gosec/v2/cmd/gosec@latest && \
#     cp /root/go/bin/gosec /usr/local/bin/

# ============================================================================
# Terraform and HCL Linters
# NOTE: IaC tools should be in CI/CD pipelines or separate containers
# ============================================================================

# COMMENTED OUT: Terraform and related tools - Not needed for Flask application runtime
# Install Terraform
# RUN wget -qO- https://apt.releases.hashicorp.com/gpg | \
#     gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
#     echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
#     tee /etc/apt/sources.list.d/hashicorp.list && \
#     apt-get update && \
#     apt-get install -y terraform && \
#     rm -rf /var/lib/apt/lists/*

# Install tflint (Terraform linter)
# RUN curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash

# Install tfsec (Terraform security scanner)
# RUN curl -sSL https://github.com/aquasecurity/tfsec/releases/download/v1.28.11/tfsec-linux-amd64 \
#     -o /usr/local/bin/tfsec && \
#     chmod +x /usr/local/bin/tfsec

# Install checkov (IaC security scanner - Python-based)
# COMMENTED OUT: checkov requires rustworkx which needs Rust compiler (adds 1GB+ to image)
# Checkov should be executed in CI/CD pipelines instead, not in runtime container
# Uncomment if needed for development, but add Rust compiler first:
# RUN apt-get update && apt-get install -y rustc cargo && rm -rf /var/lib/apt/lists/* && \
#     pip3 install --no-cache-dir checkov==3.2.319

# ============================================================================
# Ansible Linters
# NOTE: Ansible is an IaC tool that should be in CI/CD pipelines, not runtime
# ============================================================================

# COMMENTED OUT: Ansible and ansible-lint - Not needed for Flask application runtime
# Install Ansible and ansible-lint (use pip instead of apt for latest versions)
# RUN pip3 install --no-cache-dir \
#     ansible==11.1.0 \
#     ansible-lint==24.12.2

# ============================================================================
# Kubernetes/Container Linters
# NOTE: Kubernetes tools should be in CI/CD pipelines or separate containers
# ============================================================================

# COMMENTED OUT: Kubernetes tools (kubectl, kubeval, kube-linter) - Not needed for Flask runtime
# Install kubectl
# RUN curl -sSL "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
#     -o /usr/local/bin/kubectl && \
#     chmod +x /usr/local/bin/kubectl

# Install kubeval (Kubernetes manifest validator)
# RUN curl -sSL https://github.com/instrumenta/kubeval/releases/download/v0.16.1/kubeval-linux-amd64.tar.gz | \
#     tar xz && \
#     mv kubeval /usr/local/bin/ && \
#     chmod +x /usr/local/bin/kubeval

# Install kube-linter (Kubernetes YAML linter)
# RUN curl -sSL https://github.com/stackrox/kube-linter/releases/download/v0.7.1/kube-linter-linux.tar.gz | \
#     tar xz && \
#     mv kube-linter /usr/local/bin/ && \
#     chmod +x /usr/local/bin/kube-linter

# COMMENTED OUT: Hadolint (Dockerfile linter) - Development/CI tool, not needed at runtime
# Install hadolint (Dockerfile linter)
# RUN curl -sSL https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64 \
#     -o /usr/local/bin/hadolint && \
#     chmod +x /usr/local/bin/hadolint

# ============================================================================
# GitHub Actions and CI/CD Linters
# NOTE: CI/CD and workflow tools should be in CI/CD pipelines, not runtime
# ============================================================================

# COMMENTED OUT: actionlint (GitHub Actions workflow linter) - Not needed for Flask runtime
# Install actionlint (GitHub Actions workflow linter)
# RUN curl -sSL https://github.com/rhysd/actionlint/releases/download/v1.7.4/actionlint_1.7.4_linux_amd64.tar.gz | \
#     tar xz -C /usr/local/bin && \
#     chmod +x /usr/local/bin/actionlint

# ============================================================================
# Security Scanners
# NOTE: Security scanning tools should be in CI/CD pipelines, not runtime container
# ============================================================================

# COMMENTED OUT: gitleaks (secrets detection) - Should be in CI/CD pipeline
# Install gitleaks (secrets detection)
# RUN curl -sSL https://github.com/gitleaks/gitleaks/releases/download/v8.21.3/gitleaks_8.21.3_linux_x64.tar.gz | \
#     tar xz && \
#     mv gitleaks /usr/local/bin/ && \
#     chmod +x /usr/local/bin/gitleaks

# COMMENTED OUT: trivy (vulnerability scanner) - Should be in CI/CD pipeline
# Install trivy (vulnerability scanner for containers and dependencies)
# RUN curl -sSL https://github.com/aquasecurity/trivy/releases/download/v0.58.2/trivy_0.58.2_Linux-64bit.tar.gz | \
#     tar xz -C /usr/local/bin && \
#     chmod +x /usr/local/bin/trivy

# COMMENTED OUT: semgrep (SAST tool) - Should be in CI/CD pipeline, not runtime
# Install semgrep (SAST tool for multiple languages)
# RUN pip3 install --no-cache-dir semgrep==1.99.0

# COMMENTED OUT: grype (vulnerability scanner) - Should be in CI/CD pipeline
# Install grype (vulnerability scanner)
# RUN curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin

# COMMENTED OUT: CycloneDX CLI (SBOM and license scanner) - Should be in CI/CD pipeline
# Install CycloneDX CLI (SBOM and license scanner)
# RUN curl -sSL https://github.com/CycloneDX/cyclonedx-cli/releases/download/v0.27.3/cyclonedx-linux-x64 \
#     -o /usr/local/bin/cyclonedx && \
#     chmod +x /usr/local/bin/cyclonedx

# ============================================================================
# Advanced Static Analyzers
# NOTE: Static analysis tools (Infer, Cppcheck, Clang, PMD, SonarScanner) should be in CI/CD pipelines
# ============================================================================

# COMMENTED OUT: Infer (Facebook's static analyzer for Java, C, C++, Objective-C)
# Infer tarball download or extraction is failing (dependency/compatibility issues)
# Infer should be executed in CI/CD pipelines instead, not in runtime container
# To use Infer: Install separately in CI/CD jobs or development environments as needed
# RUN apt-get update && \
#     apt-get install -y opam m4 && \
#     rm -rf /var/lib/apt/lists/* && \
#     curl -sSL https://github.com/facebook/infer/releases/download/v1.2.0/infer-linux-x64-v1.2.0.tar.xz \
#     -o /tmp/infer.tar.xz && \
#     tar -C /opt -xf /tmp/infer.tar.xz && \
#     ln -s /opt/infer-linux-x64-v1.2.0/bin/infer /usr/local/bin/infer && \
#     rm /tmp/infer.tar.xz

# COMMENTED OUT: Cppcheck (C/C++ static analyzer) - Not needed for Python Flask runtime
# Install Cppcheck (C/C++ static analyzer)
# RUN apt-get update && \
#     apt-get install -y cppcheck && \
#     rm -rf /var/lib/apt/lists/*

# COMMENTED OUT: Clang Static Analyzer (scan-build) - Not needed for Python Flask runtime
# Install Clang Static Analyzer (scan-build)
# RUN apt-get update && \
#     apt-get install -y clang clang-tools && \
#     rm -rf /var/lib/apt/lists/*

# COMMENTED OUT: Spotbugs (Java static analyzer) - Not needed for Python Flask runtime
# Install Spotbugs (Java static analyzer) - requires Java
# openjdk-17-jdk-headless package is not available in Debian-slim base image
# SpotBugs is a Java static analyzer not needed at runtime in a Python Flask container
# SpotBugs should be executed in CI/CD pipelines instead, not in runtime container
# To use SpotBugs: Install separately in CI/CD jobs or development environments as needed
# RUN apt-get update && \
#     apt-get install -y openjdk-17-jdk-headless && \
#     rm -rf /var/lib/apt/lists/* && \
#     curl -sSL https://github.com/spotbugs/spotbugs/releases/download/4.8.6/spotbugs-4.8.6.tgz \
#     -o /tmp/spotbugs.tgz && \
#     tar -C /opt -xzf /tmp/spotbugs.tgz && \
#     ln -s /opt/spotbugs-4.8.6/bin/spotbugs /usr/local/bin/spotbugs && \
#     rm /tmp/spotbugs.tgz

# COMMENTED OUT: PMD (Java source code analyzer) - Not needed for Python Flask runtime
# Install PMD (Java source code analyzer)
# RUN curl -sSL https://github.com/pmd/pmd/releases/download/pmd_releases%2F7.8.0/pmd-dist-7.8.0-bin.zip \
#     -o /tmp/pmd.zip && \
#     unzip -q /tmp/pmd.zip -d /opt && \
#     ln -s /opt/pmd-bin-7.8.0/bin/pmd /usr/local/bin/pmd && \
#     rm /tmp/pmd.zip

# COMMENTED OUT: SonarScanner CLI (multi-language static analysis) - Should be in CI/CD pipeline
# Install SonarScanner CLI (multi-language static analysis)
# RUN curl -sSL https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-6.2.1.4610-linux-x64.zip \
#     -o /tmp/sonar.zip && \
#     unzip -q /tmp/sonar.zip -d /opt && \
#     ln -s /opt/sonar-scanner-6.2.1.4610-linux-x64/bin/sonar-scanner /usr/local/bin/sonar-scanner && \
#     rm /tmp/sonar.zip

# ============================================================================
# Additional Language Linters
# NOTE: Development linters should be in CI/CD pipelines or separate containers
# ============================================================================

# COMMENTED OUT: ShellCheck (shell script linter) - Not needed for Flask runtime
# Install ShellCheck (shell script linter)
# RUN apt-get update && \
#     apt-get install -y shellcheck && \
#     rm -rf /var/lib/apt/lists/*

# COMMENTED OUT: yamllint (YAML linter) - Should be in CI/CD pipeline, not runtime
# Install yamllint (YAML linter)
# RUN pip3 install --no-cache-dir yamllint==1.35.1

# COMMENTED OUT: markdownlint-cli (Markdown linter) - Not needed for Flask runtime
# Install markdownlint-cli (Markdown linter)
# RUN npm install -g markdownlint-cli@0.43.0

# COMMENTED OUT: jsonlint (JSON linter) - Not needed for Flask runtime
# Install jsonlint (JSON linter)
# RUN npm install -g jsonlint@1.6.3

# ============================================================================
# Ruby and PHP linters
# NOTE: Ruby and PHP tools are not needed in a Python Flask container
# ============================================================================

# COMMENTED OUT: RuboCop (Ruby linter) - Not needed for Python Flask runtime
# RuboCop requires Ruby installation which bloats the image
# Install Ruby and rubocop
# RUN apt-get update && \
#     apt-get install -y ruby-full && \
#     gem install rubocop -v 1.69.2 && \
#     rm -rf /var/lib/apt/lists/*

# COMMENTED OUT: PHP and PHP Code Sniffer (phpcs) - Not needed for Python Flask runtime
# Install PHP and phpcs
# RUN apt-get update && \
#     apt-get install -y php-cli php-xml composer && \
#     rm -rf /var/lib/apt/lists/*

# RUN composer global require "squizlabs/php_codesniffer=*" && \
#     ln -s /root/.composer/vendor/bin/phpcs /usr/local/bin/phpcs

# ============================================================================
# Copy Python virtual environment from builder
# ============================================================================

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ============================================================================
# Application Setup
# ============================================================================

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Environment variables
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5000
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz')" || exit 1

# Run with gunicorn in production
# Using 1 worker initially to allow database initialization, scale workers via env var
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", \
     "--worker-class", "gthread", "--access-logfile", "-", "--error-logfile", "-", \
     "--timeout", "120", \
     "app:create_app()"]
