# Structured Object Definition Language (SODL) Specification

## 1. Overview

### 1.1 Purpose
The Structured Object Definition Language (SODL) is a Domain-Specific Language (DSL) designed for defining canonical data structures, relationships, and constraints within a system. Its primary goal is to provide a single, highly expressive, and type-safe contract for data models, ensuring data integrity from the point of definition through to persistence.

SODL models data objects, relationships, and business rules in a declarative manner, making it ideal for systems where data consistency and clear architectural contracts are paramount.

### 1.2 Scope
This specification covers the syntax and semantics of the SODL language, as defined by the accompanying EBNF grammar. It details how basic types, complex structures, relationships, and constraints are defined and interpreted by the SODL compiler/runtime.

## 2. Syntax (EBNF Grammar)

The following grammar defines the legal structure of a SODL file.

*(The full EBNF grammar is provided in the `sodl.ebnf` file and is referenced here for completeness.)*

**Key Grammar Components:**

*   **Program:** The top-level structure, composed of zero or more `ImportStatement`s followed by zero or more `Declaration`s.
*   **Declaration:** The primary building blocks of the language, including `EnumDecl`, `UnionDecl`, `StructDecl`, `KeyDecl`, `ObjectDecl`, and `KeyMapDecl`.

## 3. Semantics and Constructs

### 3.1 Basic Types and Constraints
SODL supports a rich set of primitive and complex types:

*   **Basic Types:** Includes standard primitives (`string`, `bool`, `uint8` to `uint64`, `float32`, `float64`) and domain-specific types (`UUID`, `Timestamp`, `Money`, `EmailAddress`, etc.).
*   **Complex Types:**
    *   **List (`[Type; IntegerLiteral]`):** Defines a fixed-size array of a specific type.
    *   **TLV (`tlv<Type>`):** Represents variable-length metadata, useful for extensibility.
*   **Type Constraints:** Types can be constrained using:
    *   `range(min, max)`: Enforces numeric boundaries.
    *   `pattern = "regex"`: Enforces string format validation using regular expressions.

### 3.2 Core Declarations

#### A. Enums (`enum`)
Defines a set of named, discrete constants.
*   **Syntax:** `enum Identifier { Value1 = N1, Value2 = N2, ... }`
*   **Semantics:** Values are immutable and typically assigned an integer representation.

#### B. Unions (`union`)
Defines a type that can be one of several specified types.
*   **Syntax:** `union Identifier { TypeA, TypeB, ... }`
*   **Semantics:** The instance of this type must conform to *at least one* of the listed types.

#### C. Structs (`struct`)
Used for grouping related, fixed-schema data fields.
*   **Syntax:** `struct Identifier { field1: Type, field2: Type, ... }`
*   **Semantics:** Defines a composite type. Fields can be marked as `strict` to enforce a literal value.

#### D. Objects (`object`)
The primary entity definition. Objects are the most feature-rich construct, allowing for complex metadata and lifecycle management.
*   **Syntax:** `object Identifier { field1: Type (..., prop1, prop2), ... }`
*   **Semantics:**
    *   **`required`:** The field must be present for a valid object instance.
    *   **`key`:** The field contributes to the object's unique key.
    *   **`assigned`:** Specifies how the value is generated (e.g., `assigned = counter` for auto-incrementing IDs).
    *   **`optional`:** The field may be omitted.

#### E. Keys (`key`)
Defines a unique identifier structure for an object.
*   **Syntax:** `key Identifier { field1: Type (..., props), ... }`
*   **Semantics:** The combination of values for the fields marked as `key` must be unique across all instances of this key.

#### F. KeyMaps (`keymap`)
Defines explicit, named relationships between two key structures.
*   **Syntax:** `keymap SourceKey:TargetKey { sourceField -> targetField }, [primary], [name = "Name"], [cascadeDelete]`
*   **Semantics:** Establishes a foreign-key-like relationship. The `cascadeDelete` property dictates that deleting an instance in the source keymap should automatically delete related instances in the target keymap.

## 4. Usage Examples

### 4.1 Example: User Session Management (From `advanced-examples.sodl`)
This example demonstrates the combination of multiple advanced features:

```sodl
// Defines a complex key for session lookup
key SessionKey {
    sessionId: type = Crypto.SHA256Hash,
    deviceFingerprint: type = string, pattern = "^[a-f0-9]{64}$",
    ipAddress: type = IPAddress
}

// Defines the main object, using the key and complex types
object UserSession {
    sessionId: type = Crypto.SHA256Hash, assigned = random, required, key,
    userId: type = UUID, required, key,
    deviceInfo: {
        userAgent: type = string, required,
        ipAddress: type = IPAddress, required,
        geoLocation: type = GeoLocation, optional,
        deviceFingerprint: type = string, pattern = "^[a-f0-9]{64}$"
    },
    authFactors: type = [AuthenticationFactor; 3], // Array of Union
    securityLevel: type = uint8, range(1, 5),
    lastActivity: type = Timestamp,
    expiresAt: type = Timestamp,
    metadata: type = tlv<string>
}

// Defines the relationship between the two keys
keymap SessionKey:UserSession {
    sessionId -> sessionId,
    deviceFingerprint -> deviceInfo.deviceFingerprint,
    ipAddress -> deviceInfo.ipAddress
}, primary, name = "SessionLookup", cascadeDelete;
```

### 4.2 Example: Data Flow (SODL vs. Parquet)
SODL is best used at the **Application/Service Layer** to define the *intended* data structure and validation rules. This structure can then be mapped and serialized into a physical storage format like Parquet for analytical processing.

**SODL (Definition Layer):**
```sodl
object AnalyticsEvent {
    eventId: type = UUID, assigned = counter, required, key;
    timestamp: type = Timestamp, required;
    userId: type = UUID, required;
    eventType: type = string, required;
    properties: type = tlv<string>;
}
```

**Parquet (Storage Layer):**
*(Schema definition would be handled by a separate tool/process, but the data structure mirrors the SODL intent.)*

## 5. Comparison Summary

| Feature | SODL | Protocol Buffers (protobuf) | JSON Schema |
| :--- | :--- | :--- | :--- |
| **Primary Focus** | Data Model Definition & Relationships | Cross-Language Serialization | General JSON Validation |
| **Relationship Modeling** | **First-class KeyMaps** | Message References | Limited (via `allOf`/`oneOf`) |
| **Validation** | Range, Pattern, Type-Specific | Basic Types | Extensive (but verbose) |
| **Syntax** | Declarative, Object-Oriented | Protocol-based | JSON-based |
| **Best For** | Complex, highly constrained, interconnected data services. | Efficient, language-agnostic data exchange. | Validating arbitrary JSON payloads. |

## 6. Conclusion

SODL provides a powerful, robust, and highly expressive framework for data modeling. Its combination of strong typing, explicit relationship management via `KeyMaps`, and built-in validation constraints makes it superior to general-purpose schema languages for defining the core data contracts of a complex application.