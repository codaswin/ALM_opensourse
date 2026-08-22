from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from app.database import get_session_factory
from app.models.automation import ScheduledPostRecord
from app.safety.approval_gate import execute_pre_approved
from sqlalchemy import select, update

logger = structlog.get_logger(__name__)


async def process_due_posts(user_id: str, now: datetime | None = None, limit: int = 20) -> dict[str, int]:
    now = now or datetime.now(timezone.utc)
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(
            select(ScheduledPostRecord.id)
            .where(
                ScheduledPostRecord.user_id == user_id,
                ScheduledPostRecord.status == "pending",
                ScheduledPostRecord.publish_at <= now,
            )
            .order_by(ScheduledPostRecord.publish_at)
            .limit(limit)
        )
        candidate_ids = list(result.scalars())

    claimed_count = published = failed = 0
    for post_id in candidate_ids:
        async with factory() as db:
            claimed = await db.execute(
                update(ScheduledPostRecord)
                .where(ScheduledPostRecord.id == post_id, ScheduledPostRecord.status == "pending")
                .values(status="publishing", attempts=ScheduledPostRecord.attempts + 1)
            )
            await db.commit()
            if claimed.rowcount != 1:
                continue
            claimed_count += 1
            record = await db.get(ScheduledPostRecord, post_id)
            if record is None:
                continue
            content = record.content

        # Routed through approval_gate.execute_pre_approved(), which goes through the
        # tool registry's execute_tool() — not a direct call to publish_post's
        # implementation — so this path can never drift from the registry's centralized
        # approval/sandboxing enforcement. Pre-approved is legitimate here because
        # schedule_post itself requires_approval=True and this content only reached
        # scheduled_posts after a human already approved it.
        publish_result: dict[str, Any] = await execute_pre_approved("publish_post", {"content": content})
        if publish_result.get("status") == "success":
            async with factory() as db:
                record = await db.get(ScheduledPostRecord, post_id)
                if record is not None:
                    record.status = "published"
                    record.published_at = datetime.now(timezone.utc)
                    record.last_error = None
                    await db.commit()
            published += 1
            logger.info("scheduled_post_published", scheduled_post_id=post_id, result=publish_result)
        else:
            error_message = publish_result.get("error") or f"publish_post returned status {publish_result.get('status')!r}"
            async with factory() as db:
                record = await db.get(ScheduledPostRecord, post_id)
                if record is not None:
                    record.status = "failed"
                    record.last_error = error_message
                    await db.commit()
            failed += 1
            logger.error("scheduled_post_failed", scheduled_post_id=post_id, result=publish_result)

    return {"claimed": claimed_count, "published": published, "failed": failed}
