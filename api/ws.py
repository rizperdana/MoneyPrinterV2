"""WebSocket endpoint for real-time job progress streaming."""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.jobs import job_manager

router = APIRouter()


@router.websocket("/ws/jobs/{job_id}")
async def job_stream(websocket: WebSocket, job_id: str):
    """Stream job events over WebSocket."""
    await websocket.accept()

    job = job_manager.get(job_id)
    if not job:
        await websocket.close(code=4004)
        return

    try:
        while True:
            try:
                event = await asyncio.wait_for(job.events.get(), timeout=60)
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
                continue

            await websocket.send_text(json.dumps(event))

            if event.get("type") in ("done", "error", "cancelled"):
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
