from collections import Counter, defaultdict
from statistics import mean, median
from typing import Dict, List, Tuple

from process_mining_workflow_automation_analyzer.domain.models import (
    AnalysisConfig, CaseMetric, Event, ResourceMetric, SLABreach, Transition, Variant,
)


def percentile(values: List[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


class ProcessEngine:
    @classmethod
    def analyze(cls, events: List[Event], config: AnalysisConfig | None = None) -> Dict[str, object]:
        config = config or AnalysisConfig()
        indexed = list(enumerate(events))
        sorted_events = sorted(indexed, key=lambda item: (item[1].case_id, item[1].timestamp, item[1].event_id or "", item[0]))
        cases: Dict[str, List[Event]] = defaultdict(list)
        for _, event in sorted_events:
            cases[event.case_id].append(event)

        variants_counter: Counter[Tuple[str, ...]] = Counter()
        transition_data: Dict[Tuple[str, str], Dict[str, object]] = defaultdict(
            lambda: {"durations": [], "cases": set()}
        )
        rework_counter: Counter[str] = Counter()
        case_metrics: List[CaseMetric] = []
        sla_breaches: List[SLABreach] = []
        resource_events: Counter[str] = Counter()
        resource_cases: Dict[str, set] = defaultdict(set)
        handoffs: Counter[str] = Counter()

        for case_id in sorted(cases):
            case_events = cases[case_id]
            sequence = tuple(event.activity for event in case_events)
            variants_counter[sequence] += 1
            activity_counts = Counter(sequence)
            rework_count = sum(max(0, count - 1) for count in activity_counts.values())
            rework_counter.update({activity: count - 1 for activity, count in activity_counts.items() if count > 1})
            duration = (case_events[-1].timestamp - case_events[0].timestamp).total_seconds() if len(case_events) > 1 else 0.0
            case_metrics.append(CaseMetric(
                case_id=case_id, event_count=len(case_events), start_activity=case_events[0].activity,
                end_activity=case_events[-1].activity, duration_seconds=duration, rework_count=rework_count,
            ))
            if duration > config.sla_seconds:
                sla_breaches.append(SLABreach(
                    case_id=case_id, duration_seconds=duration, sla_seconds=config.sla_seconds,
                    exceeded_by_seconds=duration - config.sla_seconds,
                ))
            for event in case_events:
                if event.resource:
                    resource_events[event.resource] += 1
                    resource_cases[event.resource].add(case_id)
            for current, following in zip(case_events, case_events[1:]):
                elapsed = max(0.0, (following.timestamp - current.timestamp).total_seconds())
                key = (current.activity, following.activity)
                transition_data[key]["durations"].append(elapsed)
                transition_data[key]["cases"].add(case_id)
                if current.resource and following.resource and current.resource != following.resource:
                    handoffs[following.resource] += 1

        total_cases = len(cases)
        variants = [
            Variant(id=f"V{index}", activities_sequence=list(sequence), frequency=frequency,
                    coverage=round(frequency / total_cases, 4) if total_cases else 0.0)
            for index, (sequence, frequency) in enumerate(
                sorted(variants_counter.items(), key=lambda item: (-item[1], item[0])), 1
            )
        ]
        transitions: List[Transition] = []
        for (source, target), raw in sorted(transition_data.items()):
            durations = raw["durations"]
            transitions.append(Transition(
                source=source, target=target, frequency=len(durations),
                case_coverage=round(len(raw["cases"]) / total_cases, 4) if total_cases else 0.0,
                avg_duration_seconds=mean(durations), median_duration_seconds=median(durations),
                p95_duration_seconds=percentile(durations, 0.95),
            ))
        bottlenecks = [
            transition for transition in transitions
            if transition.frequency >= config.bottleneck_min_frequency
            and transition.avg_duration_seconds > config.bottleneck_seconds
        ]
        bottlenecks.sort(key=lambda item: (-item.avg_duration_seconds, -item.frequency, item.source, item.target))
        resources = [
            ResourceMetric(resource=name, event_count=count, case_count=len(resource_cases[name]), handoffs_in=handoffs[name])
            for name, count in sorted(resource_events.items(), key=lambda item: (-item[1], item[0]))
        ]
        return {
            "variants": variants,
            "transitions": transitions,
            "bottlenecks": bottlenecks,
            "rework_loops": sorted(rework_counter),
            "case_metrics": case_metrics,
            "sla_breaches": sorted(sla_breaches, key=lambda item: (-item.exceeded_by_seconds, item.case_id)),
            "resources": resources,
        }

    @classmethod
    def discover(cls, events: List[Event]) -> Tuple[List[Variant], List[Transition], List[Transition], List[str]]:
        analysis = cls.analyze(events)
        return (
            analysis["variants"], analysis["transitions"],
            analysis["bottlenecks"], analysis["rework_loops"],
        )
