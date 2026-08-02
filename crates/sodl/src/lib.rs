//! SODL toolchain.
//!
//! Pipeline (the language lives in `spec/`; the plan is `spec/TODO.md`,
//! section "Toolchain"):
//!
//! ```text
//! .sodl text --> parser --> AST --> resolver + checker --> IR
//!                                                            |
//!            format backends (Avro / Parquet / Protobuf)  +  codegen
//! ```
//!
//! Single-language toolchain: the IR is in-memory typed data, and every
//! format and codegen backend is a library against it. Nothing is
//! implemented yet — this crate is the skeleton the parser lands in first
//! (`spec/TODO.md`: "Write a parser"). The `spec/TODO.md` "Format-interchange
//! gaps" section tracks what the IR must be able to represent.

pub mod ast;
pub mod parser;

/// Crate version, from Cargo.
pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn version_is_set() {
        assert!(!version().is_empty());
    }
}
