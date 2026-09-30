from typing import List, Dict, Optional
from uuid import UUID
from self_healing_public_data_intelligence_pipeline.domain.models import Source, CrawlRun, ExtractionRecipe, Record, ValidationFailure, RepairProposal

class InMemoryRepository:
    def __init__(self):
        self.sources: Dict[UUID, Source] = {}
        self.recipes: Dict[UUID, ExtractionRecipe] = {}
        self.runs: Dict[UUID, CrawlRun] = {}
        self.records: Dict[UUID, Record] = {}
        self.failures: Dict[UUID, ValidationFailure] = {}
        self.proposals: Dict[UUID, RepairProposal] = {}

    def save_source(self, source: Source):
        self.sources[source.id] = source
    
    def get_source(self, source_id: UUID) -> Optional[Source]:
        return self.sources.get(source_id)

    def save_recipe(self, recipe: ExtractionRecipe):
        self.recipes[recipe.id] = recipe

    def get_recipe(self, recipe_id: UUID) -> Optional[ExtractionRecipe]:
        return self.recipes.get(recipe_id)

    def get_active_recipe_for_source(self, source_id: UUID) -> Optional[ExtractionRecipe]:
        for r in self.recipes.values():
            if r.source_id == source_id and r.is_active:
                return r
        return None

    def save_run(self, run: CrawlRun):
        self.runs[run.id] = run

    def get_runs_for_source(self, source_id: UUID) -> List[CrawlRun]:
        return sorted(
            [run for run in self.runs.values() if run.source_id == source_id],
            key=lambda item: item.timestamp,
        )

    def save_record(self, record: Record):
        self.records[record.id] = record
        
    def get_valid_records(self) -> List[Record]:
        return [r for r in self.records.values() if r.is_valid and not r.quarantined]

    def save_failure(self, failure: ValidationFailure):
        self.failures[failure.id] = failure

    def save_proposal(self, proposal: RepairProposal):
        self.proposals[proposal.id] = proposal

    def get_recipes_for_source(self, source_id: UUID) -> List[ExtractionRecipe]:
        return sorted([recipe for recipe in self.recipes.values() if recipe.source_id == source_id], key=lambda item: item.version)

    def reset(self):
        self.__init__()
