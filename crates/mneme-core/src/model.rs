use std::collections::HashMap;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ProfileIndex {
    pub version: u32,
    pub kind: String,
    pub root: String,
    pub nodes: Vec<MemoryNode>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct MemoryNode {
    pub id: String,
    pub path: String,
    pub title: String,
    pub role: String,
    pub layer: String,
    pub node_type: String,
    pub base_weight: f64,
    pub dynamic_weight: f64,
    pub decay: f64,
    pub pinned: bool,
    pub tags: Vec<String>,
    pub contexts: Vec<String>,
    pub affect_tags: Vec<String>,
    pub read_rule: String,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct MnemeState {
    pub version: u32,
    pub kind: String,
    pub current_context: String,
    pub affect_vectors: HashMap<String, AffectVector>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct AffectVector {
    pub intensity: f64,
    pub inertia: f64,
    pub decay: f64,
    pub last_update: String,
}

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct ScoredNode {
    pub id: String,
    pub path: String,
    pub title: String,
    pub role: String,
    pub layer: String,
    pub read_rule: String,
    pub score: f64,
    pub reasons: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct ActiveReadSet {
    pub context: String,
    pub limit: usize,
    pub selected: Vec<ScoredNode>,
}
