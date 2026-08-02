//! Corpus smoke test.
//!
//! Establishes the harness that will, once the parser exists, parse every
//! file under `examples/`. For now it asserts the corpus is present and
//! non-empty, so the path wiring stays honest as the tree moves.

use std::fs;
use std::path::PathBuf;

fn examples_dir() -> PathBuf {
    // crates/sodl -> repo root -> examples
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
        .join("examples")
}

#[test]
fn corpus_is_present_and_non_empty() {
    let dir = examples_dir();
    let mut count = 0;
    for entry in fs::read_dir(&dir).expect("examples/ should exist") {
        let path = entry.expect("readable dir entry").path();
        if path.extension().and_then(|e| e.to_str()) == Some("sodl") {
            let bytes = fs::metadata(&path).expect("stat example").len();
            assert!(bytes > 0, "{} is empty", path.display());
            count += 1;
        }
    }
    assert!(
        count >= 2,
        "expected at least two .sodl examples, found {count}"
    );
}
