import { CMFHistoryCreated } from "./Pipeline";

export type DataSource = Readonly<{
  data_source_id?: string;
  data_source_name: string;
  data_source_description: string;
  data_source_type: string;
  file_name: string;
  header_mappings: SheetAndMappedHeaders[];
  _history?: CMFHistoryCreated;
}>;

export interface SheetAndMappedHeaders {
  readonly sheetName: string;
  readonly headers: HeaderToEntityAttributeMapping[];
  readonly entityMappings?: Record<string, Record<string, string>>;
}

export interface HeaderToEntityAttributeMapping extends HeaderData {
  readonly entityAttributes: EntityAttribute[];
}

export interface EntityAttribute {
  readonly entityName: string;
  readonly attributeName: string;
}

export interface HeaderData {
  readonly name?: string;
  readonly previewValues?: unknown[];
}
