/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { Box, ExpandableSection, SpaceBetween } from "@cloudscape-design/components";

import TextAttribute from "./TextAttribute";
import RelatedRecordPopover from "./RelatedRecordPopover";
import { getNestedValuePath } from "../../resources/main";
import { getRelationshipRecord, getRelationshipValue } from "../../resources/recordFunctions";
import { Attribute, BaseData, EntitySchema } from "../../models/EntitySchema";

type AllViewerAttributesParams = {
  item: any;
  schemas: Record<string, EntitySchema>;
  dataAll: BaseData;
  schema: EntitySchema;
  hideEmpty?: boolean;
};
const AllViewerAttributes = ({
  dataAll,
  hideEmpty,
  item,
  schema: { attributes },
  schemas,
}: AllViewerAttributesParams) => {
  function addCheckboxAttribute(attribute: Attribute) {
    const attributeValue = getNestedValuePath(item, attribute.name);
    return attributeValue !== undefined ? (
      <TextAttribute key={attribute.name} label={attribute.description}>
        {attributeValue ? "enabled" : "disabled"}
      </TextAttribute>
    ) : null;
  }

  function addMultiStringAttribute(attribute: Attribute) {
    const attributeValue = getNestedValuePath(item, attribute.name);
    return attributeValue || displayEmpty ? (
      <TextAttribute key={attribute.name} label={attribute.description}>
        {attributeValue ? attributeValue.join("\n") : "-"}
      </TextAttribute>
    ) : null;
  }

  function addJSONAttribute(attribute: Attribute) {
    let valueJson = "";
    const attributeValue = getNestedValuePath(item, attribute.name);
    if (attributeValue) {
      valueJson = attributeValue instanceof Object ? JSON.stringify(attributeValue, undefined, 4) : attributeValue;
    }
    return attributeValue || displayEmpty ? (
      <div key={attribute.name}>
        <Box margin={{ bottom: "xxxs" }} color="text-label">
          {attribute.description}
        </Box>
        {getJSONDisplayValue(valueJson)}
      </div>
    ) : null;
  }

  function addTextAttribute(attribute: Attribute) {
    return (
      <TextAttribute key={attribute.name} label={attribute.description}>
        {"unsupported value type for viewer"}
      </TextAttribute>
    );
  }

  function addTagAttribute(attribute: Attribute) {
    const attributeValue = getNestedValuePath(item, attribute.name);

    let tags = [];
    if (attributeValue) {
      tags = attributeValue.map((item: { key: string; value: string }) => {
        return item.key + " : " + item.value;
      });
    }
    return attributeValue || displayEmpty ? (
      <TextAttribute key={attribute.name} label={attribute.description}>
        {tags.join("\n")}
      </TextAttribute>
    ) : null;
  }

  function createMutipleRelationshipList(
    actualValuesNames: { [x: string]: string },
    actualValue: { [x: string]: string | number | boolean }
  ) {
    let multipleApps = [];
    if (actualValuesNames) {
      for (const subValueIdx in actualValue) {
        if (actualValue[subValueIdx] === "tbc") {
          multipleApps.push(
            <p>
              {actualValuesNames[subValueIdx] ? actualValuesNames[subValueIdx] + " [NEW]" : actualValue[subValueIdx]}
            </p>
          );
        }
      }
    }

    return multipleApps;
  }

  function getMultiRelationshipDisplayValues(
    relatedSchema: string,
    attribute: Attribute,
    value: { status: string; value: any; invalid: any[] } | { status: string; value: any },
    actualValue: { [x: string]: string | number | boolean },
    record: Record<string, any>
  ) {
    let multipleApps = [];
    if ((value.status === "loaded" || value.status === "not found") && actualValue) {
      for (const subRecord in record) {
        multipleApps.push(
          <RelatedRecordPopover
            key={attribute.name + subRecord}
            item={record[subRecord]}
            schema={schemas[relatedSchema]}
            schemas={schemas}
            dataAll={dataAll}
          >
            {value.value[subRecord] ? value.value[subRecord] : "-"}
          </RelatedRecordPopover>
        );
      }

      let actualValuesNames = getNestedValuePath(item, "__" + attribute.name); //Only used when importing data.
      if (actualValuesNames) {
        multipleApps = createMutipleRelationshipList(actualValuesNames, actualValue);
      }

      return (
        <div key={attribute.name}>
          <Box margin={{ bottom: "xxxs" }} color="text-label">
            {attribute.description}
          </Box>
          <div>
            <SpaceBetween size={"xxs"} direction={"vertical"}>
              {multipleApps}
            </SpaceBetween>
          </div>
        </div>
      );
    } else {
      return (
        <TextAttribute key={attribute.name} label={attribute.description} loading={value.status === "loading"}>
          {value.value ? value.value.join(",") : "-"}
        </TextAttribute>
      );
    }
  }

  function addRelationshipAttribute(attribute: Attribute) {
    let attributeValue = getNestedValuePath(item, attribute.name);
    let relatedValue = getRelationshipValue(attribute, dataAll, getNestedValuePath(item, attribute.name));
    let relatedRecord = getRelationshipRecord(attribute, dataAll, getNestedValuePath(item, attribute.name));
    const relatedSchema = attribute.rel_entity!;

    if (attribute.listMultiSelect) {
      if (displayEmpty || attributeValue) {
        if (relatedRecord) {
          return getMultiRelationshipDisplayValues(
            relatedSchema,
            attribute,
            relatedValue,
            attributeValue,
            relatedRecord
          );
        } else {
          return (
            <TextAttribute key={attribute.name} label={attribute.description}>
              {attributeValue ? attributeValue : "-"}
            </TextAttribute>
          );
        }
      } else {
        return null;
      }
    } else {
      return getSingleRelationshipDisplayValue(
        relatedSchema,
        attribute,
        relatedValue,
        attributeValue,
        relatedRecord,
        displayEmpty
      );
    }
  }

  function addPasswordAttribute(attribute: Attribute) {
    const attributeValue = getNestedValuePath(item, attribute.name);
    return attributeValue || displayEmpty ? (
      <TextAttribute key={attribute.name} label={attribute.description}>
        {attributeValue ? "[value set]" : "-"}
      </TextAttribute>
    ) : null;
  }

  function addEmbeddedEntityAttribute(attribute: Attribute) {
    let currentLookupValue = getNestedValuePath(item, attribute.lookup!);
    let embedded_value = getRelationshipValue(attribute, dataAll, currentLookupValue);
    const embedded_relatedSchema = attribute.rel_entity!;

    if (embedded_value.status === "loading") {
      //Data not loaded for embedded entity.
      return (
        <TextAttribute key={attribute.name} label={attribute.description} loading={embedded_value.status === "loading"}>
          {"-"}
        </TextAttribute>
      );
    }

    if (embedded_value.status === "not found") {
      //Data not loaded for embedded entity.
      return (
        <TextAttribute key={attribute.name} label={attribute.description}>
          {"ERROR: Script not found based on UUID : " + currentLookupValue}
        </TextAttribute>
      );
    }

    if (!schemas[embedded_relatedSchema]) {
      //Valid schema not found, display text.
      return (
        <TextAttribute key={attribute.name} label={attribute.description}>
          {attribute.rel_entity ? "Schema " + attribute.rel_entity + " not found." : "-"}
        </TextAttribute>
      );
    }

    //check if this new embedded item has already been stored in the state, if not create it.
    if (embedded_value.value != null) {
      //Remove any invalid items where name key is not defined. This should not be the case but possible with script packages where incorrectly written.
      embedded_value.value = embedded_value.value.filter((item: { name?: string }) => {
        return item.name !== undefined;
      });
      embedded_value.value = embedded_value.value.map((item: { name: string; __orig_name: any; group: string }) => {
        //prepend the embedded_entity name to all attribute names in order to store them under a single key.
        let appendedName = attribute.name + "." + item.name;
        if (item.__orig_name) {
          //Item has already been updated name.
          return item;
        } else {
          //Store original name of item.
          item.__orig_name = item.name;
          item.name = appendedName;
          item.group = attribute.description;
          return item;
        }
      });
    } else {
      embedded_value.value = [];
    }

    return (
      <SpaceBetween size="xxxs" key={attribute.name}>
        <AllViewerAttributes
          schema={{ attributes: embedded_value.value } as EntitySchema}
          schemas={schemas}
          item={item}
          dataAll={dataAll}
        />
      </SpaceBetween>
    );
  }

  function addPolicyAttribute(attribute: Attribute) {
    let valueJson = [];
    const attributeValue = getNestedValuePath(item, attribute.name);
    if (attributeValue) {
      valueJson = attributeValue;
    }

    return (
      <div key={attribute.name}>
        <Box margin={{ bottom: "xxxs" }} color="text-label">
          {attribute.description}
        </Box>
        {valueJson.map((policy: any) => {
          let finalMsg = [];

          if (policy.create) {
            finalMsg.push("Create");
          }

          if (policy.read) {
            finalMsg.push("Read");
          }

          if (policy.update) {
            finalMsg.push("Update");
          }

          if (policy.delete) {
            finalMsg.push("Delete");
          }

          return (
            <div key={policy.schema_name}>
              {policy.friendly_name ? policy.friendly_name : policy.schema_name + " [" + finalMsg.join(" ") + "]"}
            </div>
          );
        })}
      </div>
    );
  }

  function addDefaultAttribute(attribute: Attribute) {
    const attributeValue = getNestedValuePath(item, attribute.name);
    return attributeValue || displayEmpty ? (
      <TextAttribute key={attribute.name} label={attribute.description}>
        {attributeValue ? attributeValue : "-"}
      </TextAttribute>
    ) : null;
  }

  function getJSONDisplayValue(valueJson: string) {
    if (valueJson) {
      if (valueJson.length > 450) {
        return <ExpandableSection header={valueJson.substring(0, 450) + " ..."}>{valueJson}</ExpandableSection>;
      } else {
        return valueJson;
      }
    } else {
      return "-";
    }
  }

  function getSingleRelationshipDisplayNonLoaded(
    value: { status: string; value: any; invalid: any[] } | { status: string; value: any },
    attribute: Attribute,
    actualValue: string
  ) {
    const nestedValuePath = getNestedValuePath(item, "__" + attribute.name);
    const nestedValuePath1 = getNestedValuePath(item, attribute.name);
    if (value.status === "not found") {
      if (actualValue === "tbc" && nestedValuePath) {
        return (
          <TextAttribute key={attribute.name} label={attribute.description} loading={false}>
            {nestedValuePath ? `${nestedValuePath} [NEW]` : "-"}
          </TextAttribute>
        );
      } else {
        return (
          <TextAttribute key={attribute.name} label={attribute.description} loading={false}>
            {nestedValuePath1 ? `Not found: ${attribute.rel_entity}[${attribute.rel_key}]=${nestedValuePath1}` : "-"}
          </TextAttribute>
        );
      }
    } else {
      return (
        <TextAttribute key={attribute.name} label={attribute.description} loading={value.status === "loading"}>
          {nestedValuePath1 || "-"}
        </TextAttribute>
      );
    }
  }

  function getSingleRelationshipDisplay(
    value: { status: string; value: any; invalid: any[] } | { status: string; value: any },
    attribute: Attribute,
    actualValue: string,
    record: Record<string, any>,
    relatedSchema: string
  ) {
    if (value.status === "loaded" && value.value !== null) {
      return (
        <div key={attribute.name}>
          <Box margin={{ bottom: "xxxs" }} color="text-label">
            {attribute.description}
          </Box>
          <div>
            <RelatedRecordPopover
              key={attribute.name}
              item={record}
              schema={schemas[relatedSchema]}
              schemas={schemas}
              dataAll={dataAll}
            >
              {value.value}
            </RelatedRecordPopover>
          </div>
        </div>
      );
    } else {
      return getSingleRelationshipDisplayNonLoaded(value, attribute, actualValue);
    }
  }

  function getSingleRelationshipDisplayValue(
    relatedSchema: string,
    attribute: Attribute,
    value: { status: string; value: any; invalid: any[] } | { status: string; value: any },
    actualValue: string,
    record: Record<string, any>,
    displayEmpty: boolean
  ) {
    if (value.value || displayEmpty) {
      return getSingleRelationshipDisplay(value, attribute, actualValue, record, relatedSchema);
    } else {
      return null;
    }
  }

  let allAttributes: any[];
  //ATTN: - finish this sort script to allow grouped attributes to be created together
  let sortedSchemaAttributes = [...attributes].sort(function (a, b) {
    if (a.group && b.group) {
      return a.group > b.group ? 1 : -1;
    } else if (!a.group && b.group) {
      return -1;
    } else {
      return 1;
    }
  });

  //ATTN: Add to state in future and possibly store in user profile.
  let displayEmpty = !hideEmpty;

  allAttributes = sortedSchemaAttributes.map((attribute) => {
    if (!attribute.hidden) {
      switch (attribute.type) {
        case "checkbox": {
          return addCheckboxAttribute(attribute);
        }
        case "multivalue-string": {
          return addMultiStringAttribute(attribute);
        }
        case "json": {
          return addJSONAttribute(attribute);
        }
        case "textarea": {
          return addTextAttribute(attribute);
        }
        case "tag": {
          return addTagAttribute(attribute);
        }
        case "relationship": {
          return addRelationshipAttribute(attribute);
        }
        case "password": {
          return addPasswordAttribute(attribute);
        }
        case "embedded_entity": {
          return addEmbeddedEntityAttribute(attribute);
        }
        case "policy": {
          return addPolicyAttribute(attribute);
        }
        default: {
          return addDefaultAttribute(attribute);
        }
      }
    }
    return null;
  });

  return <SpaceBetween size="s">{allAttributes}</SpaceBetween>;
};

export default AllViewerAttributes;
