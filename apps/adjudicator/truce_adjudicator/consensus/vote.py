"""Voting and consensus aggregation logic"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import numpy as np

from ..models import ConsensusCluster, ConsensusStatement, Vote, VoteType


def aggregate_votes(statements: List[ConsensusStatement], votes: List[Vote]) -> None:
    """Aggregate vote counts and rates for statements"""

    # Group votes by statement
    votes_by_statement: Dict[UUID, List[Vote]] = defaultdict(list)
    for vote in votes:
        votes_by_statement[vote.statement_id].append(vote)

    # Update statement vote counts
    for statement in statements:
        statement_votes = votes_by_statement.get(statement.id, [])

        # Count votes by type
        statement.agree_count = sum(
            1 for v in statement_votes if v.vote == VoteType.AGREE
        )
        statement.disagree_count = sum(
            1 for v in statement_votes if v.vote == VoteType.DISAGREE
        )
        statement.pass_count = sum(
            1 for v in statement_votes if v.vote == VoteType.PASS
        )

        # Calculate agreement rate
        total_votes = statement.agree_count + statement.disagree_count
        statement.agree_rate = (
            statement.agree_count / total_votes if total_votes > 0 else 0.0
        )


def detect_duplicate_votes(votes: List[Vote]) -> List[Vote]:
    """Remove duplicate votes from the same user/session on the same statement"""

    seen_votes = set()
    unique_votes = []

    for vote in votes:
        # Create identifier for user+statement combination
        identifier = (vote.statement_id, vote.user_id or vote.session_id)

        if identifier not in seen_votes:
            seen_votes.add(identifier)
            unique_votes.append(vote)

    return unique_votes


def get_consensus_statements(
    statements: List[ConsensusStatement],
    min_votes: int = 3,
    consensus_threshold: float = 0.7,
) -> List[ConsensusStatement]:
    """Get statements with high consensus (agreement rate above threshold)"""

    consensus = []

    for statement in statements:
        total_votes = statement.agree_count + statement.disagree_count

        if total_votes >= min_votes and statement.agree_rate >= consensus_threshold:
            consensus.append(statement)

    # Sort by agreement rate, then by total votes
    return sorted(
        consensus,
        key=lambda s: (s.agree_rate, s.agree_count + s.disagree_count),
        reverse=True,
    )


def get_divisive_statements(
    statements: List[ConsensusStatement],
    min_votes: int = 3,
    divisive_range: Tuple[float, float] = (0.3, 0.7),
) -> List[ConsensusStatement]:
    """Get statements that are divisive (agreement rate in middle range)"""

    divisive = []

    for statement in statements:
        total_votes = statement.agree_count + statement.disagree_count

        if (
            total_votes >= min_votes
            and divisive_range[0] <= statement.agree_rate <= divisive_range[1]
        ):
            divisive.append(statement)

    # Sort by how close to 50/50 the split is (most divisive first)
    return sorted(divisive, key=lambda s: abs(0.5 - s.agree_rate))


def create_vote_matrix(
    statements: List[ConsensusStatement], votes: List[Vote]
) -> Tuple[np.ndarray, List[str], List[UUID]]:
    """Create user-statement vote matrix for clustering"""

    # Get unique users/sessions
    users = list(
        set(v.user_id or v.session_id for v in votes if v.user_id or v.session_id)
    )
    statement_ids = [s.id for s in statements]

    if not users or not statement_ids:
        return np.array([]), [], []

    # Create vote matrix (users x statements)
    matrix = np.zeros((len(users), len(statement_ids)))

    # Fill matrix with votes
    user_idx_map = {user: idx for idx, user in enumerate(users)}
    stmt_idx_map = {stmt_id: idx for idx, stmt_id in enumerate(statement_ids)}

    for vote in votes:
        user_key = vote.user_id or vote.session_id
        if user_key in user_idx_map and vote.statement_id in stmt_idx_map:
            user_idx = user_idx_map[user_key]
            stmt_idx = stmt_idx_map[vote.statement_id]

            # Convert vote to numeric value
            if vote.vote == VoteType.AGREE:
                matrix[user_idx, stmt_idx] = 1
            elif vote.vote == VoteType.DISAGREE:
                matrix[user_idx, stmt_idx] = -1
            # VoteType.PASS remains 0

    return matrix, users, statement_ids


def cluster_users_by_votes(
    statements: List[ConsensusStatement], votes: List[Vote], n_clusters: int = 3
) -> List[ConsensusCluster]:
    """Cluster users by their voting patterns using k-means"""

    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        # Return empty clusters if sklearn not available
        return []

    matrix, users, statement_ids = create_vote_matrix(statements, votes)

    if matrix.size == 0 or len(users) < n_clusters:
        return []

    try:
        # Standardize the matrix
        scaler = StandardScaler()
        matrix_scaled = scaler.fit_transform(matrix)

        # Perform k-means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(matrix_scaled)

        clusters = []

        for cluster_id in range(n_clusters):
            # Get users in this cluster
            cluster_users = [
                users[i] for i in range(len(users)) if cluster_labels[i] == cluster_id
            ]

            if not cluster_users:
                continue

            # Calculate average agreement within cluster
            cluster_votes = matrix[cluster_labels == cluster_id]
            if cluster_votes.size > 0:
                # Calculate average pairwise agreement
                agreements = []
                for i in range(len(cluster_votes)):
                    for j in range(i + 1, len(cluster_votes)):
                        # Calculate agreement between users i and j
                        user_i_votes = cluster_votes[i]
                        user_j_votes = cluster_votes[j]

                        # Only compare statements both users voted on
                        both_voted = (user_i_votes != 0) & (user_j_votes != 0)
                        if np.any(both_voted):
                            agreement = np.mean(
                                user_i_votes[both_voted] == user_j_votes[both_voted]
                            )
                            agreements.append(agreement)

                avg_agreement = np.mean(agreements) if agreements else 0.0
            else:
                avg_agreement = 0.0

            # Find statements this cluster tends to agree on
            cluster_statement_ids = []
            if cluster_votes.size > 0:
                cluster_avg_votes = np.mean(cluster_votes, axis=0)
                # Include statements with strong positive or negative consensus (> 0.6 absolute)
                for idx, avg_vote in enumerate(cluster_avg_votes):
                    if abs(avg_vote) > 0.6:
                        cluster_statement_ids.append(statement_ids[idx])

            cluster = ConsensusCluster(
                id=cluster_id,
                statements=cluster_statement_ids,
                user_count=len(cluster_users),
                avg_agreement=avg_agreement,
                description=f"Cluster {cluster_id + 1}: {len(cluster_users)} users with {avg_agreement:.1%} avg agreement",
            )

            clusters.append(cluster)

        # Sort clusters by user count (largest first)
        return sorted(clusters, key=lambda c: c.user_count, reverse=True)

    except Exception as e:
        print(f"Clustering failed: {e}")
        return []


def calculate_polarization_score(statements: List[ConsensusStatement]) -> float:
    """Calculate overall polarization score for a topic (0 = consensus, 1 = highly polarized)"""

    if not statements:
        return 0.0

    # Calculate average distance from 50% agreement
    polarization_scores = []

    for statement in statements:
        total_votes = statement.agree_count + statement.disagree_count
        if total_votes > 0:
            # Polarization is measured by how far from 50/50 split
            # 0 = perfect 50/50 split (most polarized)
            # 1 = unanimous (least polarized)
            polarization = abs(statement.agree_rate - 0.5) * 2
            polarization_scores.append(1 - polarization)  # Invert so 1 = most polarized

    return np.mean(polarization_scores) if polarization_scores else 0.0
