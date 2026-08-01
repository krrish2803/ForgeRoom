from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Iterator
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from motor.motor_asyncio import AsyncIOMotorDatabase

class MongoDBSaver(BaseCheckpointSaver):
    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__()
        self.db = db
        self.checkpoints = db["room_checkpoints"]
        self.writes = db["room_checkpoint_writes"]

    # ==========================================
    # SYNCHRONOUS STUB METHODS (NOT USED IN ASYNC APP)
    # ==========================================
    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        raise NotImplementedError("Use async aget_tuple instead")

    def put(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: dict) -> dict:
        raise NotImplementedError("Use async aput instead")

    def put_writes(self, config: RunnableConfig, writes: list, task_id: str, task_path: str = "") -> None:
        raise NotImplementedError("Use async aput_writes instead")

    def list(self, config: Optional[RunnableConfig], *, filter: Optional[dict] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> Iterator[CheckpointTuple]:
        raise NotImplementedError("Use async alist instead")

    # ==========================================
    # ASYNCHRONOUS PERSISTENCE METHODS
    # ==========================================
    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"].get("checkpoint_id")
        
        query = {"thread_id": thread_id}
        if checkpoint_id:
            query["checkpoint_id"] = checkpoint_id
            doc = await self.checkpoints.find_one(query)
        else:
            # Fetch latest checkpoint
            doc = await self.checkpoints.find_one(query, sort=[("checkpoint_id", -1)])
            
        if not doc:
            return None
            
        checkpoint = self.serde.loads(doc["checkpoint"])
        metadata = self.serde.loads(doc["metadata"])
        
        # Load pending writes
        write_cursor = self.writes.find({
            "thread_id": thread_id,
            "checkpoint_id": doc["checkpoint_id"]
        })
        write_docs = await write_cursor.to_list(length=100)
        
        pending_writes = [
            (w["task_id"], w["channel"], self.serde.loads(w["value"]))
            for w in write_docs
        ]
        
        return CheckpointTuple(
            config=RunnableConfig(
                configurable={
                    "thread_id": thread_id,
                    "checkpoint_id": doc["checkpoint_id"]
                }
            ),
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config=RunnableConfig(
                configurable={
                    "thread_id": thread_id,
                    "checkpoint_id": doc.get("parent_checkpoint_id")
                }
            ) if doc.get("parent_checkpoint_id") else None,
            pending_writes=pending_writes
        )

    async def aput(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: dict) -> dict:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = checkpoint["id"]
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")
        
        doc = {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "parent_checkpoint_id": parent_checkpoint_id,
            "checkpoint": self.serde.dumps(checkpoint),
            "metadata": self.serde.dumps(metadata)
        }
        
        await self.checkpoints.update_one(
            {"thread_id": thread_id, "checkpoint_id": checkpoint_id},
            {"$set": doc},
            upsert=True
        )
        return {"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id}}

    async def aput_writes(self, config: RunnableConfig, writes: List[Tuple[str, Any]], task_id: str, task_path: str = "") -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_id = config["configurable"]["checkpoint_id"]
        
        write_docs = []
        for channel, value in writes:
            write_docs.append({
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "task_id": task_id,
                "task_path": task_path,
                "channel": channel,
                "value": self.serde.dumps(value)
            })
            
        if write_docs:
            await self.writes.insert_many(write_docs)

    async def alist(self, config: Optional[RunnableConfig], *, filter: Optional[dict] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> AsyncIterator[CheckpointTuple]:
        query = {}
        if config:
            query["thread_id"] = config["configurable"]["thread_id"]
            
        if filter:
            for k, v in filter.items():
                query[k] = v
                
        if before:
            query["checkpoint_id"] = {"$lt": before["configurable"]["checkpoint_id"]}
            
        cursor = self.checkpoints.find(query, sort=[("checkpoint_id", -1)])
        if limit:
            cursor = cursor.limit(limit)
            
        async for doc in cursor:
            checkpoint = self.serde.loads(doc["checkpoint"])
            metadata = self.serde.loads(doc["metadata"])
            
            write_cursor = self.writes.find({
                "thread_id": doc["thread_id"],
                "checkpoint_id": doc["checkpoint_id"]
            })
            write_docs = await write_cursor.to_list(length=100)
            
            pending_writes = [
                (w["task_id"], w["channel"], self.serde.loads(w["value"]))
                for w in write_docs
            ]
            
            yield CheckpointTuple(
                config=RunnableConfig(
                    configurable={
                        "thread_id": doc["thread_id"],
                        "checkpoint_id": doc["checkpoint_id"]
                    }
                ),
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=RunnableConfig(
                    configurable={
                        "thread_id": doc["thread_id"],
                        "checkpoint_id": doc.get("parent_checkpoint_id")
                    }
                ) if doc.get("parent_checkpoint_id") else None,
                pending_writes=pending_writes
            )
