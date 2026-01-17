import os
import tempfile
import subprocess
import uuid
import json
import asyncio
import logging
from contextlib import asynccontextmanager

import websockets
from fastapi import FastAPI
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestMachine")


WEBSOCKET_SERVER_URL = os.getenv("WS_SERVER_URL", "ws://localhost:8765")
TEST_TIMEOUT_SECONDS = 30
CLASS_FILENAME = "class_to_test.py"
TEST_FILENAME = "test_class.py"



class CodePayload(BaseModel):
    class_code: str = Field(..., description="Kod źródłowy klasy.")
    test_code: str = Field(..., description="Kod testów jednostkowych.")
    mode: str = Field("local", description="Tryb uruchomienia: 'local' lub 'docker'.")


class TestResult(BaseModel):
    status: str
    exit_code: int
    logs: str = ""



def save_temp_files(tmpdir: str, payload: CodePayload):
    try:
        with open(os.path.join(tmpdir, CLASS_FILENAME), "w", encoding="utf-8") as f:
            f.write(payload.class_code)
        with open(os.path.join(tmpdir, TEST_FILENAME), "w", encoding="utf-8") as f:
            f.write(payload.test_code)
    except Exception as e:
        logger.error(f"Błąd zapisu plików: {e}")
        raise


def _execute_local_tests(payload: CodePayload) -> TestResult:
    with tempfile.TemporaryDirectory() as tmpdir:
        save_temp_files(tmpdir, payload)
        try:
            result = subprocess.run(
                ['pytest', TEST_FILENAME],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=TEST_TIMEOUT_SECONDS
            )
            status = "SUCCESS" if result.returncode == 0 else "FAILURE"
            return TestResult(
                status=status,
                exit_code=result.returncode,
                logs=f"{result.stdout}\n{result.stderr}",
            )
        except subprocess.TimeoutExpired:
            return TestResult(status="FAILURE", exit_code=999, logs="Timeout: Przekroczono czas wykonania.")
        except Exception as e:
            return TestResult(status="ERROR", exit_code=500, logs=str(e))


def _execute_docker_tests(payload: CodePayload) -> TestResult:
    container_name = f"test_runner_{uuid.uuid4().hex[:8]}"
    image_tag = f"img_{container_name}"

    with tempfile.TemporaryDirectory() as tmpdir:
        save_temp_files(tmpdir, payload)

        dockerfile_content = """
FROM python:3.11-slim
WORKDIR /app/code
RUN pip install --no-cache-dir pytest
RUN useradd --create-home appuser && chown -R appuser /app/code
USER appuser
"""
        with open(os.path.join(tmpdir, "Dockerfile"), "w") as f:
            f.write(dockerfile_content)

        try:
            subprocess.run(["docker", "build", "-t", image_tag, tmpdir], check=True, capture_output=True)

            command = [
                "docker", "run", "--name", container_name, "--rm",
                "--network", "none",
                "-v", f"{tmpdir}:/app/code",
                image_tag,
                "python", "-m", "pytest", TEST_FILENAME
            ]

            result = subprocess.run(command, capture_output=True, text=True, timeout=TEST_TIMEOUT_SECONDS)
            status = "SUCCESS" if result.returncode == 0 else "FAILURE"

            return TestResult(
                status=status,
                exit_code=result.returncode,
                logs=f"{result.stdout}\n{result.stderr}",
            )

        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "stop", "-t", "0", container_name], capture_output=True)
            return TestResult(status="FAILURE", exit_code=999, logs="Błąd: Wykryto nieskończoną pętlę (Timeout).")
        except Exception as e:
            return TestResult(status="ERROR", exit_code=500, logs=str(e))
        finally:
            subprocess.run(["docker", "stop", "-t", "0", container_name], capture_output=True)
            subprocess.run(["docker", "rmi", image_tag], capture_output=True)



async def websocket_worker():
    while True:
        try:
            logger.info(f"Łączenie z {WEBSOCKET_SERVER_URL}...")
            async with websockets.connect(WEBSOCKET_SERVER_URL) as websocket:

                init_message = {"role": "TestMachine"}
                await websocket.send(json.dumps(init_message))
                logger.info("Połączono. Wysłano rolę TestMachine. Oczekiwanie na zadania...")

                async for message in websocket:
                    try:
                        data = json.loads(message)
                        logger.info("Otrzymano zadanie.")

                        payload = CodePayload(**data)

                        loop = asyncio.get_running_loop()

                        if payload.mode == "docker":
                            result = await loop.run_in_executor(None, _execute_docker_tests, payload)
                        else:
                            result = await loop.run_in_executor(None, _execute_local_tests, payload)

                        # Odesłanie wyniku
                        await websocket.send(result.model_dump_json())
                        logger.info(f"Wysłano wynik dla zadania (Status: {result.status})")

                    except json.JSONDecodeError:
                        logger.error("Otrzymano niepoprawny JSON.")
                    except Exception as e:
                        logger.error(f"Błąd przetwarzania wiadomości: {e}")
                        error_res = TestResult(status="ERROR", exit_code=500, logs=f"Internal Error: {str(e)}")
                        await websocket.send(error_res.model_dump_json())

        except (websockets.ConnectionClosed, ConnectionRefusedError) as e:
            logger.warning(f"Połączenie utracone: {e}. Ponawianie za 5 sekund...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd w pętli WebSocket: {e}")
            await asyncio.sleep(5)



@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(websocket_worker())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="AI Team Test Machine Runner (WebSocket Client)",
    version="2.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    return {"status": "alive", "mode": "websocket-client"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)