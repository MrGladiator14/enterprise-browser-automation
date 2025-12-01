# enterprise-browser-automation
## Multi-Agent Background Job System

A Python-based CLI tool for running web automation workflows in the background using Google ADK agents and Playwright MCP tools.

## What it does

This system lets you define multi-step web automation workflows and execute them as background jobs. Each job runs independently with its own agent instance, allowing you to start multiple workflows simultaneously and monitor their progress through a simple command-line interface.

## Key Features

- **Background execution**: Start workflows that run independently while you continue using the CLI
- **Multiple concurrent jobs**: Run several automation tasks simultaneously
- **Real-time monitoring**: Check job status and view detailed logs at any time
- **Workflow management**: Save, reuse, and create custom automation workflows
- **Job control**: Cancel running jobs if needed
- **Isolated agents**: Each job gets its own agent instance to prevent interference

## How Users Benefit

**Save time**: Set up repetitive web tasks once and rerun them with a single command rather than manually clicking through websites.

**Multitask efficiently**: Launch multiple automation jobs in parallel instead of waiting for each to complete sequentially.

**Monitor without blocking**: Start a long-running task and continue working on other things while checking progress periodically.

**Reduce errors**: Automated workflows execute steps consistently without the mistakes that happen during manual data entry or navigation.

**Quick troubleshooting**: Detailed logs for each job make it easy to identify where things went wrong.

**No coding needed for reuse**: Once workflows are created, non-technical users can run them by name without touching code.

## Installation

```bash
pip install python-dotenv google-adk mcp
npm install -g @playwright/mcp
```

Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_key_here
```

## Usage

Run the CLI:
```bash
python script.py
```

### Available Commands

- `list` - Show all saved workflows
- `start <workflow_name>` - Execute a workflow in the background
- `jobs` - Display status of all jobs (PENDING/RUNNING/COMPLETED/FAILED)
- `logs <job_id>` - View detailed execution logs for a specific job
- `kill <job_id>` - Cancel a running job
- `create` - Add a new workflow interactively
- `exit` - Quit and stop all running jobs

### Example Workflows

Two demo workflows are included:

**demo_insurance**: Automates logging into an insurance portal, navigating to a rating calculator, and downloading a PDF.

**google_check**: Opens Google, searches for a term, and summarizes results.

### Creating Custom Workflows

```
(cli) > create
Enter workflow name: my_automation
Enter steps (type 'done' to finish):
Step 1: navigate to example.com
Step 2: click the login button
Step 3: done
✅ Workflow 'my_automation' created.
```

### Running a Workflow

```
(cli) > start demo_insurance
✅ Job started! ID: a3f7b2c1 (Type 'jobs' to view status)

(cli) > jobs
ID         NAME                 STATUS       STARTED   
-------------------------------------------------------
a3f7b2c1   demo_insurance       RUNNING      14:23:15  

(cli) > logs a3f7b2c1
--- Logs for Job a3f7b2c1 (demo_insurance) ---
[14:23:15] Initializing Agent & Tools...
[14:23:18] Agent Setup Complete.
[14:23:18] Starting execution of 5 steps.
[14:23:18] Step 1: navigate to 'https://...'
...
```

## Architecture

- **WorkflowManager**: Stores and retrieves workflow definitions
- **JobManager**: Creates and orchestrates background jobs
- **WebAgent**: Individual agent instance that executes workflow steps
- **Job**: Data structure tracking job state, logs, and async task

Each job runs as an asyncio task with its own WebAgent instance, ensuring complete isolation between concurrent workflows.

## Requirements

- Python 3.8+
- Node.js (for Playwright MCP)
- OpenAI API key (or compatible LiteLLM endpoint)

## Configuration

Modify `DEFAULT_MODEL` and `DEFAULT_INSTRUCTION` at the top of the script to change the LLM model or agent behavior.
