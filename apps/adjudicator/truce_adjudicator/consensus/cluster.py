"""Advanced clustering and consensus analysis"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..models import ConsensusCluster, ConsensusStatement, Vote, VoteType
from .vote import create_vote_matrix


def analyze_statement_clusters(
    statements: List[ConsensusStatement], votes: List[Vote]
) -> Tuple[
    List[ConsensusStatement], List[ConsensusStatement], List[ConsensusStatement]
]:
    """Analyze and categorize statements into consensus, divisive, and uncertain"""

    consensus_statements = []
    divisive_statements = []
    uncertain_statements = []

    for statement in statements:
        total_votes = statement.agree_count + statement.disagree_count

        if total_votes < 3:  # Minimum votes for classification
            uncertain_statements.append(statement)
        elif statement.agree_rate >= 0.75:  # Strong consensus
            consensus_statements.append(statement)
        elif 0.25 <= statement.agree_rate <= 0.75:  # Divisive
            divisive_statements.append(statement)
        else:  # Low agreement (also consensus, but negative)
            consensus_statements.append(statement)

    # Sort each category
    consensus_statements.sort(key=lambda s: s.agree_rate, reverse=True)
    divisive_statements.sort(key=lambda s: abs(0.5 - s.agree_rate))
    uncertain_statements.sort(
        key=lambda s: s.agree_count + s.disagree_count, reverse=True
    )

    return consensus_statements, divisive_statements, uncertain_statements


def find_opinion_bridges(
    statements: List[ConsensusStatement],
    votes: List[Vote],
    clusters: List[ConsensusCluster],
) -> List[ConsensusStatement]:
    """Find statements that bridge different opinion clusters"""

    if len(clusters) < 2:
        return []

    bridge_statements = []

    # Group votes by cluster (approximated by user patterns)
    for statement in statements:
        statement_votes = [v for v in votes if v.statement_id == statement.id]

        if len(statement_votes) < 5:  # Need sufficient votes
            continue

        # Check if statement has reasonable agreement across different voting patterns
        agree_votes = [v for v in statement_votes if v.vote == VoteType.AGREE]

        if len(agree_votes) >= 0.4 * len(statement_votes) and len(
            agree_votes
        ) <= 0.8 * len(statement_votes):
            # This statement has moderate agreement - potential bridge
            bridge_statements.append(statement)

    return sorted(bridge_statements, key=lambda s: abs(0.6 - s.agree_rate))[:5]


def calculate_consensus_quality_metrics(
    statements: List[ConsensusStatement], votes: List[Vote]
) -> Dict[str, float]:
    """Calculate quality metrics for consensus process"""

    metrics = {}

    if not statements or not votes:
        return {
            "participation_rate": 0.0,
            "consensus_ratio": 0.0,
            "polarization_score": 0.0,
            "statement_coverage": 0.0,
        }

    # Participation rate - how many statements does average user vote on
    user_votes = defaultdict(int)
    for vote in votes:
        user_key = vote.user_id or vote.session_id
        user_votes[user_key] += 1

    avg_votes_per_user = np.mean(list(user_votes.values())) if user_votes else 0
    metrics["participation_rate"] = min(avg_votes_per_user / len(statements), 1.0)

    # Consensus ratio - proportion of statements with clear consensus
    consensus_statements = [
        s for s in statements if s.agree_rate >= 0.7 or s.agree_rate <= 0.3
    ]
    metrics["consensus_ratio"] = (
        len(consensus_statements) / len(statements) if statements else 0
    )

    # Polarization score - how divided the community is
    polarization_scores = []
    for statement in statements:
        if statement.agree_count + statement.disagree_count > 0:
            polarization_scores.append(abs(0.5 - statement.agree_rate) * 2)

    metrics["polarization_score"] = (
        1 - np.mean(polarization_scores) if polarization_scores else 0
    )

    # Statement coverage - how well distributed votes are across statements
    statement_vote_counts = [
        statement.agree_count + statement.disagree_count for statement in statements
    ]
    if statement_vote_counts and max(statement_vote_counts) > 0:
        coverage_std = np.std(statement_vote_counts) / np.mean(statement_vote_counts)
        metrics["statement_coverage"] = max(0, 1 - coverage_std)
    else:
        metrics["statement_coverage"] = 0

    return metrics


def suggest_new_statements(
    existing_statements: List[ConsensusStatement], votes: List[Vote], topic: str
) -> List[str]:
    """Suggest new statements based on gaps in current consensus"""

    suggestions = []

    # Analyze current statement patterns
    consensus_statements, divisive_statements, uncertain_statements = (
        analyze_statement_clusters(existing_statements, votes)
    )

    # Template suggestions based on topic
    if "crime" in topic.lower() and "canada" in topic.lower():
        base_suggestions = [
            "Crime statistics should be interpreted with caution due to under-reporting",
            "Different types of crime have different reporting rates to police",
            "Provincial crime trends may differ significantly from national trends",
            "Crime prevention programs should be evidence-based",
            "Both crime victims and community safety deserve priority",
            "Social factors contribute significantly to crime rates",
            "Rehabilitation and punishment both have roles in justice",
            "Crime data should be publicly accessible and transparent",
        ]

        # Filter out suggestions that are too similar to existing statements
        for suggestion in base_suggestions:
            is_similar = False
            for existing in existing_statements:
                # Simple similarity check - could be improved with NLP
                common_words = set(suggestion.lower().split()) & set(
                    existing.text.lower().split()
                )
                if len(common_words) >= 3:
                    is_similar = True
                    break

            if not is_similar:
                suggestions.append(suggestion)

    return suggestions[:3]  # Return top 3 suggestions


def detect_voting_patterns(votes: List[Vote]) -> Dict[str, any]:
    """Detect interesting patterns in voting behavior"""

    patterns = {
        "rapid_voters": [],
        "consistent_voters": [],
        "swing_voters": [],
        "engagement_trend": "stable",
    }

    if not votes:
        return patterns

    # Group votes by user
    user_votes = defaultdict(list)
    for vote in votes:
        user_key = vote.user_id or vote.session_id
        user_votes[user_key].append(vote)

    # Analyze patterns
    for user_key, user_vote_list in user_votes.items():
        if len(user_vote_list) < 3:
            continue

        # Sort votes by timestamp
        user_vote_list.sort(key=lambda v: v.created_at)

        # Check for rapid voting (multiple votes in short time)
        time_diffs = []
        for i in range(1, len(user_vote_list)):
            diff = (
                user_vote_list[i].created_at - user_vote_list[i - 1].created_at
            ).total_seconds()
            time_diffs.append(diff)

        if (
            time_diffs and np.mean(time_diffs) < 30
        ):  # Average < 30 seconds between votes
            patterns["rapid_voters"].append(user_key)

        # Check for consistency (mostly agree or mostly disagree)
        agree_count = sum(1 for v in user_vote_list if v.vote == VoteType.AGREE)
        disagree_count = sum(1 for v in user_vote_list if v.vote == VoteType.DISAGREE)
        total_votes = agree_count + disagree_count

        if total_votes > 0:
            consistency_ratio = max(agree_count, disagree_count) / total_votes
            if consistency_ratio >= 0.8:
                patterns["consistent_voters"].append(user_key)
            elif 0.3 <= consistency_ratio <= 0.7:
                patterns["swing_voters"].append(user_key)

    return patterns
