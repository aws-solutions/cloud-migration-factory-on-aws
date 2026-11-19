import {
  Application,
  Database,
  MoveGroup,
  MoveGroupRequest,
  DataSource,
  Server,
  Wave,
  WPMJob,
  WPMRule,
} from "../models";

export type PredefinedEntityType =
  | "app"
  | "application"
  | "database"
  | "server"
  | "move_group"
  | "move_group_request"
  | "wave"
  | "wpm_job"
  | "rule"
  | "data_source";

export type CustomEntityType = string & { __type: "CustomEntityType" };

export type EntityType = PredefinedEntityType | CustomEntityType;

// Helper function to create custom entity types
export function createCustomEntityType(value: string): CustomEntityType {
  return value as CustomEntityType;
}

const schemas = {
  Application: {
    name: "application",
    friendlyName: "Application",
    keyAttribute: "app_id" as keyof Application,
  },
  Database: {
    name: "database",
    friendlyName: "Database",
    keyAttribute: "database_id" as keyof Database,
  },
  DataSource: {
    name: "data_source",
    friendlyName: "Data Source",
    keyAttribute: "data_source_id" as keyof DataSource,
  },
  Server: {
    name: "server",
    friendlyName: "Server",
    keyAttribute: "server_id" as keyof Server,
  },
  MoveGroup: {
    name: "move_group",
    friendlyName: "Move Group",
    keyAttribute: "move_group_id" as keyof MoveGroup,
  },
  MoveGroupRequest: {
    name: "move_group_request",
    friendlyName: "Move Group Request",
    keyAttribute: "move_group_request_id" as keyof MoveGroupRequest,
  },
  Wave: {
    name: "wave",
    friendlyName: "Wave",
    keyAttribute: "wave_id" as keyof Wave,
  },
  WPMJob: {
    name: "wpm_job",
    friendlyName: "WPM Job",
    keyAttribute: "wpm_job_id" as keyof WPMJob,
  },
  WPMRule: {
    name: "rule",
    friendlyName: "WPM Rule",
    keyAttribute: "rule_id" as keyof WPMRule,
  },
};

type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends object ? DeepReadonly<T[P]> : T[P];
};

export const Schemas: DeepReadonly<typeof schemas> = schemas;

export const DEFAULT_WPM_VALUES = {
  NOMINATION_COUNT: 10,
  MAX_RANK: Number.MAX_VALUE,
} as const;

export const MOVE_GROUP_REQUEST_STATUS = {
  COMPLETED: "COMPLETED",
  FAILED: "FAILED",
  PENDING: "PENDING",
  IN_PROGRESS: "IN_PROGRESS",
} as const;

export const REL_FILTER_ATTRIBUTE_NAME = "rel_filter_attribute_name";
export const SOURCE_FILTER_ATTRIBUTE_NAME = "source_filter_attribute_name";
