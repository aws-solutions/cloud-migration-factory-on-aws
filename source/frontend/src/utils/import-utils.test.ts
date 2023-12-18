import * as ImportUtils from "./import-utils";
import {defaultTestProps} from "../__tests__/TestUtils";
import {
    addImportRowValuesToImportSummaryRecord,
    addRelationshipValueToImportSummaryRecord,
    performValueValidation
} from "./import-utils";

test("removeNullKeys removes nulls", () => {
    const result = ImportUtils.removeNullKeys([
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
    ]
    expect(result).toEqual(expected);
});

test("performDataValidation with format like unknown: server1", () => {
    const sampleData = [
        {
            "unknown": "server1",
        }
    ];
    const result = ImportUtils.performDataValidation(defaultTestProps.schemas, sampleData);
    const expectedData = [
        {
            "unknown": "server1",
            "__import_row": 0,
            "__validation": {
                "errors": [],
                "warnings": [
                    {
                        "attribute": "unknown",
                        "error": "unknown attribute name not found in any user schema and your data file has provided values."
                    }
                ],
                "informational": []
            }
        }
    ];
    expect(result["schema_names"]).toEqual([]);
    expect(result["data"]).toEqual(expectedData);
});

test("performDataValidation with format like [server]server_name", () => {
    const sampleData = [
        {
            "[server]server_name": "server1",
            "[server]server_os_version": "linux",
        }
    ];
    const result = ImportUtils.performDataValidation(defaultTestProps.schemas, sampleData);
    const expectedData = [
        {
            "[server]server_name": "server1",
            "[server]server_os_version": "linux",
            "__import_row": 0,
            "__validation": {
                "errors": [],
                "warnings": [],
                "informational": []
            }
        }
    ];
    expect(result["schema_names"]).toEqual(["server"]);
    expect(result["data"]).toEqual(expectedData);
});

test("performDataValidation with format like [server]", () => {
    const sampleData = [
        {
            "[server]": "server1",
        }
    ];
    const result = ImportUtils.performDataValidation(defaultTestProps.schemas, sampleData);
    const expectedData = [
        {
            "[server]": "server1",
            "__import_row": 0,
            "__validation": {
                "errors": [],
                "warnings": [
                    {
                        "attribute": "[server]",
                        "error": "[server] attribute name not found in any user schema and your data file has provided values."
                    }
                ],
                "informational": []
            }
        }
    ];
    expect(result["schema_names"]).toEqual([]);
    expect(result["data"]).toEqual(expectedData);
});

test("performDataValidation with format like [server", () => {
    const sampleData = [
        {
            "[server": "server1",
        }
    ];
    const result = ImportUtils.performDataValidation(defaultTestProps.schemas, sampleData);
    const expectedData = [
        {
            "[server": "server1",
            "__import_row": 0,
            "__validation": {
                "errors": [],
                "informational": [],
                "warnings": [
                    {
                        "attribute": "[server",
                        "error": "[server attribute name not found in any user schema and your data file has provided values."
                    }
                ]
            }
        }
    ];
    expect(result["schema_names"]).toEqual([]);
    expect(result["data"]).toEqual(expectedData);
});

test("performValueValidation null attribute and empty value", () => {
    const attribute: any = {
        "attribute": null,
        "lookup_attribute_name": "",
    };
    const result = performValueValidation(attribute, "");
    expect(result).toEqual(null);
});

test("performValueValidation attribute with multivalue string", () => {
    const attribute = {
        "attribute": {
            type: "multivalue-string",
        },
        "schema_name": null,
        "lookup_attribute_name": "server",
        "import_raw_header": "server",
    };
    const value = "server1";
    const result = performValueValidation(attribute, value);
    expect(result).toEqual(null);
});

test("performValueValidation attribute with valid json", () => {
    const attribute = {
        "attribute": {
            type: "json",
        },
        "schema_name": null,
        "lookup_attribute_name": "server",
        "import_raw_header": "server",
    };
    const value = "{}";
    const result = performValueValidation(attribute, value);
    expect(result).toEqual(null);
});

test("performValueValidation attribute with invalid json", () => {
    const attribute = {
        "attribute": {
            type: "json",
        },
        "schema_name": null,
        "lookup_attribute_name": "server",
        "import_raw_header": "server",
    };
    const value = "abc";
    const result = performValueValidation(attribute, value);
    expect(result!["type"]).toEqual("error");
    expect(/Invalid JSON/.test(result!["message"])).toEqual(true);
});

test("isMismatchedItem with non existent key", () => {
    const dataArray = [
        {
            "wave_name": "Unit testing Wave 1",
        }
    ];
    const checkAttributes = [{}];
    const key = "wave_status";
    const value = "Starting";

    const result = ImportUtils.isMismatchedItem(dataArray, checkAttributes, key, value);
    expect(result).toEqual(undefined);
});

test("isMismatchedItem with existing greater than one items", () => {
    const dataArray = [
        {
            "wave_name": "Unit testing Wave 1",
        },
        {
            "wave_name": "Unit testing Wave 1",
        }
    ];
    const checkAttributes = [
        {
            "attribute": {
                "system": true,
                "validation_regex": "^(?!\\s*$).+",
                "name": "wave_name",
                "description": "Wave Name",
                "validation_regex_msg": "Wave name must be specified.",
                "group_order": "-1000",
                "type": "string",
                "required": true
            },
            "schema_name": "wave",
            "lookup_attribute_name": "wave_name",
            "lookup_schema_name": "wave",
            "import_raw_header": "wave_name"
        }
    ];
    const key = "wave_name";
    const value = "Unit testing wave 1";

    const result = ImportUtils.isMismatchedItem(dataArray, checkAttributes, key, value);
    expect(result).toEqual({
        "wave_name": "Unit testing Wave 1"
    });
});

test("addImportRowValuesToImportSummaryRecord with attribute type list", () => {
    const schemaName = "wave";
    const attribute = {
        "attribute": {
            "name": "wave_name",
            "type": "list",
            "listMultiSelect": true,
        },
        "schema_name": "wave",
        "lookup_attribute_name": "wave_name",
        "lookup_schema_name": "wave",
        "import_raw_header": "wave_name"
    };
    const importRow = {
        "wave_name": "Wave1;Wave2",
    };
    const importRecord = {
        "wave_name": "Unit testing Wave"
    };
    const dataAll = {};
    addImportRowValuesToImportSummaryRecord(schemaName, attribute, importRow, importRecord, dataAll);
    expect(importRecord).toEqual({
        "wave_name": [
            "Wave1",
            "Wave2"
        ]
    });
});

test("addImportRowValuesToImportSummaryRecord with attribute type multivalue-string", () => {
    const schemaName = "wave";
    const attribute = {
        "attribute": {
            "name": "wave_name",
            "type": "multivalue-string",
            "listMultiSelect": true,
        },
        "schema_name": "wave",
        "lookup_attribute_name": "wave_name",
        "lookup_schema_name": "wave",
        "import_raw_header": "wave_name"
    };
    const importRow = {
        "wave_name": "Wave1;Wave2",
    };
    const importRecord = {
        "wave_name": "Unit testing Wave"
    };
    const dataAll = {};
    addImportRowValuesToImportSummaryRecord(schemaName, attribute, importRow, importRecord, dataAll);
    expect(importRecord).toEqual({
        "wave_name": [
            "Wave1",
            "Wave2"
        ]
    });
});

test("addImportRowValuesToImportSummaryRecord with attribute type tag", () => {
    const schemaName = "wave";
    const attribute = {
        "attribute": {
            "name": "wave_name",
            "type": "tag",
            "listMultiSelect": true,
        },
        "schema_name": "wave",
        "lookup_attribute_name": "wave_name",
        "lookup_schema_name": "wave",
        "import_raw_header": "wave_name"
    };
    const importRow = {
        "wave_name": "tag1=Wave1;tag2=Wave2",
    };
    const importRecord = {
        "wave_name": "Unit testing Wave"
    };
    const dataAll = {};
    addImportRowValuesToImportSummaryRecord(schemaName, attribute, importRow, importRecord, dataAll);
    expect(importRecord).toEqual({
        "wave_name": [
            {
                "key": "tag1",
                "value": "Wave1"
            },
            {
                "key": "tag2",
                "value": "Wave2"
            }
        ]
    });
});

test("addImportRowValuesToImportSummaryRecord with attribute type checkbox", () => {
    const schemaName = "wave";
    const attribute = {
        "attribute": {
            "name": "wave_name",
            "type": "checkbox",
            "listMultiSelect": true,
        },
        "schema_name": "wave",
        "lookup_attribute_name": "wave_name",
        "lookup_schema_name": "wave",
        "import_raw_header": "wave_name"
    };
    const importRow = {
        "wave_name": "on",
    };
    const importRecord = {
        "wave_name": "Unit testing Wave"
    };
    const dataAll = {};
    addImportRowValuesToImportSummaryRecord(schemaName, attribute, importRow, importRecord, dataAll);
    expect(importRecord).toEqual({
        "wave_name": true
    });
});

test("addRelationshipValueToImportSummaryRecord with attributes, one new and one update", () => {
    const importedAttribute = {
        "attribute": {
            "listMultiSelect": true,
            "system": true,
            "rel_display_attribute": "wave_name",
            "rel_key": "wave_id",
            "name": "wave_id",
            "description": "Wave Id",
            "rel_entity": "wave",
            "group_order": "-999",
            "type": "relationship",
            "required": false
        },
        "schema_name": "application",
        "lookup_attribute_name": "wave_name",
        "lookup_schema_name": "application",
        "import_raw_header": "wave_name"
    };
    const schemaName = "application";
    const importRow = {
        "app_name": "Unit testing App 1",
        "aws_accountid": "123456789012",
        "aws_region": "us-east-2",
        "wave_name": "Unit testing Wave 0;Wave2",
    };
    const importSummaryRecord = {
        "app_name": "Unit testing App 1",
        "aws_accountid": "123456789012",
        "aws_region": "us-east-2"
    };
    const dataAll = {
        "wave": {
            "data": [
                {
                    "wave_id": "0",
                    "wave_name": "Unit testing Wave 0",
                },
            ],
        }
    };
    addRelationshipValueToImportSummaryRecord(importedAttribute, schemaName, importRow, importSummaryRecord, dataAll);
    expect(importSummaryRecord).toEqual({
        "app_name": "Unit testing App 1",
        "aws_accountid": "123456789012",
        "aws_region": "us-east-2",
        "wave_id": [
            "0",
            "tbc"
        ],
        "__wave_id": [
            "Unit testing Wave 0",
            "Wave2"
        ]
    });
});

test("updateRelatedItemAttributes - Invalid new_item_schema_name", () => {
    const schemas = defaultTestProps.schemas;
    const newItem = {
        "wave_name": "Unittest Wave 1",
        "wave_id": "101",
    };
    const newItemSchemaName = "wave-INVALID";
    const relatedItems: any[] = [];
    const relatedSchemaName = "database";
    ImportUtils.updateRelatedItemAttributes(schemas, newItem, newItemSchemaName, relatedItems, relatedSchemaName);
    expect(relatedItems).toEqual([]);
});

test("updateRelatedItemAttributes - Invalid related_schema_name", () => {
    const schemas = defaultTestProps.schemas;
    const newItem = {
        "wave_name": "Unittest Wave 1",
        "wave_id": "101",
    };
    const newItemSchemaName = "wave";
    const relatedItems: any[] = [];
    const relatedSchemaName = "database-INVALID";
    ImportUtils.updateRelatedItemAttributes(schemas, newItem, newItemSchemaName, relatedItems, relatedSchemaName);
    expect(relatedItems).toEqual([]);
});

test("updateRelatedItemAttributes - No related_items to update in items:", () => {
    const schemas = defaultTestProps.schemas;
    const newItem = {
        "wave_name": "Unittest Wave 1",
        "wave_id": "101",
    };
    const newItemSchemaName = "wave";
    const relatedItems: any[] = [];
    const relatedSchemaName = "database";
    ImportUtils.updateRelatedItemAttributes(schemas, newItem, newItemSchemaName, relatedItems, relatedSchemaName);
    expect(relatedItems).toEqual([]);
});

test("updateRelatedItemAttributes - No new item to reference.", () => {
    const schemas = defaultTestProps.schemas;
    const newItem = null;
    const newItemSchemaName = "wave";
    const relatedItems = [{
        "wave_name": "Unittest Wave 1",
        "wave_id": "101"
    }];
    const relatedSchemaName = "database";
    ImportUtils.updateRelatedItemAttributes(schemas, newItem, newItemSchemaName, relatedItems, relatedSchemaName);
    expect(relatedItems).toEqual([{
        "wave_name": "Unittest Wave 1",
        "wave_id": "101"
    }]);
});

test("updateRelatedItemAttributes - update items success", () => {
    const schemas = defaultTestProps.schemas;
    const newItem = {
        "app_name": "app1",
        "aws_accountid": "123456789012",
        "aws_region": "us-east-1",
        "wave_id": "101",
        "app_id": "101",
    };
    const newItemSchemaName = "application";
    const relatedItems = [
        {
            "server_name": "unittest1-NEW",
            "server_os_family": "linux",
            "server_os_version": "redhat",
            "server_fqdn": "unittest1.testdomain.local",
            "r_type": "Rehost",
            "app_id": "tbc",
            "__app_id": "Unit testing App 1-NEW"
        },
        {
            "all_applications": ["tbc", "something else"],
            "__all_applications": ["app1", "app2"],
        }
    ];
    const relatedSchemaName = "server";
    ImportUtils.updateRelatedItemAttributes(schemas, newItem, newItemSchemaName, relatedItems, relatedSchemaName);
    expect(relatedItems).toEqual([
        {
            "server_name": "unittest1-NEW",
            "server_os_family": "linux",
            "server_os_version": "redhat",
            "server_fqdn": "unittest1.testdomain.local",
            "r_type": "Rehost",
            "app_id": "tbc",
            "__app_id": "Unit testing App 1-NEW"
        },
        {
            "all_applications": [
                "101",
                "something else"
            ],
            "__all_applications": [
                "app1",
                "app2"
            ]
        }
    ]);
});

test("getRelationshipValueType - different scenarios", () => {
    let importedAttribute: { import_raw_header: string; attribute: { rel_display_attribute: string; name: string; listMultiSelect: any; }; } = {
        "attribute": {
            "rel_display_attribute": "wave_name",
            "listMultiSelect": false,
            "name": "",
        },
        "import_raw_header": "[application]wave_name",
    };
    const schemaName = "application";
    let result = ImportUtils.getRelationshipValueType(importedAttribute, schemaName);
    expect(result).toEqual("name");

    importedAttribute = {
        "attribute": {
            "rel_display_attribute": "wave_name",
            "listMultiSelect": false,
            "name": "",
        },
        "import_raw_header": "wave_name"
    };
    result = ImportUtils.getRelationshipValueType(importedAttribute, schemaName);
    expect(result).toEqual("name");

    importedAttribute = {
        "attribute": {
            "rel_display_attribute": "wave_name_not_matching",
            "name": "wave_name",
            "listMultiSelect": true,
        },
        "import_raw_header": "wave_name"
    };
    result = ImportUtils.getRelationshipValueType(importedAttribute, schemaName);
    expect(result).toEqual("name");

    importedAttribute = {
        "attribute": {
            "rel_display_attribute": "wave_name_not_matching",
            "name": "wave_name",
            "listMultiSelect": true,
        },
        "import_raw_header": "[application]wave_name"
    };
    result = ImportUtils.getRelationshipValueType(importedAttribute, schemaName);
    expect(result).toEqual("name");

    importedAttribute = {
        "attribute": {
            "rel_display_attribute": "wave_name_not_matching",
            "name": "wave_name",
            "listMultiSelect": false,
        },
        "import_raw_header": "wave_name"
    };
    result = ImportUtils.getRelationshipValueType(importedAttribute, schemaName);
    expect(result).toEqual("id");

    importedAttribute = {
        "attribute": {
            "rel_display_attribute": "wave_name_not_matching",
            "name": "wave_name",
            "listMultiSelect": false,
        },
        "import_raw_header": "[application]wave_name"
    };
    result = ImportUtils.getRelationshipValueType(importedAttribute, schemaName);
    expect(result).toEqual("id");
});
