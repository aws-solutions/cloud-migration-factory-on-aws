import { DataSource } from "../models/DataSource";
import { WPMRule } from "../models/WpmRule";

export interface DataSourceEntityResponseBase {
  readonly errors?: DataSourceEntityResponseErrors;
}

export interface DataSourceEntityResponse extends DataSourceEntityResponseBase {
  readonly newItems?: DataSource[];
}

export interface DataSourceEntityResponseErrors {
  readonly existing_name: string[];
}

export interface DataSourceEntityUpdateResponse extends DataSourceEntityResponseBase {
  readonly ResponseMetadata?: DataSourceEntityUpdateResponseMetadata;
}

export interface DataSourceEntityUpdateResponseMetadata {
  readonly HTTPStatusCode: number;
}

export interface RuleEntityResponse {
  readonly newItems?: WPMRule[];
  readonly errors?: RuleEntityResponseErrors;
}

export interface RuleEntityResponseErrors {
  readonly existing_name: string[];
}
