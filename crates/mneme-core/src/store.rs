use std::fs;
use std::path::{Path, PathBuf};

use thiserror::Error;

use crate::model::{ActiveReadSet, MnemeState, ProfileIndex, ScoredNode};

#[derive(Debug, Error)]
pub enum MnemeError {
    #[error("failed to read {path}: {source}")]
    Read {
        path: PathBuf,
        source: std::io::Error,
    },
    #[error("failed to parse JSON from {path}: {source}")]
    Json {
        path: PathBuf,
        source: serde_json::Error,
    },
}

pub struct MnemeStore {
    project_root: PathBuf,
}

impl MnemeStore {
    pub fn from_project_root(path: impl AsRef<Path>) -> Result<Self, MnemeError> {
        Ok(Self {
            project_root: path
                .as_ref()
                .canonicalize()
                .unwrap_or_else(|_| path.as_ref().to_path_buf()),
        })
    }

    pub fn select(&self, context: &str, limit: usize) -> Result<ActiveReadSet, MnemeError> {
        let index = self.profile_index()?;
        let state = self.state()?;
        Ok(crate::selector::select(&index, &state, context, limit))
    }

    pub fn explain(&self, context: &str, node_id: &str) -> Result<Option<ScoredNode>, MnemeError> {
        let index = self.profile_index()?;
        let state = self.state()?;
        Ok(crate::selector::explain(&index, &state, context, node_id))
    }

    pub fn profile_index(&self) -> Result<ProfileIndex, MnemeError> {
        self.read_json(self.project_root.join("data").join("profile-index.json"))
    }

    pub fn state(&self) -> Result<MnemeState, MnemeError> {
        self.read_json(self.project_root.join("data").join("state.json"))
    }

    fn read_json<T>(&self, path: PathBuf) -> Result<T, MnemeError>
    where
        T: serde::de::DeserializeOwned,
    {
        let text = fs::read_to_string(&path).map_err(|source| MnemeError::Read {
            path: path.clone(),
            source,
        })?;

        serde_json::from_str(&text).map_err(|source| MnemeError::Json { path, source })
    }
}
