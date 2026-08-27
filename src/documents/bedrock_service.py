"""Optional Bedrock generation and Knowledge Base retrieval adapter."""

from __future__ import annotations

import boto3


class BedrockService:
    def __init__(self, model_id: str, region: str = "ap-south-1", knowledge_base_id: str = ""):
        if not model_id:
            raise ValueError("AWS_BEDROCK_MODEL_ID is required in AWS mode")
        self.model_id = model_id
        self.knowledge_base_id = knowledge_base_id
        self.runtime = boto3.client("bedrock-runtime", region_name=region)
        self.agent_runtime = boto3.client("bedrock-agent-runtime", region_name=region)

    def retrieve(self, question: str, limit: int = 4) -> list[dict]:
        if not self.knowledge_base_id:
            raise ValueError("AWS_BEDROCK_KNOWLEDGE_BASE_ID is required for managed retrieval")
        result = self.agent_runtime.retrieve(
            knowledgeBaseId=self.knowledge_base_id,
            retrievalQuery={"text": question},
            retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": limit}},
        )
        return result.get("retrievalResults", [])

    def generate_grounded(self, question: str, passages: list[str]) -> str:
        prompt = (
            "Answer only from the passages. If absent, say you do not know. Cite source labels.\n"
            f"Question: {question}\nPassages:\n" + "\n".join(passages)
        )
        response = self.runtime.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"temperature": 0, "maxTokens": 500},
        )
        return response["output"]["message"]["content"][0]["text"]
