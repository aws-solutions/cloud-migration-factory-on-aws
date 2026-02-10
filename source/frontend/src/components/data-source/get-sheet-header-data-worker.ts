import { read, utils, WorkSheet } from "xlsx";
import { WebWorkerMessage } from "../../actions/WorkerHook";
import { unzip } from "lodash";
import { SheetData } from "./data-source-types";
import { HeaderData } from "../../models";

const hasDataInFirstRow = (sheet: WorkSheet): boolean => {
  const cell = sheet["A1"];
  return cell !== undefined && cell.v !== undefined && cell.v !== null && cell.v !== "";
};

// exported for tests
export const getSheetData = async (file: File): Promise<SheetData[]> => {
  const buffer = await file.arrayBuffer();
  const workbook = read(buffer, { raw: true });

  const sheetsWithData: SheetData[] = [];

  for (const name of workbook.SheetNames) {
    const sheet = workbook.Sheets[name];

    if (hasDataInFirstRow(sheet)) {
      // Convert sheet to JSON with header: 1 to get array of arrays
      const data = utils.sheet_to_json(sheet, {
        header: 1,
        range: 0,
        defval: null,
      }) as unknown[][];

      const headers = data[0] as string[];
      const columns = unzip(data.slice(1, 11));

      const headersWithSamples: HeaderData[] = [];

      headers
        .filter((header) => header !== null)
        .forEach((header, index) => {
          headersWithSamples.push({
            name: header,
            previewValues: columns[index],
          });
        });

      sheetsWithData.push({
        name,
        headers: headersWithSamples,
      });
    }
  }
  return sheetsWithData;
};

const sendMessage = (result: WebWorkerMessage<SheetData[]>) => {
  self.postMessage(result);
};

const sendErrorMessage = (error: Error) => {
  sendMessage({
    state: "error",
    result: error,
  });
};

/**
 * Web worker to offload processing of large excel files which would
 * otherwise lock up the main UI thread.
 */
self.onmessage = async (event: MessageEvent<File | undefined>) => {
  sendMessage({
    state: "working",
  });

  const file = event.data;
  if (!file) {
    sendErrorMessage(new Error("No file provided"));
    return;
  }

  try {
    const sheets = await getSheetData(file);
    sendMessage({
      state: "complete",
      result: sheets,
    });
  } catch (error) {
    sendErrorMessage(error as Error);
  }
};
