use std::env;

use mneme_core::MnemeStore;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Temporary CLI smoke path. This binary will become the MCP stdio server next.
    let project_root = env::var("MNEME_PROJECT_ROOT").unwrap_or_else(|_| ".".to_string());
    let context = env::args().nth(1).unwrap_or_else(|| "mneme".to_string());
    let store = MnemeStore::from_project_root(project_root)?;
    let read_set = store.select(&context, 8)?;

    println!("{}", serde_json::to_string_pretty(&read_set)?);

    Ok(())
}
