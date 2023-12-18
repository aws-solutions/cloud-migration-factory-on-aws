import * as XLSX from "xlsx";

/**
 * Exports an array of objects to an Excel spreadsheet.
 */
export function exportTable(
  items: Record<string, any>[],
  type: string,
  fileName: string
) {
  const copiedItems: Record<string, any>[] = JSON.parse(JSON.stringify(items))

  const updatedItems = copiedItems.map(preprocessItems);

  const wb = XLSX.utils.book_new(); // create new workbook
  wb.SheetNames.push(type); // create new worksheet
  wb.Sheets[type] = XLSX.utils.json_to_sheet(updatedItems); // load headers array into worksheet

  XLSX.writeFile(wb, fileName + ".xlsx") // export to user

  console.log(type + " exported.")
}

/**
 * Exports a dict of arrays to Excel spreadsheet. Each key name will be used to create a tab in the output Excel,
 * and then the array items will be the rows of the tab.
 */
export function exportAll(
  items: Record<string, Record<string, any>[]>,
  fileName: string) {

  const wb = XLSX.utils.book_new(); // create new workbook

  for (const itemType in items) {
    const copiedItems: Record<string, any>[] = JSON.parse(JSON.stringify(items[itemType]))

    const updatedItems = copiedItems.map(preprocessItems);

    wb.SheetNames.push(itemType); // create new worksheet
    wb.Sheets[itemType] = XLSX.utils.json_to_sheet(updatedItems); // load headers array into worksheet
  }

  XLSX.writeFile(wb, fileName + ".xlsx") // export to user

  console.log("All data exported.")
}

const preprocessItems = (item: any) => {
  for (let key in item) {
    if (key.startsWith('__')) {
      //Remove system computed keys.
      delete item[key]
    }

    if (Array.isArray(item[key])) {
      if (item[key].length > 0 && item[key][0].value && item[key][0].key) {
        //tags found
        item[key] = item[key].map((tag: any) => {
          return tag.key + '=' + tag.value;
        });
      }
      //Flatten Array.
      item[key] = item[key].join(';');
    } else if (item[key] != null && typeof item[key] === 'object') {
      // Object in field, convert to string
      item[key] = JSON.stringify(item[key]);
    }

  }
  return item;
};