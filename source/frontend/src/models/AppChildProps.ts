import { FlashbarProps } from "@awsui/components-react/flashbar/interfaces";
import { EntitySchema, SchemaMetaData } from "./EntitySchema";
import { ReactNode } from "react";

export type CmfAddNotification = {
  id?: string;
  actionButtonLink?: any;
  actionButtonTitle?: string;
  action?: any;
  onDismiss?: any;
  type?: FlashbarProps.Type;
  dismissible?: boolean;
  header?: string;
  content?: string | ReactNode;
  loading?: boolean;
};

export type AppChildProps = {
  schemas: Record<string, EntitySchema>;
  isReady?: boolean;
  userEntityAccess: {};
  userGroups: string[];
  reloadPermissions: () => Promise<unknown>;
  schemaMetadata: Array<SchemaMetaData>;
  schemaIsLoading?: boolean;
  reloadSchema: () => Promise<() => void>;
};
