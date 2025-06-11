/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

// @ts-nocheck

import { getNestedValue, returnLocaleDateTime, sortAscendingComparator } from "./main";

function getSecretType(item) {
  if (item.data.SECRET_TYPE === "keyValue") {
    return "Key / Value";
  } else if (item.data.SECRET_TYPE === "OS") {
    return item.data.OS_TYPE + " OS";
  } else if (item.data.SECRET_TYPE === "plainText") {
    return "Plaintext";
  } else {
    return item.data.SECRET_TYPE;
  }
}

const COLUMN_DEFINITIONS = [
  {
    id: "secretname",
    header: "Secret name",
    cell: (item) => item.Name,
    sortingField: "Name",
  },
  {
    id: "secrettype",
    header: "Secret Type",
    cell: (item) => getSecretType(item),
    sortingField: "data",
    sortingComparator: (item1, item2) =>
      sortAscendingComparator(
        returnLocaleDateTime(getSecretType(item1), true),
        returnLocaleDateTime(getSecretType(item2), true)
      ),
  },
  {
    id: "description",
    header: "Description",
    cell: (item) => item.Description,
    sortingField: "Description",
  },
  {
    id: "createdon",
    header: "Created on",
    cell: (item) => returnLocaleDateTime(item.LastChangedDate),
    sortingField: "LastChangedDate",
    sortingComparator: (item1, item2) =>
      sortAscendingComparator(
        returnLocaleDateTime(getNestedValue(item1, "LastChangedDate"), true),
        returnLocaleDateTime(getNestedValue(item2, "LastChangedDate"), true)
      ),
  },
  {
    id: "lastretrieved",
    header: "Last retrieved",
    cell: (item) => returnLocaleDateTime(item.LastAccessedDate),
    sortingField: "LastAccessedDate",
    sortingComparator: (item1, item2) =>
      sortAscendingComparator(
        returnLocaleDateTime(getNestedValue(item1, "LastAccessedDate"), true),
        returnLocaleDateTime(getNestedValue(item2, "LastAccessedDate"), true)
      ),
  },
];

export function getColumnDefinitions() {
  return COLUMN_DEFINITIONS;
}

export function getContentSelectorOptions() {
  const contentSelectorOptions = {
    label: "Main attributes",
    options: [],
  };

  contentSelectorOptions.options = COLUMN_DEFINITIONS.map((attr, index) => {
    return {
      id: attr.id,
      label: attr.header,
      editable: true,
    };
  });

  return [contentSelectorOptions];
}

export const PAGE_SELECTOR_OPTIONS = [
  { value: 10, label: "10 Items" },
  { value: 30, label: "30 Items" },
  { value: 50, label: "50 Items" },
];

export const DEFAULT_PREFERENCES = {
  pageSize: 30,
  visibleContent: ["secretname", "secrettype", "description", "createdon"],
  wraplines: false,
};
