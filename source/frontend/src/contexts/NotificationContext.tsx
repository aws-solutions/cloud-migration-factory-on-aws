// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import React, { createContext, ReactNode, useMemo, useState } from "react";
import { CmfAddNotification } from "../models/AppChildProps";
import { Button, FlashbarProps } from "@awsui/components-react";
import { v4 } from "uuid";
import { useNavigate } from "react-router-dom";

export type NotificationContextType = {
  notifications: FlashbarProps.MessageDefinition[];
  addNotification: (notificationAddRequest: CmfAddNotification) => string;
  deleteNotification: (id: string) => void;
  clearNotifications: () => void;
  setNotifications: (
    value:
      | ((prevState: FlashbarProps.MessageDefinition[]) => FlashbarProps.MessageDefinition[])
      | FlashbarProps.MessageDefinition[]
  ) => void;
};

export const NotificationContext = createContext<NotificationContextType>(null as any);
export const NotificationContextProvider = ({ children }: { children: ReactNode }) => {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<FlashbarProps.MessageDefinition[]>([]);

  const navigateClick = (event: CustomEvent<any>, URL: any) => {
    event.preventDefault();
    navigate(URL);
  };

  const addNotification = (notificationAddRequest: CmfAddNotification) => {
    let newNotifications = [...notifications];
    if (!notificationAddRequest.id) {
      notificationAddRequest.id = v4();
    } else {
      newNotifications = notifications.filter(function (item) {
        return item.id !== notificationAddRequest.id;
      });
    }
    const id = notificationAddRequest.id;
    const notification: FlashbarProps.MessageDefinition = {
      id,
      onDismiss: () => deleteNotification(id),
      ...notificationAddRequest,
    };

    if (notificationAddRequest.actionButtonLink && notificationAddRequest.actionButtonTitle) {
      notification.action = (
        <Button onClick={(event) => navigateClick(event, notificationAddRequest.actionButtonLink)}>
          {notificationAddRequest.actionButtonTitle}
        </Button>
      );
    }
    setNotifications((notifications) => [...newNotifications, notification]);
    return id;
  };

  const clearNotifications = () => {
    setNotifications([]);
  };

  const deleteNotification = (id: string) => {
    setNotifications((notifications) => notifications.filter((item) => item.id !== id));
  };

  const context: NotificationContextType = useMemo<NotificationContextType>(() => {
    return { notifications, setNotifications, addNotification, deleteNotification, clearNotifications };
  }, [notifications]);

  return (
    <>
      <NotificationContext.Provider value={context}>{children}</NotificationContext.Provider>
    </>
  );
};
