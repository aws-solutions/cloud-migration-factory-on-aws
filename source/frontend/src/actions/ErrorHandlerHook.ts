import React from "react";
import { NotificationContext } from "../contexts/NotificationContext";
import { FlashbarProps } from "@cloudscape-design/components";

/**
 * Defines the allowed error types for notifications.
 * Limited to "warning" or "error" from Cloudscape FlashbarProps.Type.
 */
type ErrorType = Extract<FlashbarProps.Type, "warning" | "error">;

/**
 * Extended Error class that includes a type property for notification display.
 * This allows errors to be displayed as either warnings or errors in the UI.
 */
export class ErrorWithType extends Error {
  /**
   * Creates a new error with a specified type.
   *
   * @param message - The error message to display
   * @param type - The type of error notification to show ("warning" or "error")
   */
  constructor(
    message: string,
    public type: ErrorType
  ) {
    super(message);
  }
}

/**
 * Configuration options for error notifications.
 */
export interface ErrorNotificationOptions {
  /**
   * Optional header text for the notification.
   */
  header?: string;

  /**
   * Optional content text for the notification.
   * If not provided, the error message will be used instead.
   */
  content?: string;
}

/**
 * Custom React hook for handling and displaying errors as notifications.
 *
 * @returns A callback function that can be used to handle errors and display notifications
 *
 * @example
 * ```tsx
 * const handleError = useErrorHandler();
 *
 * try {
 *   // Some code that might throw an error
 * } catch (error) {
 *   handleError(error, { header: "Operation Failed" });
 * }
 * ```
 */
export const useErrorHandler = () => {
  const { addNotification } = React.useContext(NotificationContext);

  /**
   * Handles an error by logging it to the console and displaying a notification.
   *
   * @param e - The error object or unknown value to handle
   * @param options - Configuration options for the notification
   */
  return React.useCallback(
    (e: unknown, options: ErrorNotificationOptions) => {
      console.error(e);
      addNotification({
        dismissible: true,
        type: e instanceof ErrorWithType ? e.type : "error",
        header: options.header,
        content: options.content ?? (e instanceof Error ? e.message : "An unexpected error occurred"),
      });
    },
    [addNotification]
  );
};
