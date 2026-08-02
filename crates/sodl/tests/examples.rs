//! Corpus and golden-file tests.
//!
//! Two things are checked here:
//!
//!   1. The example corpus exists and is grouped as `examples/README.md`
//!      describes.
//!   2. Every `.sodl` beside a `.tree` golden parses to exactly that tree.
//!
//! The parser covers only part of the grammar, so most of the corpus has no
//! golden yet. Rather than skip silently, the golden test reports how many
//! files are still uncovered — the number should fall as the parser grows.

use std::fs;
use std::path::{Path, PathBuf};

use sodl::{parser, tree};

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

fn sodl_files(dir: &Path) -> Vec<PathBuf> {
    let mut out = Vec::new();
    let mut stack = vec![dir.to_path_buf()];
    while let Some(d) = stack.pop() {
        for entry in fs::read_dir(&d).expect("readable directory") {
            let path = entry.expect("readable entry").path();
            if path.is_dir() {
                stack.push(path);
            } else if path.extension().and_then(|e| e.to_str()) == Some("sodl") {
                out.push(path);
            }
        }
    }
    out.sort();
    out
}

#[test]
fn corpus_is_grouped_and_non_empty() {
    let examples = repo_root().join("examples");
    for group in ["core", "layout", "extensions", "integration", "invalid"] {
        let dir = examples.join(group);
        assert!(dir.is_dir(), "examples/{group}/ should exist");
        assert!(
            !sodl_files(&dir).is_empty(),
            "examples/{group}/ should hold at least one .sodl"
        );
    }
    assert!(
        sodl_files(&examples).len() >= 20,
        "corpus looks unexpectedly small"
    );
}

#[test]
fn every_invalid_example_names_the_codes_it_must_produce() {
    // An invalid file with no .expected is a test that asserts nothing.
    let invalid = repo_root().join("examples").join("invalid");
    for src in sodl_files(&invalid) {
        let expected = src.with_extension("expected");
        assert!(
            expected.is_file(),
            "{} has no .expected file naming its error codes",
            src.display()
        );
        let body = fs::read_to_string(&expected).expect("readable .expected");
        assert!(
            body.split_whitespace().any(|t| t.starts_with('E')),
            "{} names no error code",
            expected.display()
        );
    }
}

#[test]
fn goldens_match_the_parse() {
    let examples = repo_root().join("examples");
    let all = sodl_files(&examples);
    let mut checked = 0;

    for src in &all {
        let golden = src.with_extension("tree");
        if !golden.is_file() {
            continue;
        }
        let text = fs::read_to_string(src).expect("readable source");
        let want = fs::read_to_string(&golden).expect("readable golden");
        let decls = match parser::parse(&text) {
            Ok(d) => d,
            Err(errs) => panic!("{} failed to parse: {}", src.display(), errs.join("; ")),
        };
        let got = tree::render(&decls);
        assert_eq!(
            got,
            want,
            "\ngolden mismatch for {}\n--- want ---\n{want}--- got ---\n{got}",
            src.display()
        );
        checked += 1;
    }

    assert!(checked > 0, "no golden files found — the harness is inert");
    eprintln!(
        "goldens: {checked} of {} corpus files covered ({} awaiting parser support)",
        all.len(),
        all.len() - checked
    );
}
