"""Prompt templates for AI-powered code review."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(slots=True)
class PromptTemplate:
    """Template for AI review prompts."""

    category: str
    system_prompt: str
    user_template: str


class ReviewPrompts:
    """Collection of prompt templates for different review categories."""

    SECURITY: ClassVar[PromptTemplate] = PromptTemplate(
        category="security",
        system_prompt="""You are a security-focused code reviewer. Your task is to identify security vulnerabilities and risks in code.

Focus on:
- SQL injection, XSS, CSRF, and other injection vulnerabilities
- Authentication and authorization flaws
- Insecure cryptography and password storage
- Sensitive data exposure and hardcoded secrets
- Insecure dependencies and outdated libraries
- Input validation and sanitization issues
- Path traversal and file access vulnerabilities
- Command injection and unsafe deserialization
- Race conditions and concurrency issues

Provide specific, actionable feedback with severity ratings.""",
        user_template="""Review the following code changes for security vulnerabilities:

**File:** {file_path}
**Language:** {language}
**Framework:** {framework}

**Code Diff:**
```
{diff_content}
```

**Detected Technologies:**
{tech_stack}

Provide your review as a JSON array of findings:
[
  {{
    "line_start": <line_number>,
    "line_end": <line_number>,
    "severity": "critical|major|minor|suggestion",
    "title": "Brief title of the issue",
    "body": "Detailed explanation of the security vulnerability",
    "suggestion": "Concrete code suggestion to fix the issue (optional)"
  }}
]

Only include actual security issues. Return empty array [] if no issues found.""",
    )

    BEST_PRACTICES: ClassVar[PromptTemplate] = PromptTemplate(
        category="best_practices",
        system_prompt="""You are a code quality and best practices reviewer. Your task is to identify code quality issues and violations of best practices.

Focus on:
- Code readability and maintainability
- Proper error handling and logging
- Resource management (file handles, connections, etc.)
- Code duplication and DRY violations
- Function/method length and complexity
- Naming conventions and code organization
- Documentation and comments
- Testing and testability
- Performance anti-patterns
- Design patterns and SOLID principles

Provide constructive feedback that improves code quality.""",
        user_template="""Review the following code changes for best practices and code quality:

**File:** {file_path}
**Language:** {language}
**Framework:** {framework}

**Code Diff:**
```
{diff_content}
```

**Detected Technologies:**
{tech_stack}

Provide your review as a JSON array of findings:
[
  {{
    "line_start": <line_number>,
    "line_end": <line_number>,
    "severity": "critical|major|minor|suggestion",
    "title": "Brief title of the issue",
    "body": "Detailed explanation of the best practice violation",
    "suggestion": "Concrete code suggestion to improve (optional)"
  }}
]

Only include meaningful improvements. Return empty array [] if no issues found.""",
    )

    FRAMEWORK: ClassVar[PromptTemplate] = PromptTemplate(
        category="framework",
        system_prompt="""You are a framework-specific code reviewer. Your task is to identify violations of framework conventions and best practices.

Focus on:
- Framework-specific patterns and anti-patterns
- Proper use of framework features and APIs
- Configuration and setup issues
- Middleware and lifecycle hooks
- Database ORM patterns and query optimization
- Routing and URL patterns
- Template and view rendering
- State management and data flow
- Framework security features
- Performance optimizations specific to the framework

Provide framework-aware recommendations.""",
        user_template="""Review the following code changes for framework-specific issues:

**File:** {file_path}
**Language:** {language}
**Framework:** {framework}

**Code Diff:**
```
{diff_content}
```

**Detected Technologies:**
{tech_stack}

Provide your review as a JSON array of findings:
[
  {{
    "line_start": <line_number>,
    "line_end": <line_number>,
    "severity": "critical|major|minor|suggestion",
    "title": "Brief title of the issue",
    "body": "Detailed explanation of the framework issue",
    "suggestion": "Concrete code suggestion following framework conventions (optional)"
  }}
]

Focus on {framework}-specific issues. Return empty array [] if no issues found.""",
    )

    IAC: ClassVar[PromptTemplate] = PromptTemplate(
        category="iac",
        system_prompt="""You are an Infrastructure as Code (IaC) reviewer. Your task is to identify issues in infrastructure and deployment configurations.

Focus on:
- Security misconfigurations and hardcoded secrets
- Resource access control and permissions
- Network security and firewall rules
- Encryption and data protection
- High availability and disaster recovery
- Resource sizing and cost optimization
- Backup and retention policies
- Monitoring and alerting configuration
- Compliance and governance
- IaC best practices and modularity

Provide infrastructure-specific recommendations.""",
        user_template="""Review the following IaC changes:

**File:** {file_path}
**IaC Tool:** {iac_tool}

**Code Diff:**
```
{diff_content}
```

**Detected Technologies:**
{tech_stack}

Provide your review as a JSON array of findings:
[
  {{
    "line_start": <line_number>,
    "line_end": <line_number>,
    "severity": "critical|major|minor|suggestion",
    "title": "Brief title of the issue",
    "body": "Detailed explanation of the infrastructure issue",
    "suggestion": "Concrete configuration suggestion (optional)"
  }}
]

Focus on infrastructure security and best practices. Return empty array [] if no issues found.""",
    )

    @classmethod
    def get_template(cls, category: str) -> PromptTemplate | None:
        """Get prompt template by category.

        Args:
            category: Review category (security, best_practices, framework, iac)

        Returns:
            PromptTemplate or None if category not found
        """
        templates = {
            "security": cls.SECURITY,
            "best_practices": cls.BEST_PRACTICES,
            "framework": cls.FRAMEWORK,
            "iac": cls.IAC,
        }
        return templates.get(category)

    @classmethod
    def format_tech_stack(
        cls, languages: dict[str, float], frameworks: dict[str, float], iac_tools: list[str]
    ) -> str:
        """Format detected technologies for prompt.

        Args:
            languages: Detected languages with confidence
            frameworks: Detected frameworks with confidence
            iac_tools: Detected IaC tools

        Returns:
            Formatted string of detected technologies
        """
        parts = []

        if languages:
            lang_list = [f"{lang} ({conf:.0%})" for lang, conf in languages.items()]
            parts.append(f"Languages: {', '.join(lang_list)}")

        if frameworks:
            fw_list = [f"{fw} ({conf:.0%})" for fw, conf in frameworks.items()]
            parts.append(f"Frameworks: {', '.join(fw_list)}")

        if iac_tools:
            parts.append(f"IaC Tools: {', '.join(iac_tools)}")

        return "\n".join(parts) if parts else "No specific technologies detected"
