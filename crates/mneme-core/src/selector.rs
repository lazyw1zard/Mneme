use std::collections::HashSet;

use crate::model::{ActiveReadSet, MemoryNode, MnemeState, ProfileIndex, ScoredNode};

pub fn select(
    index: &ProfileIndex,
    state: &MnemeState,
    context: &str,
    limit: usize,
) -> ActiveReadSet {
    let mut selected: Vec<ScoredNode> = index
        .nodes
        .iter()
        .map(|node| score_node(node, state, context))
        .collect();

    selected.sort_by(|left, right| {
        right
            .score
            .partial_cmp(&left.score)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| left.id.cmp(&right.id))
    });

    selected.truncate(limit.max(1));

    ActiveReadSet {
        context: context.to_string(),
        limit,
        selected,
    }
}

pub fn explain(
    index: &ProfileIndex,
    state: &MnemeState,
    context: &str,
    node_id: &str,
) -> Option<ScoredNode> {
    index
        .nodes
        .iter()
        .find(|node| node.id == node_id)
        .map(|node| score_node(node, state, context))
}

fn score_node(node: &MemoryNode, state: &MnemeState, context: &str) -> ScoredNode {
    let mut score = node.base_weight + node.dynamic_weight;
    let mut reasons = Vec::new();

    if node.pinned {
        score += 0.15;
        reasons.push("pinned:+0.15".to_string());
    }

    if node.contexts.iter().any(|item| item == context) {
        score += 0.35;
        reasons.push(format!("context:{context}:+0.35"));
    }

    let tag_matches = context_tags(context)
        .intersection(&node.tags.iter().map(String::as_str).collect())
        .count();

    if tag_matches > 0 {
        let boost = 0.08 * tag_matches as f64;
        score += boost;
        reasons.push(format!("tag_match:{tag_matches}:+{boost:.2}"));
    }

    for affect_tag in &node.affect_tags {
        if let Some(vector) = state.affect_vectors.get(affect_tag) {
            let boost = 0.18 * vector.intensity;
            if boost > 0.0 {
                score += boost;
                reasons.push(format!("affect:{affect_tag}:+{boost:.2}"));
            }
        }
    }

    if node.decay > 0.0 {
        score -= node.decay;
        reasons.push(format!("decay:-{:.2}", node.decay));
    }

    ScoredNode {
        id: node.id.clone(),
        path: node.path.clone(),
        title: node.title.clone(),
        role: node.role.clone(),
        layer: node.layer.clone(),
        read_rule: node.read_rule.clone(),
        score: round_score(score),
        reasons,
    }
}

fn context_tags(context: &str) -> HashSet<&'static str> {
    match context {
        "bootstrap" => ["identity-core", "operational", "state"]
            .into_iter()
            .collect(),
        "affect" => ["affect", "symbolic-context", "identity-core"]
            .into_iter()
            .collect(),
        "kernel-maintenance" => ["operational", "kernel", "memory"].into_iter().collect(),
        "cadrelay" => ["project-active", "technical-context"]
            .into_iter()
            .collect(),
        "mneme" => ["mneme", "memory", "affect", "technical-context"]
            .into_iter()
            .collect(),
        "historical-lookup" => ["archival", "history"].into_iter().collect(),
        _ => HashSet::new(),
    }
}

fn round_score(score: f64) -> f64 {
    (score * 1000.0).round() / 1000.0
}

#[cfg(test)]
mod tests {
    use crate::store::MnemeStore;

    #[test]
    fn mneme_context_prioritizes_mneme_nodes() {
        let store = MnemeStore::from_project_root("../../").expect("fixture store");
        let read_set = store.select("mneme", 4).expect("select");
        let ids: Vec<_> = read_set
            .selected
            .iter()
            .map(|node| node.id.as_str())
            .collect();

        assert!(ids.contains(&"mneme_roadmap"));
        assert!(ids.contains(&"mneme_project"));
    }

    #[test]
    fn affect_context_prioritizes_affect_and_symbols() {
        let store = MnemeStore::from_project_root("../../").expect("fixture store");
        let read_set = store.select("affect", 5).expect("select");
        let ids: Vec<_> = read_set
            .selected
            .iter()
            .map(|node| node.id.as_str())
            .collect();

        assert!(ids.contains(&"affect_model"));
        assert!(ids.contains(&"symbols"));
    }

    #[test]
    fn explain_returns_scoring_reasons() {
        let store = MnemeStore::from_project_root("../../").expect("fixture store");
        let node = store
            .explain("mneme", "mneme_roadmap")
            .expect("explain")
            .expect("node exists");

        assert!(!node.reasons.is_empty());
    }
}
