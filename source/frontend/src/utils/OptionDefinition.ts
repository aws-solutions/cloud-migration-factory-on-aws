/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

// types that are not exported from CloudScape library, but required for the project
export interface OptionDefinition {
  value?: string;
  label?: string;
}

export type NonCancelableCustomEvent<DetailType> = Omit<CustomEvent<DetailType>, 'preventDefault'>;
export type CancelableEventHandler<Detail = {}> = (event: CustomEvent<Detail>) => void;