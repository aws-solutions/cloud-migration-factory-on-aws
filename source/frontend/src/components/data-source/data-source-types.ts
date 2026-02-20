import { EntitySchema, HeaderData, SheetAndMappedHeaders } from "../../models";

export interface SheetData {
  readonly name: string;
  readonly headers: HeaderData[];
}

export interface SheetToEntityMapping extends SheetAndMappedHeaders {
  readonly entityNames: string[];
  readonly isSelected: boolean;
}

export interface ImportSheetDataWorkerProps {
  readonly schemas: Record<string, EntitySchema>;
  readonly dataSourceFile: File;
  readonly sheetToEntityMappings: SheetToEntityMapping[];
}
