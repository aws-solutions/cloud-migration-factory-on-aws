import { defaultTestProps } from "../__tests__/TestUtils";
import {
  addImportRowValuesToImportSummaryRecord,
  addRelationshipValueToImportSummaryRecord,
  performValueValidation,
  removeNullKeys,
  performDataValidation,
  isMismatchedItem,
  updateRelatedItemAttributes,
  getRelationshipValueType,
  getSummary,
} from "./import-utils";

test("removeNullKeys removes nulls", () => {
  const result = removeNullKeys([
    {
      server_name: "server1",
      server_os_version: "linux",
    },
    {
      server_name: "server2",
      server_os_version: "",
    },
    {
      server_name: "server3",
      server_os_version: null,
    },
  ]);
  const expected = [
    {
      server_name: "server1",
      server_os_version: "linux",
    },
    {
      server_name: "server2",
    },
    {
      server_name: "server3",
    },
  ];
  expect(result).toEqual(expected);
});

test("performDataValidation with format like unknown: server1", () => {
  const sampleData = [
    {
      unknown: "server1",
    },
  ];
  const result = performDataValidation(defaultTestProps.schemas, sampleData);
  const expectedData = [
    {
      unknown: "server1",
      __import_row: 0,
      __validation: {
        errors: [],
        warnings: [
          {
            attribute: "unknown",
            error: "unknown attribute name not found in any user schema and your data file has provided values.",
          },
        ],
        informational: [],
      },
    },
  ];
  expect(result["schema_names"]).toEqual([]);
  expect(result["data"]).toEqual(expectedData);
});

test("performDataValidation with format like [server]server_name", () => {
  const sampleData = [
    {
      "[server]server_name": "server1",
      "[server]server_os_version": "linux",
    },
  ];
  const result = performDataValidation(defaultTestProps.schemas, sampleData);
  const expectedData = [
    {
      "[server]server_name": "server1",
      "[server]server_os_version": "linux",
      __import_row: 0,
      __validation: {
        errors: [],
        warnings: [],
        informational: [],
      },
    },
  ];
  expect(result["schema_names"]).toEqual(["server"]);
  expect(result["data"]).toEqual(expectedData);
});

test("performDataValidation with format like [server]", () => {
  const sampleData = [
    {
      "[server]": "server1",
    },
  ];
  const result = performDataValidation(defaultTestProps.schemas, sampleData);
  const expectedData = [
    {
      "[server]": "server1",
      __import_row: 0,
      __validation: {
        errors: [],
        warnings: [
          {
            attribute: "[server]",
            error: "[server] attribute name not found in any user schema and your data file has provided values.",
          },
        ],
        informational: [],
      },
    },
  ];
  expect(result["schema_names"]).toEqual([]);
  expect(result["data"]).toEqual(expectedData);
});

test("performDataValidation with format like [server", () => {
  const sampleData = [
    {
      "[server": "server1",
    },
  ];
  const result = performDataValidation(defaultTestProps.schemas, sampleData);
  const expectedData = [
    {
      "[server": "server1",
      __import_row: 0,
      __validation: {
        errors: [],
        informational: [],
        warnings: [
          {
            attribute: "[server",
            error: "[server attribute name not found in any user schema and your data file has provided values.",
          },
        ],
      },
    },
  ];
  expect(result["schema_names"]).toEqual([]);
  expect(result["data"]).toEqual(expectedData);
});

test("performValueValidation null attribute and empty value", () => {
  const attribute: any = {
    attribute: null,
    lookup_attribute_name: "",
  };
  const result = performValueValidation(attribute, "");
  expect(result).toEqual(null);
});

test("performValueValidation attribute with list", () => {
  const attribute = {
    attribute: {
      type: "list",
    },
    schema_name: null,
    lookup_attribute_name: "server",
    import_raw_header: "server",
  };
  const value = "server1;server2";
  const result = performValueValidation(attribute, value);
  expect(result).toEqual(null);
});

test("performValueValidation attribute with list, regex validation failing", () => {
  const attribute = {
    attribute: {
      type: "list",
      validation_regex: "^server.*",
      validation_regex_msg: "Value should start with server",
    },
    schema_name: null,
    lookup_attribute_name: "server",
    import_raw_header: "server",
  };
  const value = "server1;myserver2";
  const result = performValueValidation(attribute, value);
  expect(result).toEqual({ message: "Value should start with server", type: "error" });
});

test("performValueValidation attribute with multivalue string", () => {
  const attribute = {
    attribute: {
      type: "multivalue-string",
    },
    schema_name: null,
    lookup_attribute_name: "server",
    import_raw_header: "server",
  };
  const value = "server1";
  const result = performValueValidation(attribute, value);
  expect(result).toEqual(null);
});

test("performValueValidation attribute with multivalue string, failing validation", () => {
  const attribute = {
    attribute: {
      type: "multivalue-string",
      validation_regex: "^server.*",
      validation_regex_msg: "Value should start with server",
    },
    schema_name: null,
    lookup_attribute_name: "server",
    import_raw_header: "server",
  };
  const value = "myserver;server1";
  const result = performValueValidation(attribute, value);
  expect(result).toEqual({ message: "Value should start with server", type: "error" });
});

test("performValueValidation attribute with valid json", () => {
  const attribute = {
    attribute: {
      type: "json",
    },
    schema_name: null,
    lookup_attribute_name: "server",
    import_raw_header: "server",
  };
  const value = "{}";
  const result = performValueValidation(attribute, value);
  expect(result).toEqual(null);
});

test("performValueValidation attribute with invalid json", () => {
  const attribute = {
    attribute: {
      type: "json",
    },
    schema_name: null,
    lookup_attribute_name: "server",
    import_raw_header: "server",
  };
  const value = "abc";
  const result = performValueValidation(attribute, value);
  expect(result!["type"]).toEqual("error");
  expect(/Invalid JSON/.test(result!["message"])).toEqual(true);
});

test("isMismatchedItem with non existent key", () => {
  const dataArray = [
    {
      wave_name: "Unit testing Wave 1",
    },
  ];
  const checkAttributes = [{}];
  const key = "wave_status";
  const value = "Starting";

  const result = isMismatchedItem(dataArray, checkAttributes, key, value);
  expect(result).toEqual(undefined);
});

test("isMismatchedItem with existing greater than one items", () => {
  const dataArray = [
    {
      wave_name: "Unit testing Wave 1",
    },
    {
      wave_name: "Unit testing Wave 1",
    },
  ];
  const checkAttributes = [
    {
      attribute: {
        system: true,
        validation_regex: "^(?!\\s*$).+",
        name: "wave_name",
        description: "Wave Name",
        validation_regex_msg: "Wave name must be specified.",
        group_order: "-1000",
        type: "string",
        required: true,
      },
      schema_name: "wave",
      lookup_attribute_name: "wave_name",
      lookup_schema_name: "wave",
      import_raw_header: "wave_name",
    },
  ];
  const key = "wave_name";
  const value = "Unit testing wave 1";

  const result = isMismatchedItem(dataArray, checkAttributes, key, value);
  expect(result).toEqual({
    wave_name: "Unit testing Wave 1",
  });
});

test("addImportRowValuesToImportSummaryRecord with attribute type list", () => {
  const schemaName = "wave";
  const attribute = {
    attribute: {
      name: "wave_name",
      type: "list",
      listMultiSelect: true,
    },
    schema_name: "wave",
    lookup_attribute_name: "wave_name",
    lookup_schema_name: "wave",
    import_raw_header: "wave_name",
  };
  const importRow = {
    wave_name: "Wave1;Wave2",
  };
  const importRecord = {
    wave_name: "Unit testing Wave",
  };
  const dataAll = {};
  addImportRowValuesToImportSummaryRecord(schemaName, attribute, importRow, importRecord, dataAll);
  expect(importRecord).toEqual({
    wave_name: ["Wave1", "Wave2"],
  });
});

test("addImportRowValuesToImportSummaryRecord with attribute type multivalue-string", () => {
  const schemaName = "wave";
  const attribute = {
    attribute: {
      name: "wave_name",
      type: "multivalue-string",
      listMultiSelect: true,
    },
    schema_name: "wave",
    lookup_attribute_name: "wave_name",
    lookup_schema_name: "wave",
    import_raw_header: "wave_name",
  };
  const importRow = {
    wave_name: "Wave1;Wave2",
  };
  const importRecord = {
    wave_name: "Unit testing Wave",
  };
  const dataAll = {};
  addImportRowValuesToImportSummaryRecord(schemaName, attribute, importRow, importRecord, dataAll);
  expect(importRecord).toEqual({
    wave_name: ["Wave1", "Wave2"],
  });
});

test("addImportRowValuesToImportSummaryRecord with attribute type tag", () => {
  const schemaName = "wave";
  const attribute = {
    attribute: {
      name: "wave_name",
      type: "tag",
      listMultiSelect: true,
    },
    schema_name: "wave",
    lookup_attribute_name: "wave_name",
    lookup_schema_name: "wave",
    import_raw_header: "wave_name",
  };
  const importRow = {
    wave_name: "tag1=Wave1;tag2=Wave2",
  };
  const importRecord = {
    wave_name: "Unit testing Wave",
  };
  const dataAll = {};
  addImportRowValuesToImportSummaryRecord(schemaName, attribute, importRow, importRecord, dataAll);
  expect(importRecord).toEqual({
    wave_name: [
      {
        key: "tag1",
        value: "Wave1",
      },
      {
        key: "tag2",
        value: "Wave2",
      },
    ],
  });
});

test("addImportRowValuesToImportSummaryRecord with attribute type checkbox", () => {
  const schemaName = "wave";
  const attribute = {
    attribute: {
      name: "wave_name",
      type: "checkbox",
      listMultiSelect: true,
    },
    schema_name: "wave",
    lookup_attribute_name: "wave_name",
    lookup_schema_name: "wave",
    import_raw_header: "wave_name",
  };
  const importRow = {
    wave_name: "on",
  };
  const importRecord = {
    wave_name: "Unit testing Wave",
  };
  const dataAll = {};
  addImportRowValuesToImportSummaryRecord(schemaName, attribute, importRow, importRecord, dataAll);
  expect(importRecord).toEqual({
    wave_name: true,
  });
});

test("addRelationshipValueToImportSummaryRecord with attributes, one new and one update", () => {
  const importedAttribute = {
    attribute: {
      listMultiSelect: true,
      system: true,
      rel_display_attribute: "wave_name",
      rel_key: "wave_id",
      name: "wave_id",
      description: "Wave Id",
      rel_entity: "wave",
      group_order: "-999",
      type: "relationship",
      required: false,
    },
    schema_name: "application",
    lookup_attribute_name: "wave_name",
    lookup_schema_name: "application",
    import_raw_header: "wave_name",
  };
  const schemaName = "application";
  const importRow = {
    app_name: "Unit testing App 1",
    aws_accountid: "123456789012",
    aws_region: "us-east-2",
    wave_name: "Unit testing Wave 0;Wave2",
  };
  const importSummaryRecord = {
    app_name: "Unit testing App 1",
    aws_accountid: "123456789012",
    aws_region: "us-east-2",
  };
  const dataAll = {
    wave: {
      data: [
        {
          wave_id: "0",
          wave_name: "Unit testing Wave 0",
        },
      ],
    },
  };
  addRelationshipValueToImportSummaryRecord(importedAttribute, schemaName, importRow, importSummaryRecord, dataAll);
  expect(importSummaryRecord).toEqual({
    app_name: "Unit testing App 1",
    aws_accountid: "123456789012",
    aws_region: "us-east-2",
    wave_id: ["0", "tbc"],
    __wave_id: ["Unit testing Wave 0", "Wave2"],
  });
});

test("updateRelatedItemAttributes - Invalid new_item_schema_name", () => {
  const schemas = defaultTestProps.schemas;
  const newItem = {
    wave_name: "Unittest Wave 1",
    wave_id: "101",
  };
  const newItemSchemaName = "wave-INVALID";
  const relatedItems: any[] = [];
  const relatedSchemaName = "database";
  updateRelatedItemAttributes(schemas, newItem, newItemSchemaName, relatedItems, relatedSchemaName);
  expect(relatedItems).toEqual([]);
});

test("updateRelatedItemAttributes - Invalid related_schema_name", () => {
  const schemas = defaultTestProps.schemas;
  const newItem = {
    wave_name: "Unittest Wave 1",
    wave_id: "101",
  };
  const newItemSchemaName = "wave";
  const relatedItems: any[] = [];
  const relatedSchemaName = "database-INVALID";
  updateRelatedItemAttributes(schemas, newItem, newItemSchemaName, relatedItems, relatedSchemaName);
  expect(relatedItems).toEqual([]);
});

test("updateRelatedItemAttributes - No related_items to update in items:", () => {
  const schemas = defaultTestProps.schemas;
  const newItem = {
    wave_name: "Unittest Wave 1",
    wave_id: "101",
  };
  const newItemSchemaName = "wave";
  const relatedItems: any[] = [];
  const relatedSchemaName = "database";
  updateRelatedItemAttributes(schemas, newItem, newItemSchemaName, relatedItems, relatedSchemaName);
  expect(relatedItems).toEqual([]);
});

test("updateRelatedItemAttributes - No new item to reference.", () => {
  const schemas = defaultTestProps.schemas;
  const newItem = null;
  const newItemSchemaName = "wave";
  const relatedItems = [
    {
      wave_name: "Unittest Wave 1",
      wave_id: "101",
    },
  ];
  const relatedSchemaName = "database";
  updateRelatedItemAttributes(schemas, newItem, newItemSchemaName, relatedItems, relatedSchemaName);
  expect(relatedItems).toEqual([
    {
      wave_name: "Unittest Wave 1",
      wave_id: "101",
    },
  ]);
});

test("updateRelatedItemAttributes - update items success", () => {
  const schemas = defaultTestProps.schemas;
  const newItem = {
    app_name: "app1",
    aws_accountid: "123456789012",
    aws_region: "us-east-1",
    wave_id: "101",
    app_id: "101",
  };
  const newItemSchemaName = "application";
  const relatedItems = [
    {
      server_name: "unittest1-NEW",
      server_os_family: "linux",
      server_os_version: "redhat",
      server_fqdn: "unittest1.testdomain.local",
      r_type: "Rehost",
      app_id: "tbc",
      __app_id: "Unit testing App 1-NEW",
    },
    {
      all_applications: ["tbc", "something else"],
      __all_applications: ["app1", "app2"],
    },
  ];
  const relatedSchemaName = "server";
  updateRelatedItemAttributes(schemas, newItem, newItemSchemaName, relatedItems, relatedSchemaName);
  expect(relatedItems).toEqual([
    {
      server_name: "unittest1-NEW",
      server_os_family: "linux",
      server_os_version: "redhat",
      server_fqdn: "unittest1.testdomain.local",
      r_type: "Rehost",
      app_id: "tbc",
      __app_id: "Unit testing App 1-NEW",
    },
    {
      all_applications: ["101", "something else"],
      __all_applications: ["app1", "app2"],
    },
  ]);
});

test("getRelationshipValueType - different scenarios", () => {
  let importedAttribute: {
    import_raw_header: string;
    attribute: { rel_display_attribute: string; name: string; listMultiSelect: any };
  } = {
    attribute: {
      rel_display_attribute: "wave_name",
      listMultiSelect: false,
      name: "",
    },
    import_raw_header: "[application]wave_name",
  };
  const schemaName = "application";
  let result = getRelationshipValueType(importedAttribute, schemaName);
  expect(result).toEqual("name");

  importedAttribute = {
    attribute: {
      rel_display_attribute: "wave_name",
      listMultiSelect: false,
      name: "",
    },
    import_raw_header: "wave_name",
  };
  result = getRelationshipValueType(importedAttribute, schemaName);
  expect(result).toEqual("name");

  importedAttribute = {
    attribute: {
      rel_display_attribute: "wave_name_not_matching",
      name: "wave_name",
      listMultiSelect: true,
    },
    import_raw_header: "wave_name",
  };
  result = getRelationshipValueType(importedAttribute, schemaName);
  expect(result).toEqual("name");

  importedAttribute = {
    attribute: {
      rel_display_attribute: "wave_name_not_matching",
      name: "wave_name",
      listMultiSelect: true,
    },
    import_raw_header: "[application]wave_name",
  };
  result = getRelationshipValueType(importedAttribute, schemaName);
  expect(result).toEqual("name");

  importedAttribute = {
    attribute: {
      rel_display_attribute: "wave_name_not_matching",
      name: "wave_name",
      listMultiSelect: false,
    },
    import_raw_header: "wave_name",
  };
  result = getRelationshipValueType(importedAttribute, schemaName);
  expect(result).toEqual("id");

  importedAttribute = {
    attribute: {
      rel_display_attribute: "wave_name_not_matching",
      name: "wave_name",
      listMultiSelect: false,
    },
    import_raw_header: "[application]wave_name",
  };
  result = getRelationshipValueType(importedAttribute, schemaName);
  expect(result).toEqual("id");
});

test("getSummary - different scenarios", () => {
  const schemas = defaultTestProps.schemas;
  const dataJson = {
    data: [
      {
        server_name: "unittest1",
        server_os_family: "linux",
        server_os_version: "redhat",
        server_fqdn: "unittest1.testdomain.local",
        r_type: "Rehost",
        app_name: "Unit testing App 1",
        aws_accountid: "123456789012",
        aws_region: "us-east-2",
        wave_name: "Unit testing Wave 1",
        __import_row: 0,
        __validation: {
          errors: [],
          warnings: [],
          informational: [
            {
              attribute: "app_name",
              error:
                "Ambiguous attribute name provided. It is found in multiple schemas [database, application, server]. Import will map data to schemas as required based on record types.",
            },
            {
              attribute: "wave_name",
              error:
                "Ambiguous attribute name provided. It is found in multiple schemas [wave, application]. Import will map data to schemas as required based on record types.",
            },
          ],
        },
      },
    ],
    attributeMappings: [
      {
        attribute: {
          system: true,
          validation_regex:
            "^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\\-]*[a-zA-Z0-9])\\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\\-]*[A-Za-z0-9])$",
          name: "server_name",
          description: "Server Name",
          validation_regex_msg: "Server names must contain only alphanumeric, hyphen or period characters.",
          group_order: "-1000",
          type: "string",
          required: true,
        },
        schema_name: "server",
        lookup_attribute_name: "server_name",
        lookup_schema_name: "server",
        import_raw_header: "server_name",
      },
      {
        attribute: {
          system: true,
          validation_regex: "^(?!\\s*$).+",
          listvalue: "windows,linux",
          name: "server_os_family",
          description: "Server OS Family",
          validation_regex_msg: "Select a valid operating system.",
          type: "list",
          required: true,
        },
        schema_name: "server",
        lookup_attribute_name: "server_os_family",
        lookup_schema_name: "server",
        import_raw_header: "server_os_family",
      },
      {
        attribute: {
          name: "server_os_version",
          description: "Server OS Version",
          system: true,
          type: "string",
          required: true,
        },
        schema_name: "server",
        lookup_attribute_name: "server_os_version",
        lookup_schema_name: "server",
        import_raw_header: "server_os_version",
      },
      {
        attribute: {
          system: true,
          validation_regex:
            "^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\\-]*[a-zA-Z0-9])\\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\\-]*[A-Za-z0-9])$",
          name: "server_fqdn",
          description: "Server FQDN",
          validation_regex_msg: "Server FQDN must contain only alphanumeric, hyphen or period charaters.",
          group_order: "-999",
          type: "string",
          required: true,
        },
        schema_name: "server",
        lookup_attribute_name: "server_fqdn",
        lookup_schema_name: "server",
        import_raw_header: "server_fqdn",
      },
      {
        attribute: {
          schema: "server",
          system: true,
          help_content: {
            header: "Migration Strategy",
            content_html:
              "The following Migration Strategies are commonly used in Cloud Migration projects.  The AWS Cloud Migration factory solution supports the automation activities to assist with these strategies, for Rehost and Replatform prepackaged automations are provided, and for other strategies customized automations can be created and imported into the AWS CMF solution:\n<ul>\n<li><b>Retire</b> - Server retired and not migrated, data will need to be removed and any software services decommissioned.</li>\n<li><b>Retain</b> - Server will remain on-premise , assessment should be preformed to verify any changes for migrating dependent services.</li>\n<li><b>Relocate</b> - VMware virtual machine on-premise, is due to be relocated to VMware Cloud on AWS, using VMware HCX. Currently AWS CMF does not natively support this capability, although custom automation script packages coudl be used to interface with this service.</li>\n<li><b>Rehost</b> - AWS Cloud Migration Factory supports native integration with AWS MGN, selecting this strategy will enable the options in the server UI to support specifying the required parameters to migrate a server instance to EC2 using block level replication. The AWS CMF Solution comes packaged will all the required automation scripts to support the standard tasks required to migrate a server, all of which can be initiated from the CMF web interface.</li>\n<li><b>Repurchase</b> - Service that the server is currently supporting will be replaced with another service.</li>\n<li><b>Replatform</b> - AWS Cloud Migration Factory supports native integration to create Cloud Formation templates for each application in a wave, these Cloud Formation template are automatically generated through the UI based on the properties of the servers defined here, and can then be deployed to any account that has had the target AWS CMF Solution CFT deployed.</li>\n<li><b>Reachitect</b> - Service will be rebuilt from other services in the AWS Cloud.</li>\n</ul>\n",
          },
          listvalue: "Retire,Retain,Relocate,Rehost,Repurchase,Replatform,Reachitect,TBC,Replatform - A2C",
          name: "r_type",
          description: "Migration Strategy",
          type: "list",
          required: true,
        },
        schema_name: "server",
        lookup_attribute_name: "r_type",
        lookup_schema_name: "server",
        import_raw_header: "r_type",
      },
      {
        attribute: {
          rel_display_attribute: "app_name",
          system: true,
          rel_key: "app_id",
          name: "app_id",
          description: "Application",
          rel_entity: "application",
          group_order: "-998",
          type: "relationship",
          required: true,
        },
        schema_name: "database",
        lookup_attribute_name: "app_name",
        lookup_schema_name: "database",
        import_raw_header: "app_name",
      },
      {
        attribute: {
          system: true,
          validation_regex: "^(?!\\s*$).+",
          name: "app_name",
          description: "Application Name",
          validation_regex_msg: "Application name must be specified.",
          group_order: "-1000",
          type: "string",
          required: true,
        },
        schema_name: "application",
        lookup_attribute_name: "app_name",
        lookup_schema_name: "application",
        import_raw_header: "app_name",
      },
      {
        attribute: {
          rel_display_attribute: "app_name",
          system: true,
          rel_key: "app_id",
          name: "app_id",
          description: "Application",
          rel_entity: "application",
          group_order: "-998",
          type: "relationship",
          required: true,
        },
        schema_name: "server",
        lookup_attribute_name: "app_name",
        lookup_schema_name: "server",
        import_raw_header: "app_name",
      },
      {
        attribute: {
          schema: "application",
          system: true,
          validation_regex: "^\\d{12}$",
          listvalue: "123456789012,111122223333",
          name: "aws_accountid",
          description: "AWS Account Id",
          validation_regex_msg: "Invalid AWS account Id.",
          type: "list",
          required: true,
          group: "Target",
        },
        schema_name: "application",
        lookup_attribute_name: "aws_accountid",
        lookup_schema_name: "application",
        import_raw_header: "aws_accountid",
      },
      {
        attribute: {
          system: true,
          listvalue:
            "us-east-2,us-east-1,us-west-1,us-west-2,af-south-1,ap-east-1,ap-southeast-3,ap-south-1,ap-northeast-3,ap-northeast-2,ap-southeast-1,ap-southeast-2,ap-northeast-1,ca-central-1,cn-north-1,cn-northwest-1,eu-central-1,eu-west-1,eu-west-2,eu-south-1,eu-west-3,eu-north-1,me-south-1,sa-east-1",
          name: "aws_region",
          description: "AWS Region",
          type: "list",
          required: true,
          group: "Target",
        },
        schema_name: "application",
        lookup_attribute_name: "aws_region",
        lookup_schema_name: "application",
        import_raw_header: "aws_region",
      },
      {
        attribute: {
          system: true,
          validation_regex: "^(?!\\s*$).+",
          name: "wave_name",
          description: "Wave Name",
          validation_regex_msg: "Wave name must be specified.",
          group_order: "-1000",
          type: "string",
          required: true,
        },
        schema_name: "wave",
        lookup_attribute_name: "wave_name",
        lookup_schema_name: "wave",
        import_raw_header: "wave_name",
      },
      {
        attribute: {
          system: true,
          rel_display_attribute: "wave_name",
          rel_key: "wave_id",
          name: "wave_id",
          description: "Wave Id",
          rel_entity: "wave",
          group_order: "-999",
          type: "relationship",
          required: false,
        },
        schema_name: "application",
        lookup_attribute_name: "wave_name",
        lookup_schema_name: "application",
        import_raw_header: "wave_name",
      },
    ],
    schema_names: ["server", "database", "application", "wave"],
  };

  //scenario: no exiting data
  const dataAllNoExisting = {
    server: {
      data: [],
    },
    application: {
      data: [],
    },
    wave: {
      data: [],
    },
  };
  let response = getSummary(schemas, dataJson, dataAllNoExisting);
  const notUpdatedEntities = {
    Create: [],
    Update: [],
    NoChange: [],
  };
  const createNeededEntities = {
    Create: [expect.any(Object)],
    Update: [],
    NoChange: [],
  };
  const updateNeededEntities = {
    Create: [],
    Update: [expect.any(Object)],
    NoChange: [],
  };
  const noChangeNeededEntities = {
    Create: [],
    Update: [],
    NoChange: [expect.any(Object)],
  };
  expect(response["entities"]["database"]).toEqual(notUpdatedEntities);
  expect(response["entities"]["template"]).toEqual(notUpdatedEntities);
  expect(response["entities"]["pipeline"]).toEqual(notUpdatedEntities);

  expect(response["entities"]["wave"]).toEqual(expect.objectContaining(createNeededEntities));
  expect(response["entities"]["application"]).toEqual(expect.objectContaining(createNeededEntities));
  expect(response["entities"]["server"]).toEqual(expect.objectContaining(createNeededEntities));

  // scenario: app existing
  const dataAllAppExisting = {
    server: {
      data: [],
    },
    application: {
      data: [
        {
          app_id: "0",
          app_name: "Unit testing App 1",
        },
      ],
    },
    wave: {
      data: [],
    },
  };
  response = getSummary(schemas, dataJson, dataAllAppExisting);
  expect(response["entities"]["database"]).toEqual(notUpdatedEntities);
  expect(response["entities"]["template"]).toEqual(notUpdatedEntities);
  expect(response["entities"]["pipeline"]).toEqual(notUpdatedEntities);
  expect(response["entities"]["wave"]).toEqual(expect.objectContaining(createNeededEntities));
  expect(response["entities"]["application"]).toEqual(expect.objectContaining(updateNeededEntities));
  expect(response["entities"]["server"]).toEqual(expect.objectContaining(createNeededEntities));

  // scenario: app and wave existing
  const dataAllAppAndWaveExisting = {
    server: {
      data: [],
    },
    application: {
      data: [
        {
          app_id: "0",
          app_name: "Unit testing App 1",
        },
      ],
    },
    wave: {
      data: [
        {
          wave_id: "0",
          wave_name: "Unit testing Wave 1",
        },
      ],
    },
  };
  response = getSummary(schemas, dataJson, dataAllAppAndWaveExisting);
  expect(response["entities"]["database"]).toEqual(notUpdatedEntities);
  expect(response["entities"]["template"]).toEqual(notUpdatedEntities);
  expect(response["entities"]["pipeline"]).toEqual(notUpdatedEntities);
  expect(response["entities"]["wave"]).toEqual(expect.objectContaining(noChangeNeededEntities));
  expect(response["entities"]["application"]).toEqual(expect.objectContaining(updateNeededEntities));
  expect(response["entities"]["server"]).toEqual(expect.objectContaining(createNeededEntities));

  // scenario: app, wave and server existing
  const dataAllAppWaveServerExisting = {
    server: {
      data: [
        {
          server_id: "0",
          server_name: "unittest1",
        },
      ],
    },
    application: {
      data: [
        {
          app_id: "0",
          app_name: "Unit testing App 1",
        },
      ],
    },
    wave: {
      data: [
        {
          wave_id: "0",
          wave_name: "Unit testing Wave 1",
        },
      ],
    },
  };
  response = getSummary(schemas, dataJson, dataAllAppWaveServerExisting);
  expect(response["entities"]["database"]).toEqual(notUpdatedEntities);
  expect(response["entities"]["template"]).toEqual(notUpdatedEntities);
  expect(response["entities"]["pipeline"]).toEqual(notUpdatedEntities);
  expect(response["entities"]["wave"]).toEqual(expect.objectContaining(noChangeNeededEntities));
  expect(response["entities"]["application"]).toEqual(expect.objectContaining(updateNeededEntities));
  expect(response["entities"]["server"]).toEqual(expect.objectContaining(updateNeededEntities));
});
