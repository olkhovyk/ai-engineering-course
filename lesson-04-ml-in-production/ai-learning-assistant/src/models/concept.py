from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class Concept(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str
    explanation: str = ""
    level: int = 0  # depth from root (0 = main topic)
    is_expanded: bool = False


class ConceptEdge(BaseModel):
    source: str  # parent concept id
    target: str  # prerequisite concept id
    label: str = "requires"


class KnowledgeGraph(BaseModel):
    concepts: dict[str, Concept] = {}
    edges: list[ConceptEdge] = []
    root_id: str = ""

    def add_concept(self, concept: Concept) -> None:
        self.concepts[concept.id] = concept

    def add_edge(self, source_id: str, target_id: str, label: str = "requires") -> None:
        self.edges.append(ConceptEdge(source=source_id, target=target_id, label=label))

    def get_unexpanded_concepts(self, max_level: int) -> list[Concept]:
        return [
            c for c in self.concepts.values()
            if not c.is_expanded and c.level < max_level
        ]


class DecompositionResult(BaseModel):
    """LLM output schema for concept decomposition."""
    prerequisites: list[str] = Field(
        description="List of prerequisite concept names needed to understand the parent concept"
    )


class ExplanationResult(BaseModel):
    """LLM output schema for concept explanation."""
    explanation: str = Field(
        description="Clear, concise explanation of the concept (2-4 sentences)"
    )
