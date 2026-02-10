// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import { createContext, ReactNode, useCallback, useMemo, useState, useRef, useEffect } from "react";
import { Button, FlashbarProps } from "@cloudscape-design/components";
import { useNavigate } from "react-router-dom";
import { v4 } from "uuid";
import { CmfAddNotification } from "../models/AppChildProps";

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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const NotificationContext = createContext<NotificationContextType>(null as any);
export const NotificationContextProvider = ({ children }: { children: ReactNode }) => {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<FlashbarProps.MessageDefinition[]>([]);
  // Reference for auto dismiss timers
  const timerRefs = useRef<Map<string, NodeJS.Timeout>>(new Map());

  // Clear all timers on unmount
  useEffect(() => {
    const timers = timerRefs.current;
    return () => {
      timers.forEach((timer) => clearInterval(timer));
      timers.clear();
    };
  }, []);

  const navigateClick = useCallback(
    (event: CustomEvent<unknown>, url: string) => {
      event.preventDefault();
      navigate(url);
    },
    [navigate]
  );

  const deleteNotification = useCallback((id: string) => {
    // Clear timer when notification is dismissed
    if (timerRefs.current.has(id)) {
      clearInterval(timerRefs.current.get(id));
      timerRefs.current.delete(id);
    }
    setNotifications((notifications) => notifications.filter((item) => item.id !== id));
  }, []);

  const addNotification = useCallback(
    (notificationAddRequest: CmfAddNotification) => {
      const autoDismissInSecs =
        notificationAddRequest.type === "success"
          ? (notificationAddRequest.autoDismissInSeconds ?? 10)
          : notificationAddRequest.autoDismissInSeconds;
      let timeLeft = autoDismissInSecs ?? 0;

      const headerWithAutoDismiss = (tl: number) =>
        tl > 0 ? (
          <>
            {notificationAddRequest.header} <i>(Dismissing in {tl}s)</i>
          </>
        ) : (
          notificationAddRequest.header
        );

      const id = notificationAddRequest.id ?? v4();
      const notification: FlashbarProps.MessageDefinition = {
        id,
        ...notificationAddRequest,
        onDismiss: () => deleteNotification(id),
        header: headerWithAutoDismiss(timeLeft),
        action:
          notificationAddRequest.actionButtonLink && notificationAddRequest.actionButtonTitle ? (
            <Button
              onClick={(event) => {
                if (notificationAddRequest.actionButtonLink)
                  navigateClick(event, notificationAddRequest.actionButtonLink);
              }}
            >
              {notificationAddRequest.actionButtonTitle}
            </Button>
          ) : undefined,
      };

      setNotifications((prevItems) => {
        const hasItem = prevItems.some((item) => item.id === notification.id);
        return hasItem
          ? prevItems.map((item) => (item.id === notification.id ? notification : item))
          : [...prevItems, notification];
      });

      // Auto dismiss timer
      if (autoDismissInSecs) {
        // Clear any existing timer for this notification
        if (timerRefs.current.has(id)) clearInterval(timerRefs.current.get(id));

        const updateNotification = () => {
          timeLeft -= 1;
          if (timeLeft <= 0) {
            // Delete notification when times up
            deleteNotification(id);
          } else {
            // Update the notification with countdown
            setNotifications((notifications) =>
              notifications.map((item) =>
                item.id === id
                  ? {
                      ...item,
                      header: headerWithAutoDismiss(timeLeft),
                    }
                  : item
              )
            );
          }
        };
        timerRefs.current.set(id, setInterval(updateNotification, 1000));
      }
      return id;
    },
    [deleteNotification, navigateClick]
  );

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  const context: NotificationContextType = useMemo<NotificationContextType>(() => {
    return {
      notifications,
      setNotifications,
      addNotification,
      deleteNotification,
      clearNotifications,
    };
  }, [addNotification, clearNotifications, deleteNotification, notifications]);

  return (
    <>
      <NotificationContext.Provider value={context}>{children}</NotificationContext.Provider>
    </>
  );
};
