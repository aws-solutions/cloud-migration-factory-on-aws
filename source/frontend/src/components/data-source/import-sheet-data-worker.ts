import { WebWorkerMessage } from "../../actions/WorkerHook";
import { ImportSheetData } from "./import-sheet-data";

/**
 * Thin implementation of a web worker to make the core implementation
 * found in ImportSheetData, more testable.
 */

const sendMessage = (result: WebWorkerMessage<unknown>) => {
  self.postMessage(result);
};

const importSheetData = new ImportSheetData(sendMessage);

self.onmessage = importSheetData.handleOnMessage.bind(importSheetData);
