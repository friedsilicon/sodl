#!/usr/bin/env python3
"""Static checks for SODL sources.

The EBNF in sodl.ebnf defines what parses. It cannot express the rules
that make a schema coherent -- those live here. See DECISIONS.md (D6, D7)
and the STATIC CHECKS block at the foot of sodl.ebnf.

This is a lint over the concrete syntax, not a parser: it reads the
constructs by regex. It exists to keep the example files honest about the
rules the language claims. A real front end would do this on the AST.

Usage: ./check-sodl.py FILE...   (exit 1 if any check fails)
"""

import re
import sys

BASIC_TYPES = {
    "uint8", "uint16", "uint32", "uint64",
    "int8", "int16", "int32", "int64",
    "float32", "float64",
    "string", "bool", "bytes", "Timestamp",
}

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
                errs.append(f"const {name}: `{val}` is not an integer literal for `{ty}`")
                continue
            lo, hi = INT_RANGES[ty]
            if not lo <= n <= hi:
                errs.append(f"const {name}: {val} out of range for `{ty}` [{lo}, {hi}]")
            decls[name] = "number"
        elif ty in FLOAT_TYPES:
            if not re.fullmatch(r"-?[0-9]+(\.[0-9]+)?", val):
                errs.append(f"const {name}: `{val}` is not a numeric literal for `{ty}`")
            decls[name] = "number"
        elif ty == "string":
            if not re.fullmatch(r'"[^"]*"', val):
                errs.append(f"const {name}: `{val}` is not a string literal")
            decls[name] = "other"
        elif ty == "bool":
            if val not in ("true", "false"):
                errs.append(f"const {name}: `{val}` is not a bool literal")
            decls[name] = "other"
        elif ty in ("bytes", "Timestamp"):
            errs.append(f"const {name}: `{ty}` has no literal form (D10)")
            decls[name] = "other"
        else:
            errs.append(f"const {name}: type `{ty}` is not a basic type (D10)")
            decls[name] = "other"
    return errs, decls


def blocks(src, kw):
    """Yield (name, body) for each `kw Name { ... }` declaration."""
    for m in re.finditer(rf"^{kw} (\w+)[^{{]*\{{(.*?)^\}}", src, re.S | re.M):
        yield m.group(1), m.group(2)


def fields(body):
    """Yield (name, props_text) per field line: `name: Type, props;`."""
    for line in body.splitlines():
        line = re.sub(r"//.*", "", line)
        m = re.match(r"\s*(\w+)\s*:\s*(.*?);\s*$", line)
        if m:
            yield m.group(1), m.group(2)


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
                    errs.append(f"range bound `{op}` names no declared const (D10)")
                elif const_decls[op] != "number":
                    errs.append(f"range bound `{op}` is not a numeric const (D10)")

    objects = {n: dict(fields(b)) for n, b in blocks(src, "object")}
    keydecls = {n: dict(fields(b)) for n, b in blocks(src, "key")}

    keymaps = []  # (srckey, target, {lhs -> rhs})
    for m in re.finditer(r"^keymap (\w+):(\w+)\s*\{(.*?)^\}", src, re.S | re.M):
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
                    f"{obj}.{f}: `required` is redundant on a key field "
                    f"(D6 rule 1: key implies required)"
                )

    # --- D6 rule 3: every object needs at least one key field.
    for obj in objects:
        if not keyed[obj]:
            errs.append(f"{obj}: no `key` field (D6 rule 3: every object needs one)")

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
            errs.append(f"{obj}.{f}: key field named by no `key` declaration (D6 rule 2)")
        for f in sorted(kfields - by_keymap):
            errs.append(f"{obj}.{f}: key field used by no `keymap` (D6 rule 2)")

    # --- D6: a key/keymap may only reference `key`-annotated fields.
    for srckey, tgt, pairs in keymaps:
        if tgt not in objects:
            errs.append(f"keymap {srckey}:{tgt}: target object `{tgt}` not declared")
            continue
        for lhs in pairs:
            if lhs in objects[tgt] and lhs not in keyed[tgt]:
                errs.append(
                    f"keymap {srckey}:{tgt}: `{lhs}` referenced but not "
                    f"annotated `key` on {tgt}"
                )

    # --- defect 17: keymaps must reference declared keys.
    for srckey, tgt, _ in keymaps:
        if srckey not in keydecls:
            errs.append(f"keymap {srckey}:{tgt}: source key `{srckey}` not declared")

    # --- defect 19: importing a name that collides with a BasicType.
    for m in re.finditer(r"^import\s*\{([^}]*)\}", src, re.M):
        for name in (n.strip() for n in m.group(1).split(",")):
            if name in BASIC_TYPES:
                errs.append(f"import: `{name}` collides with a BasicType (static check 5)")

    # --- D11 (static check 7): alias chains must terminate; no cycles.
    # An alias's RHS head token is another alias iff it names one; those are
    # the only edges that can form a cycle. Chase each chain and flag a loop.
    aliases = dict(re.findall(r"^alias\s+(\w+)\s*=\s*(\w+)", src, re.M))
    for start in aliases:
        seen, cur = [], start
        while cur in aliases:
            if cur in seen:
                loop = " -> ".join(seen[seen.index(cur):] + [cur])
                errs.append(f"alias `{start}`: cycle {loop} (static check 7)")
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
    sys.exit(main(sys.argv[1:] or ["example.sodl", "advanced-examples.sodl"]))
