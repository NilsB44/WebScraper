# ROADMAP.md

## Modernization Roadmap: WebScraper

This roadmap outlines the steps to bring the WebScraper repository to State-of-the-Art (2025) standards, focusing on agentic readiness and parallel workflows.

---

### PHASE 1: Enable Parallel Agents
**Goal:** Prepare the repository for simultaneous multi-agent development using Worktrunk.

#### Task 1.1: Install Worktrunk and Configure Git Ignores
- **Task:** Install `worktrunk` CLI and update `.gitignore`.
- **Why:** Allows multiple AI agents to work on different features simultaneously in isolated worktrees without git lock conflicts or affecting the main branch's state.
- **Prompt:**
  ```text
  Install worktrunk using 'brew install max-sixty/worktrunk/worktrunk' (or 'cargo install worktrunk'). 
  Then, update the .gitignore file in the WebScraper repository to include '../WebScraper.*' and '*.worktree' to ensure sibling worktree directories are ignored.
  ```

#### Task 1.2: Create AGENT.md for Isolated Testing
- **Task:** Create an `AGENT.md` file with instructions for agents.
- **Why:** Provides clear guidance for AI agents on how to run tests and manage dependencies within their isolated worktrees.
- **Prompt:**
  ```text
  Create an 'AGENT.md' file in the root directory. This file should instruct agents to:
  1. Use 'uv sync' to manage dependencies in their worktree.
  2. Run tests using 'uv run pytest' ensuring they don't interfere with other worktrees.
  3. Use 'uv run ruff check .' and 'uv run mypy .' before submitting changes.
  ```

---

### PHASE 2: Standardize Dependency Management and Typing
**Goal:** Ensure fast, reliable builds and strict code quality.

#### Task 2.1: Enforce strict `uv` usage
- **Task:** Remove any legacy dependency files and consolidate to `uv`.
- **Why:** `uv` is significantly faster and more reliable than poetry or pip.
- **Prompt:**
  ```text
  Audit the repository for any 'requirements.txt' or 'requirements-dev.txt' files. 
  Ensure all dependencies are correctly listed in 'pyproject.toml' and remove the legacy requirements files. 
  Update the README to strictly use 'uv sync' for setup.
  ```

#### Task 2.2: Harden Strict Typing with `mypy`
- **Task:** Resolve any remaining `mypy` errors and ensure strict mode is fully operational.
- **Why:** Prevents runtime type errors and improves agentic code understanding.
- **Prompt:**
  ```text
  Run 'uv run mypy .' and fix all reported type errors. 
  Ensure that '[tool.mypy]' in 'pyproject.toml' has 'strict = true' and 'disallow_untyped_defs = true'.
  ```

---

### PHASE 3: Advanced CI/CD and Security
**Goal:** Automate quality gates and protect the codebase.

#### Task 3.1: Enhance GitHub Actions
- **Task:** Add security scanning (Bandit/CodeQL) and automated formatting checks to the CI pipeline.
- **Why:** Ensures that every PR from an agent or human meets security and style standards automatically.
- **Prompt:**
  ```text
  Update '.github/workflows/' to include a 'lint-and-test.yml' that runs 'ruff check', 'ruff format --check', 'mypy', and 'pytest' on every push and pull request. 
  Add a step for security scanning using 'bandit' or 'CodeQL'.
  ```
