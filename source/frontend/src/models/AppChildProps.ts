/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {FlashbarProps} from "@cloudscape-design/components";
import {EntitySchema, SchemaMetaData} from "./EntitySchema";
import {ReactNode} from "react";

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
