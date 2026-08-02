//! Syntax tree for the slice of SODL the parser currently covers.
//!
//! Deliberately shallow: names and literals are kept as written, and nothing
//! is resolved. Resolution (D5's dotted-name question, const references,
//! alias chains) belongs to a later pass over this tree, not to the parser.

/// A literal as written in the source.
#[derive(Debug, Clone, PartialEq)]
pub enum Literal {
    Int(i64),
    Float(f64),
    Str(String),
    Bool(bool),
}

/// A type in type position. `Named` covers both user types and basic types;
/// which is which is a resolution question, not a syntactic one.
#[derive(Debug, Clone, PartialEq)]
pub enum Type {
    Named(String),
    /// A parameterized type written `name<arg>` — `string<36>` (D16),
    /// `timestamp<ms>` (D17). The argument is kept as written; whether it
    /// is a valid size or unit is a resolution question.
    Applied(String, String),
    /// `Crypto.SHA256Hash` — a qualified type (D5).
    Qualified(String, String),
}

/// A `range` bound or `pattern`. Bounds are kept unresolved: the grammar
/// admits a const reference here as well as a literal (D10), and telling
/// them apart needs a symbol table.
#[derive(Debug, Clone, PartialEq)]
pub enum Bound {
    Literal(Literal),
    ConstRef(String),
}

#[derive(Debug, Clone, PartialEq)]
pub enum Constraint {
    Range(Bound, Bound),
    Pattern(Bound),
}

/// `const NAME: TYPE = VALUE;` — D10.
#[derive(Debug, Clone, PartialEq)]
pub struct ConstDecl {
    pub name: String,
    pub ty: String,
    pub value: Literal,
}

/// `alias NAME = TYPE, constraints...;` — D11.
#[derive(Debug, Clone, PartialEq)]
pub struct AliasDecl {
    pub name: String,
    pub ty: Type,
    pub constraints: Vec<Constraint>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Decl {
    Const(ConstDecl),
    Alias(AliasDecl),
}
