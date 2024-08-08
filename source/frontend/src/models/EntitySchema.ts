import { HelpContent } from "./HelpContent";
import { Database } from "./Database";
import { Application } from "./Application";
import { Wave } from "./Wave";
import { Server } from "./Server";

export type SchemaMetaData = {
  schema_name: string;
  schema_type: string;
  friendly_name?: string;
};

export type EntitySchema = {
  schema_type: string;
  friendly_name?: string;
  attributes: Array<Attribute>;
  schema_name: string;
  group?: string;
  description?: string;
  actions?: Array<any>;
  lastModifiedTimestamp?: string;
  help_content?: HelpContent;
};

export type EntityName = "secret" | "script" | "database" | "server" | "application" | "wave" | "policy";

export type Attribute = {
  sample_data_intake?: any;
  conditions?: any;
  default?: string;
  description: string;
  group?: string;
  group_order?: string;
  help_content?: HelpContent;
  hidden?: boolean;
  labelKey?: string;
  listMultiSelect?: any;
  listValueAPI?: string;
  listvalue?: string;
  long_desc?: string;
  lookup?: string;
  name: string;
  readonly?: boolean;
  rel_additional_attributes?: string[];
  rel_attribute?: string;
  rel_display_attribute?: string;
  rel_entity?: EntityName;
  rel_filter_attribute_name?: string;
  rel_key?: string;
  required?: boolean;
  schema?: string;
  source_filter_attribute_name?: string;
  system?: boolean;
  type: string;
  unique?: boolean;
  validation_regex?: string;
  validation_regex_msg?: string;
  valueKey?: string;
};

export type DataLoadingState<T> = {
  data: T[];
  isLoading: boolean;
  error: any;
};

export type BaseData = {
  secret?: DataLoadingState<any>;
  script?: DataLoadingState<any>;
  database?: DataLoadingState<Database>;
  server?: DataLoadingState<Server>;
  application?: DataLoadingState<Application>;
  wave?: DataLoadingState<Wave>;
  policy?: DataLoadingState<any>;
};
