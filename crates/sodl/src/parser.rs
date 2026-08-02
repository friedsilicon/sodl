//! Parser for the `const` and `alias` slice of `spec/sodl.ebnf`.
//!
//! Built on chumsky (D13). This is a vertical slice, not a partial parser of
//! the whole grammar: it parses two declarations completely and rejects
//! everything else, so the tests can assert on real example text rather than
//! on fixtures. The remaining declarations land here as they are written.

use chumsky::prelude::*;

use crate::ast::{AliasDecl, Bound, ConstDecl, Constraint, Decl, Literal, Type};

type Extra<'a> = extra::Err<Rich<'a, char>>;

/// Whitespace and `//` comments, which are trivia anywhere between tokens.
fn trivia<'a>() -> impl Parser<'a, &'a str, (), Extra<'a>> + Clone {
    let comment = just("//")
        .then(any().and_is(just('\n').not()).repeated())
        .ignored();
    choice((text::whitespace().at_least(1).ignored(), comment))
        .repeated()
        .ignored()
}

/// Wraps a parser so trailing trivia is consumed.
fn tok<'a, T, P>(p: P) -> impl Parser<'a, &'a str, T, Extra<'a>> + Clone
where
    P: Parser<'a, &'a str, T, Extra<'a>> + Clone,
{
    p.then_ignore(trivia())
}

fn ident<'a>() -> impl Parser<'a, &'a str, String, Extra<'a>> + Clone {
    tok(text::ident().map(|s: &str| s.to_string()))
}

fn keyword<'a>(kw: &'static str) -> impl Parser<'a, &'a str, (), Extra<'a>> + Clone {
    tok(text::keyword(kw)).ignored()
}

fn sym<'a>(c: char) -> impl Parser<'a, &'a str, (), Extra<'a>> + Clone {
    tok(just(c)).ignored()
}

fn string_literal<'a>() -> impl Parser<'a, &'a str, String, Extra<'a>> + Clone {
    tok(any()
        .and_is(just('"').not())
        .repeated()
        .to_slice()
        .map(|s: &str| s.to_string())
        .delimited_by(just('"'), just('"')))
}

/// Number, string, or bool. `bytes` and `Timestamp` have no literal form
/// (D10), which is a check for a later pass, not a parse error.
fn literal<'a>() -> impl Parser<'a, &'a str, Literal, Extra<'a>> + Clone {
    let hex = just("0x")
        .ignore_then(text::digits(16).to_slice())
        .map(|s: &str| Literal::Int(i64::from_str_radix(s, 16).unwrap_or(0)));

    let number = just('-')
        .or_not()
        .then(text::int(10))
        .then(just('.').then(text::digits(10)).or_not())
        .to_slice()
        .map(|s: &str| {
            if s.contains('.') {
                Literal::Float(s.parse().unwrap_or(0.0))
            } else {
                Literal::Int(s.parse().unwrap_or(0))
            }
        });

    let boolean = choice((
        text::keyword("true").to(Literal::Bool(true)),
        text::keyword("false").to(Literal::Bool(false)),
    ));

    choice((
        tok(hex),
        tok(boolean),
        tok(number),
        string_literal().map(Literal::Str),
    ))
}

/// A bound is a literal or a name standing for one (D10, static check 6).
fn bound<'a>() -> impl Parser<'a, &'a str, Bound, Extra<'a>> + Clone {
    choice((
        literal().map(Bound::Literal),
        ident().map(Bound::ConstRef),
    ))
}

fn constraint<'a>() -> impl Parser<'a, &'a str, Constraint, Extra<'a>> + Clone {
    let range = keyword("range")
        .ignore_then(sym('('))
        .ignore_then(bound())
        .then_ignore(sym(','))
        .then(bound())
        .then_ignore(sym(')'))
        .map(|(lo, hi)| Constraint::Range(lo, hi));

    let pattern = keyword("pattern")
        .ignore_then(sym('='))
        .ignore_then(bound())
        .map(Constraint::Pattern);

    choice((range, pattern))
}

fn type_ref<'a>() -> impl Parser<'a, &'a str, Type, Extra<'a>> + Clone {
    // `name`, `name.name`, or `name<arg>`. The three are distinguished by
    // one token of lookahead; none is resolved here.
    let qualified = just('.').ignore_then(text::ident()).map(Suffix::Qualified);
    let applied = text::ident()
        .or(text::int(10))
        .delimited_by(just('<'), just('>'))
        .map(Suffix::Applied);

    tok(text::ident().then(choice((qualified, applied)).or_not()).map(
        |(head, suffix): (&str, Option<Suffix>)| match suffix {
            Some(Suffix::Qualified(t)) => Type::Qualified(head.to_string(), t.to_string()),
            Some(Suffix::Applied(a)) => Type::Applied(head.to_string(), a.to_string()),
            None => Type::Named(head.to_string()),
        },
    ))
}

#[derive(Clone)]
enum Suffix<'a> {
    Qualified(&'a str),
    Applied(&'a str),
}

/// `const NAME: TYPE = VALUE;`
fn const_decl<'a>() -> impl Parser<'a, &'a str, ConstDecl, Extra<'a>> + Clone {
    keyword("const")
        .ignore_then(ident())
        .then_ignore(sym(':'))
        .then(ident())
        .then_ignore(sym('='))
        .then(literal())
        .then_ignore(sym(';'))
        .map(|((name, ty), value)| ConstDecl { name, ty, value })
}

/// `alias NAME = TYPE, constraints...;`
fn alias_decl<'a>() -> impl Parser<'a, &'a str, AliasDecl, Extra<'a>> + Clone {
    keyword("alias")
        .ignore_then(ident())
        .then_ignore(sym('='))
        .then(type_ref())
        .then(
            sym(',')
                .ignore_then(constraint())
                .repeated()
                .collect::<Vec<_>>(),
        )
        .then_ignore(sym(';'))
        .map(|((name, ty), constraints)| AliasDecl {
            name,
            ty,
            constraints,
        })
}

/// Parses a whole source of `const` and `alias` declarations.
pub fn parser<'a>() -> impl Parser<'a, &'a str, Vec<Decl>, Extra<'a>> {
    let decl = choice((
        const_decl().map(Decl::Const),
        alias_decl().map(Decl::Alias),
    ));

    trivia()
        .ignore_then(decl.repeated().collect::<Vec<_>>())
        .then_ignore(end())
}

/// Parse `src`, returning the declarations or a list of rendered errors.
pub fn parse(src: &str) -> Result<Vec<Decl>, Vec<String>> {
    parser()
        .parse(src)
        .into_result()
        .map_err(|errs| errs.iter().map(|e| e.to_string()).collect())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_a_const() {
        let decls = parse("const MAX: uint8 = 5;").expect("should parse");
        assert_eq!(
            decls,
            vec![Decl::Const(ConstDecl {
                name: "MAX".into(),
                ty: "uint8".into(),
                value: Literal::Int(5),
            })]
        );
    }

    #[test]
    fn parses_string_and_bool_consts() {
        let decls = parse(r#"const T: string = "light"; const B: bool = true;"#)
            .expect("should parse");
        assert_eq!(decls.len(), 2);
        assert!(matches!(
            &decls[0],
            Decl::Const(c) if c.value == Literal::Str("light".into())
        ));
        assert!(matches!(
            &decls[1],
            Decl::Const(c) if c.value == Literal::Bool(true)
        ));
    }

    #[test]
    fn parses_hex_literal() {
        let decls = parse("const MASK: uint16 = 0xFF;").expect("should parse");
        assert!(matches!(
            &decls[0],
            Decl::Const(c) if c.value == Literal::Int(255)
        ));
    }

    #[test]
    fn parses_alias_with_constraint() {
        let decls = parse("alias Port = uint16, range(1, 65535);").expect("should parse");
        assert_eq!(
            decls,
            vec![Decl::Alias(AliasDecl {
                name: "Port".into(),
                ty: Type::Named("uint16".into()),
                constraints: vec![Constraint::Range(
                    Bound::Literal(Literal::Int(1)),
                    Bound::Literal(Literal::Int(65535)),
                )],
            })]
        );
    }

    #[test]
    fn parses_alias_with_pattern() {
        let decls = parse(r#"alias UUID = string, pattern = "^[0-9a-f]+$";"#)
            .expect("should parse");
        assert!(matches!(
            &decls[0],
            Decl::Alias(a) if a.constraints.len() == 1
        ));
    }

    #[test]
    fn range_bound_may_name_a_const() {
        // D10: a bound may be a const reference. The parser records the name;
        // resolving it is a later pass.
        let decls = parse("alias Attempts = uint8, range(0, MAX_LOGIN);").expect("should parse");
        assert!(matches!(
            &decls[0],
            Decl::Alias(a) if a.constraints[0]
                == Constraint::Range(
                    Bound::Literal(Literal::Int(0)),
                    Bound::ConstRef("MAX_LOGIN".into()),
                )
        ));
    }

    #[test]
    fn parses_bounded_string() {
        let decls = parse("alias Name = string<32>;").expect("should parse");
        assert!(matches!(
            &decls[0],
            Decl::Alias(a) if a.ty == Type::Applied("string".into(), "32".into())
        ));
    }

    #[test]
    fn parses_temporal_type() {
        let decls = parse("alias When = timestamp<ms>;").expect("should parse");
        assert!(matches!(
            &decls[0],
            Decl::Alias(a) if a.ty == Type::Applied("timestamp".into(), "ms".into())
        ));
    }

    #[test]
    fn parses_qualified_type() {
        let decls = parse("alias Hash = Crypto.SHA256Hash;").expect("should parse");
        assert!(matches!(
            &decls[0],
            Decl::Alias(a) if a.ty == Type::Qualified("Crypto".into(), "SHA256Hash".into())
        ));
    }

    #[test]
    fn skips_comments_and_whitespace() {
        let src = "
            // a leading comment
            const A: uint8 = 1;   // trailing

            // another
            alias B = uint8;
        ";
        assert_eq!(parse(src).expect("should parse").len(), 2);
    }

    #[test]
    fn rejects_a_missing_semicolon() {
        assert!(parse("const A: uint8 = 1").is_err());
    }

    #[test]
    fn rejects_unknown_construct() {
        // struct is not in this slice yet; it must fail rather than be skipped.
        assert!(parse("struct Foo { a: uint8; }").is_err());
    }
}
