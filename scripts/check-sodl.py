#!/usr/bin/env python3
"""Static checks for SODL sources.

The EBNF in spec/sodl.ebnf defines what parses. It cannot express the rules
that make a schema coherent -- those live here. See spec/DECISIONS.md (D6,
D7) and the STATIC CHECKS block at the foot of spec/sodl.ebnf.

This is a lint over the concrete syntax, not a parser: it reads the
constructs by regex. It exists to keep the example files honest about the
rules the language claims. A real front end would do this on the AST.

Usage: scripts/check-sodl.py FILE...   (exit 1 if any check fails)
       scripts/check-sodl.py           (defaults to the examples/ corpus)
"""

import re
import sys
from pathlib import Path

# scripts/ -> repo root -> examples/. Lets the no-arg default work from any cwd.
ROOT = Path(__file__).resolve().parent.parent
# Every .sodl in the corpus except examples/invalid/, which is expected to
# fail and is driven by scripts/run-checks.py instead.
DEFAULT_CORPUS = sorted(
    str(p)
    for p in (ROOT / "examples").rglob("*.sodl")
    if "invalid" not in p.parts
)

# Error codes -- stable identifiers so tests can assert which rule fired
# without depending on message wording. Numbers follow the STATIC CHECKS
# list at the foot of spec/sodl.ebnf; codes above E016 are rules stated in
# the spec but not in that numbered list.
CODES = {
    "E001": "key or keymap references a field not annotated `key` (check 1)",
    "E002": "`key` field reached by no key declaration or keymap (check 2)",
    "E003": "keymap names an undeclared key or object (check 3)",
    "E005": "import collides with a BasicType or ExtensionType (check 5)",
    "E006": "const declaration or const reference is invalid (check 6)",
    "E007": "alias chain contains a cycle (check 7)",
    "E009": "union tag is out of range, duplicated, or wrongly typed (check 9)",
    "E010": "union member type is not fixed-size (check 10)",
    "E012": "fixed-size field follows a variable-length one (check 12)",
    "E013": "fixed list has a variable-length element type (check 13)",
    "E016": "temporal unit missing or invalid (check 16)",
    "E017": "`required` is redundant on a `key` field (D6 rule 1)",
    "E018": "object declares no `key` field (D6 rule 3)",
}

BASIC_TYPES = {
    "uint8", "uint16", "uint32", "uint64",
    "int8", "int16", "int32", "int64",
    "float32", "float64",
    "string", "bool", "bytes",
}

# D17: extension types (spec/SODL_Extensions.md). Reserved like basic types,
# and all fixed-size, so none falls under the D16 ordering rule.
EXTENSION_TYPES = {"date", "duration"}
EXTENSION_PARAMETRIC = ("timestamp", "localTimestamp", "time")
TIME_UNITS = {"s", "ms", "us", "ns"}

# Inclusive value ranges for the integer basic types (D10, static check 6).
INT_RANGES = {
    "uint8": (0, 2**8 - 1),
    "uint16": (0, 2**16 - 1),
    "uint32": (0, 2**32 - 1),
    "uint64": (0, 2**64 - 1),
    "int8": (-(2**7), 2**7 - 1),
    "int16": (-(2**15), 2**15 - 1),
    "int32": (-(2**31), 2**31 - 1),
    "int64": (-(2**63), 2**63 - 1),
}
FLOAT_TYPES = {"float32", "float64"}


def consts(src):
    """Parse `const NAME: TYPE = VALUE;` lines.

    Returns (errs, decls) where decls maps a const name to "number" for a
    numeric const and "other" otherwise -- enough to police range bounds,
    which must name a numeric const (D10, static check 6). Validates each
    literal against its declared basic type on the way through.
    """
    errs = []
    decls = {}
    for m in re.finditer(r"^const\s+(\w+)\s*:\s*(\w+)\s*=\s*(.+?);\s*$", src, re.M):
        name, ty, val = m.group(1), m.group(2), m.group(3).strip()
        if ty in INT_RANGES:
            if re.fullmatch(r"0x[0-9a-fA-F]+", val):
                n = int(val, 16)
            elif re.fullmatch(r"-?[0-9]+", val):
                n = int(val)
            else:
                errs.append(f"E006 const {name}: `{val}` is not an integer literal for `{ty}`")
                continue
            lo, hi = INT_RANGES[ty]
            if not lo <= n <= hi:
                errs.append(f"E006 const {name}: {val} out of range for `{ty}` [{lo}, {hi}]")
            decls[name] = "number"
        elif ty in FLOAT_TYPES:
            if not re.fullmatch(r"-?[0-9]+(\.[0-9]+)?", val):
                errs.append(f"E006 const {name}: `{val}` is not a numeric literal for `{ty}`")
            decls[name] = "number"
        elif ty == "string":
            if not re.fullmatch(r'"[^"]*"', val):
                errs.append(f"E006 const {name}: `{val}` is not a string literal")
            decls[name] = "other"
        elif ty == "bool":
            if val not in ("true", "false"):
                errs.append(f"E006 const {name}: `{val}` is not a bool literal")
            decls[name] = "other"
        elif ty == "bytes" or ty in EXTENSION_TYPES:
            errs.append(f"E006 const {name}: `{ty}` has no literal form (D10)")
            decls[name] = "other"
        else:
            errs.append(f"E006 const {name}: type `{ty}` is not a basic type (D10)")
            decls[name] = "other"
    return errs, decls


# D16 layout modifiers may precede a declaration keyword. Without this,
# `packed struct Foo` does not match `^struct` and the whole declaration is
# invisible to every check below -- which is exactly what happened, and what
# examples/invalid/ordering-violation.sodl now guards against.
MODS = r"(?:(?:packed|fixed(?:\s*\(\s*\d+\s*\))?|littleEndian|bigEndian)\s+)*"


def blocks(src, kw):
    """Yield (name, body) for each `[modifiers] kw Name { ... }` declaration."""
    for m in re.finditer(rf"^{MODS}{kw}\s+(\w+)[^{{]*\{{(.*?)^\}}", src, re.S | re.M):
        yield m.group(1), m.group(2)


def fields(body):
    """Yield (name, props_text) per field line: `name: Type, props;`."""
    for line in body.splitlines():
        line = re.sub(r"//.*", "", line)
        m = re.match(r"\s*(\w+)\s*:\s*(.*?);\s*$", line)
        if m:
            yield m.group(1), m.group(2)


# --- D16 layout: variable-length detection, the ordering rule, and fixed
# lists. A type is variable-length if it is bare `string`, `bytes`, a
# `tlv<T>`, or any declared type transitively containing one. `string<N>` is
# fixed. Imported names are unknown and assumed fixed -- the regex checker
# cannot see across files, which is the same blind spot noted for static
# check 4.

def type_graph(src):
    """Collect alias targets, aggregate field types, and union member types."""
    aliases = dict(re.findall(r"^alias\s+(\w+)\s*=\s*([^,;]+)", src, re.M))
    aggregates = {}
    for kw in ("struct", "object"):
        for name, body in blocks(src, kw):
            aggregates[name] = [t for _, t in fields(body)]
    for m in re.finditer(rf"^{MODS}union\s+(\w+)\s*:[^{{]*\{{(.*?)^\}}", src, re.S | re.M):
        members = []
        for line in m.group(2).splitlines():
            line = re.sub(r"//.*", "", line)
            mm = re.match(r"\s*\w+\s*=\s*\S+\s*->\s*(.+?)\s*;\s*$", line)
            if mm:
                members.append(mm.group(1).strip())
        aggregates[m.group(1)] = members
    return aliases, aggregates


def strip_props(t):
    """A field's text is `Type, prop, prop` -- keep the type."""
    depth = 0
    for i, ch in enumerate(t):
        if ch in "[<":
            depth += 1
        elif ch in "]>":
            depth -= 1
        elif ch == "," and depth == 0:
            return t[:i].strip()
    return t.strip()


def is_variable(t, aliases, aggregates, seen=None):
    t = strip_props(t)
    seen = seen or set()
    if re.match(r"^tlv\s*<", t) or t == "bytes" or t == "string":
        return True
    if re.match(r"^string\s*<\s*\d+\s*>$", t):
        return False
    m = re.match(r"^\[(.+);[^;\]]+\]$", t)
    if m:
        # A fixed list is itself fixed; a variable element is check 13's error.
        return False
    if t in seen:
        return False
    seen = seen | {t}
    if t in aliases:
        return is_variable(aliases[t], aliases, aggregates, seen)
    if t in aggregates:
        return any(is_variable(f, aliases, aggregates, seen) for f in aggregates[t])
    return False


def check_layout(src):
    """Static checks 12 and 13 (D16)."""
    errs = []
    aliases, aggregates = type_graph(src)

    # 12: within a declaration, no fixed field may follow a variable one.
    for kw in ("struct", "object"):
        for name, body in blocks(src, kw):
            seen_var = None
            for fname, ftext in fields(body):
                if is_variable(ftext, aliases, aggregates):
                    seen_var = seen_var or fname
                elif seen_var:
                    errs.append(
                        f"E012 {name}.{fname}: fixed-size field follows variable-length "
                        f"`{seen_var}` (D16 ordering rule, static check 12)"
                    )

    # 13: a fixed list needs a fixed-size element type.
    for m in re.finditer(r"\[([^\[\]]+);[^;\]]+\]", src):
        elem = m.group(1).strip()
        if is_variable(elem, aliases, aggregates):
            errs.append(
                f"E013 [{elem}; N]: element type is variable-length; a fixed list "
                f"needs computable offsets (D16, static check 13)"
            )
    return errs


def _is_var_member(mtype, src):
    aliases, aggregates = type_graph(src)
    return is_variable(mtype, aliases, aggregates)


def check(path):
    src = open(path).read()
    errs = []

    # --- D10: const declarations, and range bounds that name a const.
    const_errs, const_decls = consts(src)
    errs += const_errs
    for a, b in re.findall(r"range\s*\(\s*([^,]+?)\s*,\s*([^)]+?)\s*\)", src):
        for op in (a.strip(), b.strip()):
            if re.fullmatch(r"[A-Za-z_]\w*", op):
                if op not in const_decls:
                    errs.append(f"E006 range bound `{op}` names no declared const (D10)")
                elif const_decls[op] != "number":
                    errs.append(f"E006 range bound `{op}` is not a numeric const (D10)")

    objects = {n: dict(fields(b)) for n, b in blocks(src, "object")}
    keydecls = {n: dict(fields(b)) for n, b in blocks(src, "key")}

    keymaps = []  # (srckey, target, {lhs -> rhs})
    for m in re.finditer(r"^keymap\s+(\w+)\s*:\s*(\w+)\s*\{(.*?)^\}", src, re.S | re.M):
        pairs = dict(re.findall(r"^\s*(\w+)\s*->\s*([\w.]+)", m.group(3), re.M))
        keymaps.append((m.group(1), m.group(2), pairs))

    # key-annotated fields, per object
    keyed = {
        obj: {f for f, props in flds.items() if re.search(r"\bkey\b", props)}
        for obj, flds in objects.items()
    }

    # --- D6 rule 1: `key` implies `required`; the prop is redundant.
    for obj, flds in objects.items():
        for f, props in flds.items():
            if re.search(r"\bkey\b", props) and re.search(r"\brequired\b", props):
                errs.append(
                    f"E017 {obj}.{f}: `required` is redundant on a key field "
                    f"(D6 rule 1: key implies required)"
                )

    # --- D6 rule 3: every object needs at least one key field.
    for obj in objects:
        if not keyed[obj]:
            errs.append(f"E018 {obj}: no `key` field (D6 rule 3: every object needs one)")

    # --- D6 rule 2: every key field used by >=1 key decl AND >=1 keymap.
    for obj, kfields in keyed.items():
        # A key declaration names this object's fields if some keymap binds
        # it to this object. Its own field names need not all be top-level
        # fields of the object: a keymap may bind them via FieldPath into a
        # nested struct (SessionKey.deviceFingerprint ->
        # deviceInfo.deviceFingerprint), so match through the keymap rather
        # than by subset.
        by_keydecl = set()
        for srckey, tgt, pairs in keymaps:
            if tgt != obj:
                continue
            if srckey in keydecls:
                # fields of obj that this key reaches, directly or by binding
                by_keydecl |= set(keydecls[srckey]) & kfields
                by_keydecl |= {lhs for lhs in pairs if lhs in kfields}
        by_keymap = set()
        for srckey, tgt, pairs in keymaps:
            if tgt != obj:
                continue
            by_keymap |= set(pairs) & kfields
            by_keymap |= set(keydecls.get(srckey, {})) & kfields

        for f in sorted(kfields - by_keydecl):
            errs.append(f"E002 {obj}.{f}: key field named by no `key` declaration (D6 rule 2)")
        for f in sorted(kfields - by_keymap):
            errs.append(f"E002 {obj}.{f}: key field used by no `keymap` (D6 rule 2)")

    # --- D6: a key/keymap may only reference `key`-annotated fields.
    for srckey, tgt, pairs in keymaps:
        if tgt not in objects:
            errs.append(f"E003 keymap {srckey}:{tgt}: target object `{tgt}` not declared")
            continue
        for lhs in pairs:
            if lhs in objects[tgt] and lhs not in keyed[tgt]:
                errs.append(
                    f"E001 keymap {srckey}:{tgt}: `{lhs}` referenced but not "
                    f"annotated `key` on {tgt}"
                )

    # --- defect 17: keymaps must reference declared keys.
    for srckey, tgt, _ in keymaps:
        if srckey not in keydecls:
            errs.append(f"E003 keymap {srckey}:{tgt}: source key `{srckey}` not declared")

    # --- D12: discriminated unions. Tag type is unsigned; tags fit and are
    # unique; member names are unique; members are fixed-size (no bytes/tlv).
    unsigned_bits = {"uint8": 8, "uint16": 16, "uint32": 32, "uint64": 64}
    for m in re.finditer(rf"^{MODS}union\s+(\w+)\s*:\s*([^\s{{]+)\s*\{{(.*?)^\}}", src, re.S | re.M):
        uname, tagtype = m.group(1), m.group(2)
        bits = unsigned_bits.get(tagtype)
        if bits is None:
            errs.append(f"E009 union {uname}: tag type `{tagtype}` is not an unsigned integer (D12)")
        seen_names, seen_tags = set(), {}
        for line in m.group(3).splitlines():
            line = re.sub(r"//.*", "", line)
            mm = re.match(r"\s*(\w+)\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*->\s*(.+?)\s*;\s*$", line)
            if not mm:
                continue
            mname, tag, mtype = mm.group(1), mm.group(2), mm.group(3).strip()
            if mname in seen_names:
                errs.append(f"E009 union {uname}: duplicate member name `{mname}` (D12)")
            seen_names.add(mname)
            tagval = int(tag, 0)
            if tagval in seen_tags:
                errs.append(
                    f"E009 union {uname}: tag {tag} on `{mname}` duplicates `{seen_tags[tagval]}` (D12)"
                )
            else:
                seen_tags[tagval] = mname
            if bits is not None and tagval >= (1 << bits):
                errs.append(f"E009 union {uname}.{mname}: tag {tag} does not fit in {tagtype} (D12)")
            if _is_var_member(mtype, src):
                errs.append(
                    f"E010 union {uname}.{mname}: member type `{mtype}` is variable-length; "
                    f"union members must be fixed-size (D12)"
                )

    # --- D17 (static check 16): a temporal type's unit is written and valid.
    # Only in type position -- after `:`, `=`, `[`, or `->`. A field may
    # legitimately be *named* `timestamp`, which is not a type reference.
    for m in re.finditer(
        r"(?:[:=\[]|->)\s*(timestamp|localTimestamp|time)\b\s*(<\s*(\w+)\s*>)?", src
    ):
        kind, has_unit, unit = m.group(1), m.group(2), m.group(3)
        if not has_unit:
            errs.append(f"E016 `{kind}` requires a unit, e.g. `{kind}<ms>` (D17, static check 16)")
        elif unit not in TIME_UNITS:
            errs.append(
                f"E016 `{kind}<{unit}>`: unit must be one of s, ms, us, ns (D17, static check 16)"
            )

    # --- D16 (static checks 12, 13): layout ordering and fixed lists.
    errs += check_layout(src)

    # --- defect 19: importing a name that collides with a BasicType.
    for m in re.finditer(r"^import\s*\{([^}]*)\}", src, re.M):
        for name in (n.strip() for n in m.group(1).split(",")):
            if name in BASIC_TYPES:
                errs.append(f"E005 import: `{name}` collides with a BasicType (static check 5)")
            elif name in EXTENSION_TYPES or name in EXTENSION_PARAMETRIC:
                errs.append(
                    f"E005 import: `{name}` collides with an ExtensionType (D17, static check 5)"
                )

    # --- D11 (static check 7): alias chains must terminate; no cycles.
    # An alias's RHS head token is another alias iff it names one; those are
    # the only edges that can form a cycle. Chase each chain and flag a loop.
    aliases = dict(re.findall(r"^alias\s+(\w+)\s*=\s*(\w+)", src, re.M))
    for start in aliases:
        seen, cur = [], start
        while cur in aliases:
            if cur in seen:
                loop = " -> ".join(seen[seen.index(cur):] + [cur])
                errs.append(f"E007 alias `{start}`: cycle {loop} (static check 7)")
                break
            seen.append(cur)
            cur = aliases[cur]

    return errs


def main(paths):
    failed = False
    for p in paths:
        errs = check(p)
        if errs:
            failed = True
            print(f"{p}: {len(errs)} error(s)")
            for e in errs:
                print(f"  {e}")
        else:
            print(f"{p}: ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or DEFAULT_CORPUS))
