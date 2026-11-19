import { read, WorkBook } from "xlsx";
import { WebWorkerMessage } from "../../actions/WorkerHook";
import { ImportSheetDataWorkerProps } from "./data-source-types";
import { processSheetData, SheetNotFoundError } from "./import-sheet-data-utils";
import { validateData } from "../data-validation";

/**
 * Implementation of the logic for importing multisheet data using
 * a web Worker.
 */
export class ImportSheetData {
  constructor(private postMessage: (result: WebWorkerMessage<unknown>) => void) {}

  /**
   * Handles messages sent to the web Worker.
   */
  public async handleOnMessage(event: MessageEvent<ImportSheetDataWorkerProps | undefined>) {
    this.sendMessage({
      state: "working",
    });

    const props = event.data;
    if (!props) {
      this.sendErrorMessage(new Error("No input props provided"));
      return;
    }

    const { schemas, dataSourceFile, sheetToEntityMappings } = props;

    try {
      // Step 1: Load the workbook from the file
      const workbook = await this.loadWorkbook(dataSourceFile);

      // Step 2: Process sheet data and get entities ready for validation
      const entities = processSheetData(sheetToEntityMappings, workbook, schemas);

      // Step 3: Validate the data
      const validationResult = validateData(entities);

      // Step 4: Return validation results
      this.postMessage({
        state: "complete",
        result: {
          validationResult,
        },
      });
    } catch (error) {
      if (error instanceof SheetNotFoundError) {
        this.sendErrorMessage(
          new Error(
            `Import failed: ${error.message}. Please verify that the file you've imported matches the selected data source.`
          )
        );
      } else {
        this.sendErrorMessage(error as Error);
      }
    }
  }

  /**
   * Loads a workbook from a file.
   *
   * @param dataSourceFile - The file to load
   * @returns The loaded workbook
   */
  private async loadWorkbook(dataSourceFile: File): Promise<WorkBook> {
    const buffer = await dataSourceFile.arrayBuffer();
    return read(buffer, { raw: true });
  }

  /**
   * Posts message back to the main thread from the web worker.
   *
   * @param result - The message to post
   */
  private sendMessage(result: WebWorkerMessage<unknown>) {
    this.postMessage(result);
  }

  /**
   * Posts an error message back to the main thread.
   *
   * @param error - The error to post
   */
  private sendErrorMessage(error: Error) {
    this.sendMessage({
      state: "error",
      result: error,
    });
  }
}
