from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import time
from typing import Generator, Callable, Dict
import uuid
from src.rule_runner import RuleRunner

app = FastAPI()
templates = Jinja2Templates(directory="templates")

task_results = {}

# In-memory result store
task_results: Dict[str, str] = {}


def run_task(callback: Callable[[str], None]) -> str:
    for i in range(5):
        callback(f"Step {i+1} done<br/>\n")
        time.sleep(1)
    return "This is the final result from task_runner"


def run_and_stream(task_id: str) -> Generator[bytes, None, None]:
    def stream() -> Generator[bytes, None, None]:
        # This will yield output messages to the client
        output_messages: list[str] = []

        def callback(msg: str) -> None:
            output_messages.append(msg)

        # Run the task (collects messages into output_messages)
        runner = RuleRunner()
        result = runner.do_work(callback)

        # Stream collected output
        for msg in output_messages:
            yield msg.encode("utf-8")

        # Save final result
        task_results[task_id] = result
        print(result)

        # Trigger redirect to results page
        yield f'<script>window.location="/results/{task_id}";</script>'.encode("utf-8")

    return stream()


@app.get("/", response_class=HTMLResponse)
async def start() -> StreamingResponse:
    task_id = str(uuid.uuid4())
    return StreamingResponse(run_and_stream(task_id), media_type="text/html")


@app.get("/results/{task_id}", response_class=HTMLResponse)
async def results(request: Request, task_id: str) -> HTMLResponse:
    result: str = task_results.get(task_id, "Result not found")
    return templates.TemplateResponse("results.html", {"request": request, "data": result})
