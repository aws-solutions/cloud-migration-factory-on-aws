/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { ColumnLayout, SpaceBetween } from "@awsui/components-react";

import TextAttribute from "./TextAttribute";
import { getNestedValuePath } from "../../resources/main";

// Attribute Display message content
function returnLocaleDateTime(stringDateTime: string | number | Date) {
  let originalDate = new Date(stringDateTime);
  let newDate = new Date(originalDate.getTime() - originalDate.getTimezoneOffset() * 60 * 1000);

  return newDate.toLocaleString();
}

const Audit = ({ item }: any) => {
  function getHistoryUser(item: any, type: string) {
    const value = getNestedValuePath(item, "_history." + type + ".email");

    if (value) {
      return value;
    } else {
      return "-";
    }
  }

  function getHistoryDate(item: any, type: string) {
    const value = getNestedValuePath(item, "_history." + type);

    if (value) {
      return value;
    } else {
      return "-";
    }
  }

  return (
    <ColumnLayout columns={2} variant="text-grid">
      <div>
        <SpaceBetween size="l">
          <TextAttribute label={"Created by"}>{getHistoryUser(item, "createdBy")}</TextAttribute>
          <TextAttribute label={"Created on"}>{getHistoryDate(item, "createdTimestamp")}</TextAttribute>
        </SpaceBetween>
      </div>
      <div>
        <SpaceBetween size="l">
          <TextAttribute label={"Last modified by"}>{getHistoryUser(item, "lastModifiedBy")}</TextAttribute>
          <TextAttribute label={"Last updated on"}>{getHistoryDate(item, "lastModifiedTimestamp")}</TextAttribute>
        </SpaceBetween>
      </div>
    </ColumnLayout>
  );
};

export default Audit;
