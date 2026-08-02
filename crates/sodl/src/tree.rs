//! Indented-tree rendering of a parsed program, for golden-file tests.
//!
//! This is a *stable* rendering, not a debug dump. It exists so a diff shows
//! what a grammar change did to the parse, which means it must not churn
//! when an AST field is renamed or reordered. Print what the source said,
//! in source order, and nothing about how it is stored.

use crate::ast::{Bound, Constraint, Decl, Literal, Type};

const INDENT: &str = "  ";

fn literal(l: &Literal) -> String {
    match l {
        Literal::Int(n) => n.to_string(),
        Literal::Float(f) => {
            // Always show a point, so 1.0 does not render as "1" and read
            // as an integer in the golden.
            if f.fract() == 0.0 {
                format!("{f:.1}")
            } else {
                f.to_string()
            }
        }
        Literal::Str(s) => format!("{s:?}"),
        Literal::Bool(b) => b.to_string(),
    }
}

fn ty(t: &Type) -> String {
    match t {
        Type::Named(n) => n.clone(),
        Type::Applied(n, a) => format!("{n}<{a}>"),
        Type::Qualified(m, n) => format!("{m}.{n}"),
    }
}

fn bound(b: &Bound) -> String {
    match b {
        Bound::Literal(l) => literal(l),
        Bound::ConstRef(n) => format!("const {n}"),
    }
}

fn constraint(c: &Constraint) -> String {
    match c {
        Constraint::Range(lo, hi) => format!("range {} .. {}", bound(lo), bound(hi)),
        Constraint::Pattern(p) => format!("pattern {}", bound(p)),
    }
}

/// Render a program as an indented tree, newline-terminated.
pub fn render(decls: &[Decl]) -> String {
    let mut out = String::from("program\n");
    for d in decls {
        match d {
            Decl::Const(c) => {
                out.push_str(&format!(
                    "{INDENT}const {}: {} = {}\n",
                    c.name,
                    c.ty,
                    literal(&c.value)
                ));
            }
            Decl::Alias(a) => {
                out.push_str(&format!("{INDENT}alias {} = {}\n", a.name, ty(&a.ty)));
                for c in &a.constraints {
                    out.push_str(&format!("{INDENT}{INDENT}{}\n", constraint(c)));
                }
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use crate::parser::parse;
    use crate::tree::render;

    #[test]
    fn renders_a_const_and_an_alias() {
        let decls = parse("const N: uint8 = 5; alias Port = uint16, range(1, 65535);").unwrap();
        assert_eq!(
            render(&decls),
            "program\n  const N: uint8 = 5\n  alias Port = uint16\n    range 1 .. 65535\n"
        );
    }

    #[test]
    fn renders_a_const_reference_as_such() {
        // A bound naming a const must not render as a bare identifier: the
        // distinction is the whole point of Bound (D10).
        let decls = parse("alias A = uint8, range(0, MAX);").unwrap();
        assert!(render(&decls).contains("range 0 .. const MAX"));
    }

    #[test]
    fn float_keeps_its_point() {
        let decls = parse("const F: float32 = 2.0;").unwrap();
        assert!(render(&decls).contains("= 2.0"));
    }
}
