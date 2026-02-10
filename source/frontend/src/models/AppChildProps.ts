/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
import { ReactNode } from "react";
import { FlashbarProps } from "@cloudscape-design/components";
import { EntitySchema, SchemaMetaData } from "./EntitySchema";
import { CancelableEventHandler } from "../utils/OptionDefinition";

export type CmfAddNotification = {
  id?: string;
  actionButtonLink?: string;
  actionButtonTitle?: string;
  action?: ReactNode;
  onDismiss?: CancelableEventHandler;
  type?: FlashbarProps.Type;
  dismissible?: boolean;
  header?: string;
  content?: string | ReactNode;
  loading?: boolean;
  /**
   * The time in seconds after which the notification will be automatically dismissed.
   * @default 10 when the type is "success" otherwise `undefined`, i.e. no auto dismiss
   */
  autoDismissInSeconds?: number;
};

export type AppChildProps = {
  schemas: Record<string, EntitySchema>;
  isReady?: boolean;
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  userEntityAccess: {};
  userGroups: string[];
  reloadPermissions: () => Promise<unknown>;
  schemaMetadata: Array<SchemaMetaData>;
  schemaIsLoading?: boolean;
  reloadSchema: (refresh?: boolean) => Promise<() => void>;
  enabledModules: string[];
};
