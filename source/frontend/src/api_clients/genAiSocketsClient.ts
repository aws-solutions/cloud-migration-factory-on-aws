/**
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { EntitySchema, HeaderData, HeaderMappingResponse } from "../models";

/**
 * GenAI WebSockets Client
 *
 * A TypeScript client for interfacing with the Migration Factory GenAI WebSockets API.
 * This client handles authentication, connection management, and message handling for
 * long-running GenAI operations.
 */
export interface GenAiSocketsConfig {
  /** WebSocket API endpoint URL (e.g., wss://abc123.execute-api.us-east-1.amazonaws.com/prod) */
  apiUrl: string;
  /** Authentication token (JWT from Cognito) */
  authToken: string;
  /** Auto-reconnect on connection close (default: true) */
  autoReconnect?: boolean;
  /** Maximum reconnection attempts (default: 5) */
  maxReconnectAttempts?: number;
  /** Reconnection delay in milliseconds (default: 3000) */
  reconnectDelay?: number;
  /** Timeout for sync operations in milliseconds (default: 60000) */
  syncTimeout?: number;
  /** Debug mode for additional logging (default: false) */
  debug?: boolean;
}

/**
 * Action types supported by the GenAI WebSocket API
 *
 * - "MAP_HEADERS": Request to map column headers against an entity schema
 * - "*": Wildcard to handle all action types (used for global message handlers)
 */
export type Action = "MAP_HEADERS" | "*";

interface PrivateGenAiSocketsConfig extends GenAiSocketsConfig {
  autoReconnect: boolean;
  maxReconnectAttempts: number;
  reconnectDelay: number;
  syncTimeout: number;
  debug: boolean;
}

/** Union type for all supported GenAI WebSocket message types */
type GenAiMessage = MapHeadersMessage; // replace any with new request types

/** Message for requesting header mapping from GenAI service */
interface MapHeadersMessage {
  /** Action identifier for header mapping requests */
  action: "MAP_HEADERS";
  /** Array of header data to be mapped */
  headers: HeaderData[];
  /** Entity schema to map headers against */
  schemas: Record<string, Partial<EntitySchema>>;
}

/** Response received from GenAI WebSocket service */
export interface GenAiResponse {
  /** Action identifier indicating the type of response */
  action: string;
  /** Response payload containing the mapping results */
  result?: HeaderMappingResponse; // replace any with new response types
  /** Error message if the request failed */
  error?: string;
}

/** Request structure for header mapping operations */
export interface MapHeadersRequest {
  /** Immutable array of headers to be processed */
  readonly headers: HeaderData[];
  /** Immutable schema definition for mapping */
  readonly schemas: Record<string, Partial<EntitySchema>>;
}

/** Handler function for processing incoming WebSocket messages */
export type MessageHandler = (response: GenAiResponse) => void;
/** Handler function for WebSocket connection events */
export type ConnectionHandler = () => void;
/** Handler function for WebSocket error events */
export type ErrorHandler = (error: Error) => void;

/**
 * GenAI WebSockets Client for Migration Factory
 */
export class GenAiSocketsClient {
  private config: PrivateGenAiSocketsConfig;
  private socket: WebSocket | null = null;
  private messageHandlers: Map<string, MessageHandler[]> = new Map();
  private onConnectHandlers: ConnectionHandler[] = [];
  private onDisconnectHandlers: ConnectionHandler[] = [];
  private onErrorHandlers: ErrorHandler[] = [];
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private connectionPromise: Promise<void> | null = null;

  /**
   * Create a new GenAI WebSockets client
   * @param config Client configuration
   */
  constructor(config: GenAiSocketsConfig) {
    this.config = {
      autoReconnect: true,
      maxReconnectAttempts: 5,
      reconnectDelay: 3000,
      syncTimeout: 60000,
      debug: false,
      ...config,
    };
  }

  /**
   * Connect to the WebSocket API
   * @returns Promise that resolves when connected
   */
  public connect(): Promise<void> {
    if (this.isConnected()) {
      return Promise.resolve();
    }

    if (this.connectionPromise) {
      return this.connectionPromise;
    }

    this.connectionPromise = this.createConnection();
    return this.connectionPromise;
  }

  /**
   * Register a handler for connection events
   * @param handler Handler function
   * @returns this (for chaining)
   */
  public onConnect(handler: ConnectionHandler): this {
    this.onConnectHandlers.push(handler);
    return this;
  }

  /**
   * Register a handler for disconnection events
   * @param handler Handler function
   * @returns this (for chaining)
   */
  public onDisconnect(handler: ConnectionHandler): this {
    this.onDisconnectHandlers.push(handler);
    return this;
  }

  /**
   * Register a handler for error events
   * @param handler Handler function
   * @returns this (for chaining)
   */
  public onError(handler: ErrorHandler): this {
    this.onErrorHandlers.push(handler);
    return this;
  }

  /**
   * Close the WebSocket connection
   */
  public disconnect(): void {
    this.config.autoReconnect = false;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.socket) {
      this.socket.close(1000, "Client disconnect");
      this.socket = null;
    }

    this.connectionPromise = null;
  }

  /**
   * Register a handler for a specific message action
   * @param action Action to handle (or '*' for all actions)
   * @param handler Handler function
   * @returns this (for chaining)
   */
  public on(action: Action, handler: MessageHandler): this {
    const handlers = this.messageHandlers.get(action) || [];
    handlers.push(handler);
    this.messageHandlers.set(action, handlers);
    return this;
  }

  /**
   * Remove a handler for a specific message action
   * @param action Action to remove handler from
   * @param handler Handler function to remove
   * @returns this (for chaining)
   */
  public off(action: Action, handler: MessageHandler): this {
    const handlers = this.messageHandlers.get(action);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
    return this;
  }

  /**
   * Send a MAP_HEADERS request to map column headers
   * @param request MapHeadersRequest containing headers and schema
   * @returns Promise that resolves when the request is sent
   */
  public mapHeaders(request: MapHeadersRequest): Promise<void> {
    return this.send({
      action: "MAP_HEADERS",
      headers: request.headers,
      schemas: request.schemas,
    });
  }

  /**
   * Send a MAP_HEADERS request and wait for the response
   * @param request MapHeadersRequest containing headers and schema
   * @returns Promise that resolves with the mapping response
   */
  public async mapHeadersSync(request: MapHeadersRequest): Promise<HeaderMappingResponse> {
    return new Promise(async (resolve, reject) => {
      const timeout = setTimeout(() => {
        this.off("MAP_HEADERS", handler);
        reject(new Error(`Request timeout after ${this.config.syncTimeout}ms`));
      }, this.config.syncTimeout);

      const handler = (response: GenAiResponse) => {
        clearTimeout(timeout);
        this.off("MAP_HEADERS", handler);

        if (response.result) {
          resolve(response.result);
        } else if (response.error) {
          reject(new Error(response.error));
        } else {
          // If result and error not set
          reject(new Error("Received empty response"));
        }
      };

      this.on("MAP_HEADERS", handler);

      try {
        await this.send({
          action: "MAP_HEADERS",
          headers: request.headers,
          schemas: request.schemas,
        });
      } catch (error) {
        clearTimeout(timeout);
        this.off("MAP_HEADERS", handler);
        reject(error);
      }
    });
  }

  /**
   * Check if the client is connected
   * @returns True if connected
   */
  public isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  private createConnection(): Promise<void> {
    this.isConnecting = true;

    return new Promise((resolve, reject) => {
      try {
        this.socket = new WebSocket(`${this.config.apiUrl}`, this.config.authToken);

        this.socket.onopen = () => {
          this.log("WebSocket connection established");
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.connectionPromise = null;
          this.onConnectHandlers.forEach((handler) => handler());
          resolve();
        };

        this.socket.onclose = (event) => {
          this.log(`WebSocket connection closed: ${event.code} ${event.reason}`);
          this.isConnecting = false;
          this.connectionPromise = null;
          this.onDisconnectHandlers.forEach((handler) => handler());
          this.handleReconnection();
        };

        this.socket.onerror = () => {
          const error = new Error("WebSocket connection error");
          this.log("WebSocket error", error);
          this.onErrorHandlers.forEach((handler) => handler(error));
          if (this.isConnecting) {
            this.isConnecting = false;
            this.connectionPromise = null;
            reject(error);
          }
        };

        this.socket.onmessage = (event) => this.handleMessage(event);
      } catch (err) {
        this.isConnecting = false;
        this.connectionPromise = null;
        reject(err);
      }
    });
  }

  private handleReconnection(): void {
    if (!this.config.autoReconnect || this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      return;
    }

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.config.maxReconnectAttempts})`);
      this.connect().catch((err) => this.log(`Reconnection failed: ${err.message}`));
    }, this.config.reconnectDelay);
  }

  private handleMessage(event: MessageEvent): void {
    try {
      if (typeof event.data !== "string" || event.data.length > 1048576) {
        throw new Error("Invalid message format or size");
      }

      const response = JSON.parse(event.data) as GenAiResponse;

      if (!response || typeof response !== "object" || typeof response.action !== "string") {
        throw new Error("Invalid message structure");
      }

      this.log("Received message:", response);

      const handlers = this.messageHandlers.get(response.action) || [];
      const wildcardHandlers = this.messageHandlers.get("*") || [];

      [...handlers, ...wildcardHandlers].forEach((handler) => handler(response));
    } catch (err) {
      const error = new Error(`Failed to parse message: ${err instanceof Error ? err.message : String(err)}`);
      this.log("Error parsing message:", err);
      this.onErrorHandlers.forEach((handler) => handler(error));
    }
  }

  private async send(message: GenAiMessage): Promise<void> {
    if (!this.isConnected()) {
      await this.connect();
    }

    try {
      if (!this.socket) {
        throw new Error("WebSocket is not connected");
      }

      this.log("Sending message:", message);
      this.socket.send(JSON.stringify(message));
    } catch (err) {
      this.log("Error sending message:", err);
      throw err;
    }
  }

  /**
   * Log a message if debug mode is enabled
   * @param message Message to log
   * @param data Additional data to log
   */
  /* eslint-disable-next-line @typescript-eslint/no-explicit-any */
  private log(message: string, ...data: any[]): void {
    if (this.config.debug) {
      console.log(`[GenAiSocketsClient] ${message}`, ...data);
    }
  }
}

/**
 * Create a WebSocket client with the provided configuration
 * @param config Client configuration
 * @returns Configured client instance
 */
export function createGenAiSocketsClient(config: GenAiSocketsConfig): GenAiSocketsClient {
  return new GenAiSocketsClient(config);
}
