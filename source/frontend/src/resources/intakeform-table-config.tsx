// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { ExpandableSection, SpaceBetween, StatusIndicator } from "@cloudscape-design/components";
import { getNestedValuePath } from "./main";

const ErrorCell = (props) => {
  return (
    <div>
      <StatusIndicator type={"error"}>{props.validation.length} Validation Errors</StatusIndicator>
      {props.validation.map((msg, i) => {
        if (props.validation.length !== i) {
          const displayKey = i;
          return <div key={displayKey}>{msg.attribute ? msg.attribute + ": " + msg.error : msg.error}</div>;
        } else {
          return msg.error;
        }
      })}
    </div>
  );
};

const WarningCell = (props) => {
  return (
    <div>
      <StatusIndicator type={"warning"}>{props.validation.length} Validation Warnings</StatusIndicator>
      {props.validation.map((msg, i) => {
        if (props.validation.length !== i) {
          const displayKey = i;
          return <div key={displayKey}>{msg.attribute ? msg.attribute + ": " + msg.error : msg.error}</div>;
        } else {
          return msg.error;
        }
      })}
    </div>
  );
};

const InformationalCell = (props) => {
  return (
    <ExpandableSection
      header={<StatusIndicator type={"info"}>{props.validation.length} Validation Informational</StatusIndicator>}
    >
      {props.validation.map((msg, i) => {
        if (props.validation.length !== i) {
          const displayKey = i;
          return <div key={displayKey}>{msg.attribute ? msg.attribute + ": " + msg.error : msg.error}</div>;
        } else {
          return msg.error;
        }
      })}
    </ExpandableSection>
  );
};

function status(value) {
  let component = undefined;

  let new_value = value.toLowerCase();

  switch (new_value) {
    case "failed":
      component = <StatusIndicator type="error">{value}</StatusIndicator>;
      break;
    case "running":
      component = <StatusIndicator type="in-progress">{value}</StatusIndicator>;
      break;
    case "complete":
      component = <StatusIndicator type="success">{value}</StatusIndicator>;
      break;
    case "error":
      component = <StatusIndicator type="error">{value}</StatusIndicator>;
      break;
    case "in-progress":
      component = <StatusIndicator type="in-progress">{value}</StatusIndicator>;
      break;
    case "success":
      component = <StatusIndicator type="success">{value}</StatusIndicator>;
      break;
    default:
      component = value;
  }

  return component;
}

function getColumnDefinitionsForCheckBox(attr, lattr) {
  return {
    id: attr.name,
    header: attr.description,
    cell: (item) => (getNestedValuePath(item, lattr.import_raw_header) ? "Yes" : "No"),
    minWidth: 180,
    sortingField: attr.name,
  };
}

function getColumnDefinitionsForStatus(attr, lattr) {
  return {
    id: attr.name,
    header: attr.description,
    cell: (item) => status(getNestedValuePath(item, lattr.import_raw_header)),
    minWidth: 180,
    sortingField: attr.name,
  };
}

function getColumnDefinitionsForPassword(attr, lattr) {
  return {
    id: attr.name,
    header: attr.description,
    cell: (item) => (getNestedValuePath(item, lattr.import_raw_header) ? "[value set]" : ""),
    minWidth: 180,
    sortingField: attr.name,
  };
}

function getColumnDefinitionsForRelationship(lattr, attr) {
  //Update last element in key name with __.
  let arrName = lattr.import_raw_header.split(".");
  arrName[arrName.length - 1] = "__" + arrName[arrName.length - 1];
  let newName = arrName.join(".");
  return {
    id: newName,
    header: attr.description,
    cell: (item) =>
      getNestedValuePath(item, newName)
        ? getNestedValuePath(item, newName)
        : getNestedValuePath(item, lattr.import_raw_header),
    minWidth: 180,
    sortingField: newName,
  };
}

function getColumnDefinitionsForTag(attr, lattr) {
  return {
    id: attr.name,
    header: attr.description,
    cell: (item) => getNestedValuePath(item, lattr.import_raw_header),
    minWidth: 180,
    sortingField: attr.name,
  };
}

function getColumnDefinitionsForPolicies(lattr, attr) {
  //Update last element in key name with __.
  let arrName1 = lattr.import_raw_header.split(".");
  arrName1[arrName1.length - 1] = "__" + arrName1[arrName1.length - 1];
  let newName1 = arrName1.join(".");
  return {
    id: attr.name,
    header: attr.description,
    cell: (item) =>
      getNestedValuePath(item, newName1)
        ? getNestedValuePath(item, newName1).join(", ")
        : getNestedValuePath(item, newName1),
    minWidth: 180,
    sortingField: attr.name,
  };
}

function mapPolicy(policy) {
  let finalMsg = [];

  if (policy.create) {
    finalMsg.push("C");
  }

  if (policy.read) {
    finalMsg.push("R");
  }

  if (policy.update) {
    finalMsg.push("U");
  }

  if (policy.delete) {
    finalMsg.push("D");
  }

  return (
    <div key={policy.schema_name}>
      {policy.friendly_name ? policy.friendly_name : policy.schema_name + " [" + finalMsg.join("") + "]"}
    </div>
  );
}

function getColumnDefinitionsForPolicy(attr, lattr) {
  return {
    id: attr.name,
    header: attr.description,
    cell: (item) =>
      getNestedValuePath(item, lattr.import_raw_header)
        ? getNestedValuePath(item, lattr.import_raw_header).map((policy, index) => {
            return mapPolicy(policy);
          })
        : getNestedValuePath(item, lattr.import_raw_header),
    minWidth: 180,
    sortingField: attr.name,
  };
}

function getColumnDefinitionsForGroups(attr, lattr) {
  return {
    id: attr.name,
    header: attr.description,
    cell: (item) =>
      getNestedValuePath(item, lattr.import_raw_header)
        ? getNestedValuePath(item, lattr.import_raw_header)
            .map((group, index) => {
              return group.group_name;
            })
            .join(", ")
        : getNestedValuePath(item, lattr.import_raw_header),
    minWidth: 180,
    sortingField: attr.name,
  };
}

function getColumnDefinitionsForJson(attr, lattr) {
  return {
    id: attr.name,
    header: attr.description,
    cell: (item) =>
      getNestedValuePath(item, lattr.import_raw_header)
        ? JSON.stringify(getNestedValuePath(item, lattr.import_raw_header))
        : "",
    minWidth: 180,
    sortingField: attr.name,
  };
}

function getColumnDefinitionsDefault(attr, lattr) {
  return {
    id: attr.name,
    header: (
      <ExpandableSection header={attr.description}>
        <SpaceBetween size={"xxs"}>
          {"File header: " + lattr.import_raw_header}
          {"Schema: " + lattr.schema_name}
        </SpaceBetween>
      </ExpandableSection>
    ),
    cell: (item) => getNestedValuePath(item, lattr.import_raw_header),
    minWidth: 180,
    sortingField: attr.name,
  };
}

export function getColumnDefinitions(schemaName, schema) {
  let columnDefinitions = [];

  defaultColumns(columnDefinitions);

  let lcolumnDefinitions = schema.map((lattr, index) => {
    const attr = lattr.attribute;

    if (!attr) {
      return {};
    }

    switch (attr.type) {
      case "checkbox":
        return getColumnDefinitionsForCheckBox(attr, lattr);
      case "status":
        return getColumnDefinitionsForStatus(attr, lattr);
      case "password":
        return getColumnDefinitionsForPassword(attr, lattr);
      case "relationship":
        return getColumnDefinitionsForRelationship(lattr, attr);
      case "tag":
        return getColumnDefinitionsForTag(attr, lattr);
      case "policies":
        return getColumnDefinitionsForPolicies(lattr, attr);
      case "policy":
        return getColumnDefinitionsForPolicy(attr, lattr);
      case "groups":
        return getColumnDefinitionsForGroups(attr, lattr);
      case "json":
        return getColumnDefinitionsForJson(attr, lattr);
      default:
        return getColumnDefinitionsDefault(attr, lattr);
    }
  });

  columnDefinitions = columnDefinitions.concat(lcolumnDefinitions);

  //Remove any dynamic embedded_entity attributes as currently not supported in table.
  //ATTN: add support for embedded_entity in table column.
  columnDefinitions = columnDefinitions.filter((filterAttribute) => {
    return filterAttribute.type !== "embedded_entity";
  });

  return columnDefinitions;
}

function defaultColumns(columnDefinitions) {
  columnDefinitions.push({
    id: "__validation",
    header: "Validation",
    cell: (item) =>
      item.__validation.errors.length > 0 ||
      item.__validation.warnings.length > 0 ||
      item.__validation.informational.length > 0 ? (
        <SpaceBetween size={"xxs"} direction={"vertical"}>
          {item.__validation.errors.length > 0 ? <ErrorCell validation={item.__validation.errors} /> : undefined}
          {item.__validation.warnings.length > 0 ? <WarningCell validation={item.__validation.warnings} /> : undefined}
          {item.__validation.informational.length > 0 ? (
            <InformationalCell validation={item.__validation.informational} />
          ) : undefined}
        </SpaceBetween>
      ) : (
        <StatusIndicator type={"success"}>Valid</StatusIndicator>
      ),
    width: 180,
    minWidth: 100,
    maxWidth: 200,
    sortingField: "__validation",
  });
}

function mapAttributeToOption(lattr) {
  const attr = lattr.attribute;
  let option = {};
  if (attr.type === "relationship") {
    //Update last element in key name with __.
    let arrName = attr.name.split(".");
    arrName[arrName.length - 1] = "__" + arrName[arrName.length - 1];
    let newName = arrName.join(".");

    option = {
      id: newName,
      label: attr.description,
      editable: attr.alwaysDisplay ? !attr.alwaysDisplay : true,
    };
  } else if (attr.type === "json" || attr.type === "embedded_entity") {
    option = {
      id: attr.name,
      label: attr.description,
      editable: false,
    };
  } else {
    option = {
      id: attr.name,
      label: attr.description,
      editable: attr.alwaysDisplay ? !attr.alwaysDisplay : true,
    };
  }
  return option;
}

export function getContentSelectorOptions(schema) {
  if (!schema) {
    return [];
  }

  //Remove any dynamic embedded_entity attributes as currently not supported in table.
  //ATTN: add support for embedded_entity in table column.

  let cleansedSchema = schema.filter((filterAttribute) => {
    if (filterAttribute.attribute) {
      return (
        filterAttribute.attribute.type !== "embedded_entity" ||
        filterAttribute.attribute.type !== "policy" ||
        filterAttribute.attribute.type !== "policies" ||
        filterAttribute.attribute.type !== "groups"
      );
    } else {
      return false;
    }
  });

  let options = cleansedSchema.map((lattr, index) => {
    return mapAttributeToOption(lattr);
  });

  const contentSelectorOptions = [
    {
      label: "Main attributes",
      options: options,
    },
  ];

  return contentSelectorOptions;
}

export const PAGE_SELECTOR_OPTIONS = [
  { value: 10, label: "10 Items" },
  { value: 30, label: "30 Items" },
  { value: 50, label: "50 Items" },
];

export const CUSTOM_PREFERENCE_OPTIONS = [
  { value: "table", label: "Table" },
  { value: "cards", label: "Cards" },
];

export const DEFAULT_PREFERENCES = {
  pageSize: 30,
  visibleContent: [
    "__validation",
    "wave_name",
    "app_name",
    "aws_region",
    "aws_accountid",
    "server_name",
    "server_os_family",
  ],
  wraplines: false,
};
