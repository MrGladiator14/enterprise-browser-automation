import asyncio
import os
import sys
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.genai import types
from mcp import StdioServerParameters

# --- Configuration ---
DEFAULT_MODEL = "openai/gpt-4o"
DEFAULT_INSTRUCTION = """
You are a background web automation agent. 
Execute the steps provided faithfully. 
If a step fails, report the error.
"""

# --- Data Structures ---

@dataclass
class Job:
    id: str
    name: str
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
    logs: List[str] = field(default_factory=list)
    task: Optional[asyncio.Task] = None
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))

class WorkflowManager:
    """Manages saved workflows."""
    def __init__(self):
        self.workflows: Dict[str, List[str]] = {
            "demo_insurance": [
                "navigate to 'https://www.royalsundaram.in/MOPIS/Login.jsp'",
                "Enter username 'invictus' and password 'Secret123', click sign in",
                "Click 'Rating Calculator' -> 'New Business' -> 'Private Car'",
                "Enter vehicle MH 02 FR 1294 and click get started",
                "download the generated pdf"
            ],
            "google_check": [
                "navigate to google.com",
                "search for 'Google ADK python'",
                "summarize the first result"
            ]
        }

    def get_workflow(self, name: str) -> List[str]:
        return self.workflows.get(name, [])

    def add_workflow(self, name: str, steps: List[str]):
        self.workflows[name] = steps

    def list_workflows(self) -> List[str]:
        return list(self.workflows.keys())

# --- Core Logic ---

class WebAgent:
    """A self-contained agent instance."""
    def __init__(self, job_id: str, log_callback):
        self.job_id = job_id
        self.log_callback = log_callback  # Function to send logs back to the Job
        self.agent = None
        self.runner = None

    def log(self, message: str):
        """Helper to send logs to the job storage."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        self.log_callback(formatted_msg)

    async def setup(self):
        """Initializes the LLM and MCP tools specific to this agent."""
        self.log("Initializing Agent & Tools...")
        load_dotenv()
        
        # 1. Setup Retry Logic
        retry_config = types.HttpRetryOptions(
            attempts=3, exp_base=2, initial_delay=1, max_delay=10, 
            http_status_codes=[429, 500, 503]
        )

        # 2. Setup Playwright Tool (One per agent/task usually safest)
        server_params = StdioServerParameters(command="npx", args=["@playwright/mcp@latest"])
        playwright_tool = McpToolset(
            connection_params=StdioConnectionParams(server_params=server_params, timeout=60)
        )

        # 3. Setup LLM
        model = LiteLlm(
            model=DEFAULT_MODEL,
            temperature=0.01, # Low temp for deterministic actions
            max_retries=3
        )

        # 4. Create Agent
        self.agent = LlmAgent(
            model=model,
            name=f"agent_{self.job_id}",
            instruction=DEFAULT_INSTRUCTION,
            tools=[playwright_tool],
        )
        self.runner = InMemoryRunner(agent=self.agent, app_name=f"runner_{self.job_id}")
        self.log("Agent Setup Complete.")

    async def run_steps(self, steps: List[str]):
        """Executes the workflow steps."""
        if not self.agent:
            await self.setup()

        self.log(f"Starting execution of {len(steps)} steps.")
        for i, step in enumerate(steps, 1):
            self.log(f"Step {i}: {step}")
            try:
                # We use run_debug but capture output via our log wrapper usually
                # Here we simulate the result capture
                response = await self.runner.run_debug(step, verbose=False)
                self.log(f"Result: {response}")
            except Exception as e:
                self.log(f"❌ Error on step {i}: {str(e)}")
                raise e # Re-raise to mark job as failed
        
        self.log("✅ Workflow completed successfully.")

class JobManager:
    """Orchestrates background jobs."""
    def __init__(self):
        self.jobs: Dict[str, Job] = {}

    def create_job(self, name: str, steps: List[str]) -> str:
        job_id = str(uuid.uuid4())[:8]
        job = Job(id=job_id, name=name)
        self.jobs[job_id] = job
        
        # Create the async task
        task = asyncio.create_task(self._run_job(job, steps))
        job.task = task
        return job_id

    async def _run_job(self, job: Job, steps: List[str]):
        """Internal runner that handles the lifecycle."""
        job.status = "RUNNING"
        
        def job_logger(msg):
            job.logs.append(msg)

        agent = WebAgent(job.id, job_logger)
        
        try:
            await agent.setup()
            await agent.run_steps(steps)
            job.status = "COMPLETED"
        except asyncio.CancelledError:
            job.status = "CANCELLED"
            job_logger("⚠️ Job was cancelled by user.")
        except Exception as e:
            job.status = "FAILED"
            job_logger(f"💥 Critical Failure: {str(e)}")
        finally:
            # Cleanup logic could go here
            pass

    def list_jobs(self):
        return self.jobs.values()

    def get_job(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if job and job.task and not job.task.done():
            job.task.cancel()
            return True
        return False

# --- Interactive CLI ---

async def cli_loop():
    print("==============================================")
    print(" 🚀 Multi-Agent Background Job System CLI")
    print("==============================================")
    print("Commands:")
    print("  start <workflow_name>  -> Run a workflow in background")
    print("  list                   -> List available workflows")
    print("  jobs                   -> Show status of background jobs")
    print("  logs <job_id>          -> View logs for a specific job")
    print("  kill <job_id>          -> Stop a running job")
    print("  create                 -> Create a new workflow")
    print("  exit                   -> Quit")
    print("==============================================\n")

    workflow_mgr = WorkflowManager()
    job_mgr = JobManager()

    while True:
        try:
            # Use asyncio.to_thread for input to not block background tasks
            user_input = await asyncio.to_thread(input, "\n(cli) > ")
            parts = user_input.strip().split()
            if not parts: continue
            
            cmd = parts[0].lower()
            args = parts[1:]

            if cmd in ('exit', 'quit'):
                print("Stopping all jobs and exiting...")
                # Cancel all running jobs before exit
                for job in job_mgr.jobs.values():
                    if job.status == "RUNNING":
                        job.task.cancel()
                break

            elif cmd == 'list':
                print("\nAvailable Workflows:")
                for name in workflow_mgr.list_workflows():
                    print(f" - {name}")

            elif cmd == 'start':
                if not args:
                    print("❌ Usage: start <workflow_name>")
                    continue
                name = args[0]
                steps = workflow_mgr.get_workflow(name)
                if not steps:
                    print(f"❌ Workflow '{name}' not found.")
                else:
                    job_id = job_mgr.create_job(name, steps)
                    print(f"✅ Job started! ID: {job_id} (Type 'jobs' to view status)")

            elif cmd == 'jobs':
                jobs = list(job_mgr.list_jobs())
                if not jobs:
                    print("No jobs found.")
                else:
                    print(f"\n{'ID':<10} {'NAME':<20} {'STATUS':<12} {'STARTED':<10}")
                    print("-" * 55)
                    for job in jobs:
                        print(f"{job.id:<10} {job.name[:18]:<20} {job.status:<12} {job.created_at:<10}")

            elif cmd == 'logs':
                if not args:
                    print("❌ Usage: logs <job_id>")
                    continue
                job = job_mgr.get_job(args[0])
                if not job:
                    print("❌ Job not found.")
                else:
                    print(f"\n--- Logs for Job {job.id} ({job.name}) ---")
                    for log in job.logs:
                        print(log)
                    print("------------------------------------------")

            elif cmd == 'kill':
                if not args:
                    print("❌ Usage: kill <job_id>")
                    continue
                success = job_mgr.cancel_job(args[0])
                if success:
                    print(f"⚠️ Job {args[0]} cancelled.")
                else:
                    print("❌ Could not cancel job (maybe already finished or invalid ID).")

            elif cmd == 'create':
                name = await asyncio.to_thread(input, "Enter workflow name: ")
                print("Enter steps (type 'done' to finish):")
                new_steps = []
                while True:
                    step = await asyncio.to_thread(input, f"Step {len(new_steps)+1}: ")
                    if step.lower() == 'done': break
                    if step.strip(): new_steps.append(step)
                
                if new_steps:
                    workflow_mgr.add_workflow(name, new_steps)
                    print(f"✅ Workflow '{name}' created.")

            else:
                print("❌ Unknown command. Try 'help' or list available commands.")

        except Exception as e:
            print(f"CLI Error: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(cli_loop())
    except KeyboardInterrupt:
        print("\nForce Quit.")
