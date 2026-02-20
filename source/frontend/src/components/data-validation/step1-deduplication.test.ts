import { deduplicateEntities } from "./step1-deduplication";
import { EntityForValidation } from "./types";
import { EntitySchema, Attribute } from "../../models";

const createMockSchema = (attributes: Partial<Attribute>[], entityName?: string): EntitySchema => ({
  schema_type: "test",
  schema_name: entityName || "test-schema",
  attributes: attributes.map((attr) => ({
    name: attr.name || "test-attr",
    description: attr.description || "Test attribute",
    type: attr.type || "string",
    required: attr.required || false,
    default: attr.default,
    validation_regex: attr.validation_regex,
    validation_regex_msg: attr.validation_regex_msg,
    rel_entity: attr.rel_entity,
    ...attr,
  })) as Attribute[],
});

const createMockEntityForValidation = (
  entityName: string,
  attributes: Partial<Attribute>[],
  data: Record<string, Record<string, unknown>[]>
): EntityForValidation => ({
  entityName,
  schema: createMockSchema(attributes, entityName),
  data,
});

describe("Step 1: Deduplication", () => {
  it("should merge non-conflicting attributes", () => {
    const entities: EntityForValidation[] = [
      createMockEntityForValidation("application", [{ name: "name", type: "string" }], {
        app1: [{ name: "App One" }, { description: "Test app" }],
      }),
    ];

    const result = deduplicateEntities(entities);

    expect(result.deduplicatedEntities["application"].data["app1"]).toEqual({
      name: "App One",
      description: "Test app",
    });
  });

  it("should create warning and keep first value for required field conflicts", () => {
    const entities: EntityForValidation[] = [
      createMockEntityForValidation("application", [{ name: "name", type: "string", required: true }], {
        app1: [{ name: "App One" }, { name: "App Two" }],
      }),
    ];

    const result = deduplicateEntities(entities);

    expect(result.warnings).toHaveLength(1);
    expect(result.warnings[0].message).toBe("Conflicting values for required attribute 'name': 'App One' vs 'App Two'");
    expect(result.deduplicatedEntities["application"].data["app1"]?.name).toBe("App One");
  });

  it("should create warning and keep first value for optional field conflicts", () => {
    const entities: EntityForValidation[] = [
      createMockEntityForValidation("application", [{ name: "description", type: "string", required: false }], {
        app1: [{ description: "First desc" }, { description: "Second desc" }],
      }),
    ];

    const result = deduplicateEntities(entities);

    expect(result.warnings).toHaveLength(1);
    expect(result.warnings[0].message).toBe(
      "Conflicting values for optional attribute 'description': 'First desc' vs 'Second desc'"
    );
    expect(result.deduplicatedEntities["application"].data["app1"]?.description).toBe("First desc");
  });

  it("should append values for multi-value relationship conflicts", () => {
    const entities: EntityForValidation[] = [
      createMockEntityForValidation(
        "application",
        [{ name: "servers", type: "multivalue-relationship", rel_entity: "server" }],
        {
          app1: [{ servers: ["server1", "server2"] }, { servers: ["server3", "server2"] }],
        }
      ),
    ];

    const result = deduplicateEntities(entities);

    expect(result.warnings).toHaveLength(0);
    expect(result.deduplicatedEntities["application"].data["app1"]?.servers).toEqual(["server1", "server2", "server3"]);
  });

  it("should append values for multi-value relationship with single values", () => {
    const entities: EntityForValidation[] = [
      createMockEntityForValidation(
        "application",
        [{ name: "servers", type: "multivalue-relationship", rel_entity: "server" }],
        {
          app1: [{ servers: "server1" }, { servers: "server2" }],
        }
      ),
    ];

    const result = deduplicateEntities(entities);

    expect(result.warnings).toHaveLength(0);
    expect(result.deduplicatedEntities["application"].data["app1"]?.servers).toEqual(["server1", "server2"]);
  });

  it("should still create warnings for single-value relationship conflicts", () => {
    const entities: EntityForValidation[] = [
      createMockEntityForValidation(
        "server",
        [{ name: "wave", type: "relationship", rel_entity: "wave", required: false }],
        {
          server1: [{ wave: "wave1" }, { wave: "wave2" }],
        }
      ),
    ];

    const result = deduplicateEntities(entities);

    expect(result.warnings).toHaveLength(1);
    expect(result.warnings[0].message).toBe("Conflicting values for optional attribute 'wave': 'wave1' vs 'wave2'");
    expect(result.deduplicatedEntities["server"].data["server1"]?.wave).toBe("wave1");
  });

  it("should handle semicolon-delimited multivalue relationships correctly", () => {
    const entities: EntityForValidation[] = [
      createMockEntityForValidation(
        "application",
        [{ name: "servers", type: "multivalue-relationship", rel_entity: "server" }],
        {
          app1: [{ servers: "server1; server2; server3" }, { servers: "server4; server5" }],
        }
      ),
    ];

    const result = deduplicateEntities(entities);

    expect(result.warnings).toHaveLength(0);
    expect(result.deduplicatedEntities["application"].data["app1"]?.servers).toEqual([
      "server1",
      "server2",
      "server3",
      "server4",
      "server5",
    ]);
  });
});
