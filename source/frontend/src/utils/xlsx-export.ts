/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import * as XLSX from "xlsx";

/**
 * Exports an array of objects to an Excel spreadsheet.
 */
export function exportTable(items: Record<string, any>[], type: string, fileName: string) {
  const copiedItems: Record<string, any>[] = JSON.parse(JSON.stringify(items));

  const updatedItems = copiedItems.map(preprocessItems);

  const wb = XLSX.utils.book_new(); // create new workbook
  wb.SheetNames.push(type); // create new worksheet
  wb.Sheets[type] = XLSX.utils.json_to_sheet(updatedItems); // load headers array into worksheet

  XLSX.writeFile(wb, fileName + ".xlsx"); // export to user

  console.log(type + " exported.");
}

/**
 * Exports a dict of arrays to Excel spreadsheet. Each key name will be used to create a tab in the output Excel,
 * and then the array items will be the rows of the tab.
 */
export function exportAll(items: Record<string, Record<string, any>[]>, fileName: string) {
  const wb = XLSX.utils.book_new(); // create new workbook

  for (const itemType in items) {
    const copiedItems: Record<string, any>[] = JSON.parse(JSON.stringify(items[itemType]));

    const updatedItems = copiedItems.map(preprocessItems);

    wb.SheetNames.push(itemType); // create new worksheet
    wb.Sheets[itemType] = XLSX.utils.json_to_sheet(updatedItems); // load headers array into worksheet
  }

  XLSX.writeFile(wb, fileName + ".xlsx"); // export to user

  console.log("All data exported.");
}

const truncateLargeText = (item: any, key: string) => {
  const truncate_to: number = 1000;
  const excel_limit_chars: number = 32767;

  if (item[key] != null && typeof item[key] === "string") {
    // If the text is longer than excel supports truncate it.
    if (item[key].length > excel_limit_chars) {
      //Truncate long strings
      let over_chars: number = item[key].length - truncate_to;

      let message_over: string = "[" + over_chars + " characters truncated, first " + truncate_to + " provided]";

      item[key + "[truncated - Excel max chars " + excel_limit_chars + "]"] =
        message_over + item[key].substring(0, truncate_to);
      delete item[key];
    }
  }
};

const preprocessItems = (item: any) => {
  for (let key in item) {
    if (key.startsWith("__")) {
      //Remove system computed keys.
      delete item[key];
      continue;
    }

    if (Array.isArray(item[key])) {
      if (item[key].length > 0 && item[key][0].value && item[key][0].key) {
        //tags found
        item[key] = item[key].map((tag: any) => {
          return tag.key + "=" + tag.value;
        });
      }
      //Flatten Array.
      item[key] = item[key].join(";");
    } else if (item[key] != null && typeof item[key] === "object") {
      // Object in field, convert to string
      item[key] = JSON.stringify(item[key]);
    }

    truncateLargeText(item, key);
  }
  return item;
};
