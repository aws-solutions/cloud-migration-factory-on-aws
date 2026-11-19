/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { useContext } from "react";
import { NotificationContext } from "../contexts/NotificationContext";

export interface Notification {
  type: "success" | "error" | "warning" | "info";
  header: string;
  content: string;
  dismissible?: boolean;
  action?: React.ReactNode;
}

export function useNotifications() {
  const { notifications, addNotification, deleteNotification } = useContext(NotificationContext);

  return {
    notifications,
    addNotification,
    removeNotification: deleteNotification, // Alias deleteNotification as removeNotification for backward compatibility
  };
}
