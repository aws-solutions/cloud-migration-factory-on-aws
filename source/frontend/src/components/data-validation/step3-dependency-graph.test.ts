import { buildDependencyGraph } from "./step3-dependency-graph";
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

describe("Step 3: Dependency Graph", () => {
  it("should create dependency graph for simple relationships", () => {
    const schemas = [
      createMockSchema(
        [
          {
            name: "server_id",
            type: "string",
            required: true,
            rel_entity: "server",
          },
        ],
        "application"
      ),
      createMockSchema([{ name: "name", type: "string" }], "server"),
    ];

    const result = buildDependencyGraph(schemas);

    expect(result.dependencies["application"]).toEqual(["server"]);
    expect(result.dependencies["server"]).toEqual([]);
  });

  it("should create complex dependency graph with circular references", () => {
    const schemas = [
      createMockSchema(
        [
          { name: "server_id", type: "string", required: true, rel_entity: "server" },
          { name: "database_id", type: "string", required: false, rel_entity: "database" },
        ],
        "application"
      ),
      createMockSchema(
        [
          { name: "name", type: "string" },
          { name: "app_id", type: "string", required: false, rel_entity: "application" },
        ],
        "server"
      ),
      createMockSchema(
        [
          { name: "name", type: "string" },
          { name: "server_id", type: "string", required: true, rel_entity: "server" },
        ],
        "database"
      ),
    ];

    const result = buildDependencyGraph(schemas);

    expect(result.dependencies["application"]).toEqual(["server", "database"]);
    expect(result.dependencies["server"]).toEqual(["application"]);
    expect(result.dependencies["database"]).toEqual(["server"]);
  });

  it("should handle entities with no dependencies", () => {
    const schemas = [createMockSchema([{ name: "name", type: "string", required: true }], "application")];

    const result = buildDependencyGraph(schemas);

    expect(result.dependencies["application"]).toEqual([]);
  });
});
