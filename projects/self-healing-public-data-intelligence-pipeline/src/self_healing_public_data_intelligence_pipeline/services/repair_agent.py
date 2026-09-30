from typing import Dict
from uuid import UUID

from bs4 import BeautifulSoup

from self_healing_public_data_intelligence_pipeline.adapters.repositories import InMemoryRepository
from self_healing_public_data_intelligence_pipeline.domain.models import ExtractionRecipe, RepairProposal
from self_healing_public_data_intelligence_pipeline.services.pipeline_service import TYPE_MAP, extract_records


class RepairAgentService:
    """Deterministic locator repair with mandatory replay before activation."""

    def __init__(self, repo: InMemoryRepository):
        self.repo = repo

    def propose_repair(self, failure_id: UUID) -> RepairProposal:
        failure = self.repo.failures.get(failure_id)
        if not failure:
            raise ValueError("Failure not found")
        run = self.repo.runs.get(failure.crawl_run_id)
        if not run:
            raise ValueError("Run not found")
        original_recipe = self.repo.get_recipe(run.recipe_id)
        if not original_recipe:
            raise ValueError("Original recipe not found")
        field = failure.field or "value"
        candidate, rationale, confidence = self._candidate_for_field(run.html_snapshot, field)
        proposed_selectors = dict(original_recipe.selectors)
        proposed_selectors[field] = candidate
        proposal = RepairProposal(
            source_id=run.source_id,
            original_recipe_id=original_recipe.id,
            proposed_selectors=proposed_selectors,
            target_field=field,
            rationale=rationale,
            confidence_score=confidence,
        )
        self.repo.save_proposal(proposal)
        return proposal

    @staticmethod
    def _candidate_for_field(html: str, field: str) -> tuple[str, str, float]:
        soup = BeautifulSoup(html, "html.parser")
        candidates = [
            (f"[data-field='{field}']", "stable data-field attribute", 0.95),
            (f"[aria-label='{field}']", "accessible aria-label", 0.9),
            (f"#{field}", "unique semantic id", 0.85),
            (f".{field}", "semantic class", 0.7),
        ]
        for selector, rationale, confidence in candidates:
            if soup.select_one(selector):
                return selector, f"Selected {rationale} found in the captured snapshot", confidence
        raise ValueError(f"No explainable locator candidate found for field: {field}")

    def replay_proposal(self, proposal_id: UUID, test_html: str) -> RepairProposal:
        proposal = self.repo.proposals.get(proposal_id)
        if not proposal:
            raise ValueError("Proposal not found")
        if not test_html.strip():
            raise ValueError("Replay HTML cannot be empty")
        records = extract_records(test_html, proposal.proposed_selectors)
        required_fields = [key for key in proposal.proposed_selectors if not key.startswith("_")]
        matches: Dict[str, int] = {
            field: sum(1 for record in records if record.get(field) not in (None, "")) for field in required_fields
        }
        source = self.repo.get_source(proposal.source_id)
        if not source:
            raise ValueError("Source not found")
        for field, type_name in source.expected_schema.items():
            converter = TYPE_MAP[type_name]
            valid_count = 0
            for record in records:
                try:
                    converter(record[field])
                    valid_count += 1
                except (KeyError, TypeError, ValueError):
                    pass
            matches[field] = min(matches.get(field, valid_count), valid_count)
        proposal.replay_matches = matches
        proposal.replay_passed = bool(records) and all(count == len(records) for count in matches.values())
        self.repo.save_proposal(proposal)
        if not proposal.replay_passed:
            missing = [field for field, count in matches.items() if count != len(records)]
            raise ValueError(f"Replay failed; selectors did not cover: {', '.join(missing)}")
        return proposal

    def activate_proposal(self, proposal_id: UUID, approved: bool) -> ExtractionRecipe:
        proposal = self.repo.proposals.get(proposal_id)
        if not proposal:
            raise ValueError("Proposal not found")
        if not approved:
            raise ValueError("Human approval is required")
        if not proposal.replay_passed:
            raise ValueError("Proposal must pass replay before activation")
        original_recipe = self.repo.get_recipe(proposal.original_recipe_id)
        if not original_recipe or not original_recipe.is_active:
            raise ValueError("Original recipe is no longer active")
        original_recipe.is_active = False
        self.repo.save_recipe(original_recipe)
        proposal.approved = True
        self.repo.save_proposal(proposal)
        new_recipe = ExtractionRecipe(
            source_id=proposal.source_id,
            version=original_recipe.version + 1,
            selectors=proposal.proposed_selectors,
            is_active=True,
        )
        self.repo.save_recipe(new_recipe)
        return new_recipe

    def test_and_activate_proposal(self, proposal_id: UUID, test_html: str) -> ExtractionRecipe:
        self.replay_proposal(proposal_id, test_html)
        return self.activate_proposal(proposal_id, approved=True)
