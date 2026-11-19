import React from "react";

export type WebWorkerState = "working" | "complete" | "error";

export type WorkerController = {
  state?: WebWorkerState;
  terminate: () => void;
};

/**
 * If state is:
 *  * 'working' then result will be undefined
 *  * 'error' then result will be of type Error
 *  * 'complete' then result will be of type T
 */
export interface WebWorkerMessage<T> {
  readonly state: WebWorkerState;
  readonly result?: T | Error;
}

export interface WorkerOptions {
  readonly timeoutSeconds?: number;
}

/**
 * Hook for making web workers easier to work with. Returns a function
 * where type:
 *   - T is the input parameter and the type that is ultimately passed to the web
 *     worker when Worker.postMessage(..) is called.
 *   - K is the return parameter of the Promise.
 * The onmessage handler of the Worker needs to accept messages of type T and
 * when calling postMessage from the Worker it needs to send messages of type
 * WebWorkerMessage<K>.
 *
 * Only terminate once you have finished using the worker, it cannot be
 * re-instantiated.
 *
 * @param webWorkerUrl is the url to the logic you want the Worker to execute
 *  eg `new URL("./get-sheet-data-worker.ts", import.meta.url)`
 *
 */
export const useWorker = <T, K>(
  webWorkerUrl: URL,
  options: WorkerOptions = {
    timeoutSeconds: 5 * 60,
  }
): [(input: T) => Promise<K>, WorkerController] => {
  const [workerState, setWorkerState] = React.useState<WebWorkerState | undefined>();
  const workerStateRef = React.useRef<WebWorkerState>();
  const [isTerminated, setIsTerminated] = React.useState(false);
  const timeoutId = React.useRef<number>();
  const worker = React.useRef(new Worker(webWorkerUrl, { type: "module" }));
  const promise = React.useRef<
    | {
        resolve: (value: K) => void;
        reject: (reason?: Error) => void;
      }
    | undefined
  >(undefined);

  React.useEffect(() => {
    const localWorker = worker.current;
    localWorker.onmessage = (message: MessageEvent<WebWorkerMessage<K>>) => {
      if (!promise.current) {
        return;
      }

      const {
        data: { state, result },
      } = message;
      const { resolve, reject } = promise.current;

      if (state === "complete") {
        resolve(result as K);
      } else if (state === "error") {
        const error = result instanceof Error ? result : new Error("Unknown error occurred.");
        reject(error);
      }

      setWorkerState(state);
    };

    return () => {
      clearTimeoutIfSet();
      rejectOutstandingPromise();
      localWorker.terminate();
    };
  }, []);

  const clearTimeoutIfSet = () => {
    if (timeoutId.current) {
      clearTimeout(timeoutId.current);
      timeoutId.current = undefined;
    }
  };

  const rejectOutstandingPromise = (reason?: string) => {
    if (promise.current) {
      const error = new Error(reason ?? "Unknown error occurred.");
      promise.current.reject(error);
      promise.current = undefined;
    }
  };

  const terminate = React.useCallback((reason?: string) => {
    clearTimeoutIfSet();
    rejectOutstandingPromise(reason);
    setWorkerState(undefined);
    worker.current.terminate();
    setIsTerminated(true);
  }, []);

  React.useEffect(() => {
    workerStateRef.current = workerState;
  }, [workerState]);

  const { timeoutSeconds } = options;

  const invokeWorker = React.useCallback(
    async (input: T) => {
      if (workerStateRef.current === "working") {
        return Promise.reject(new Error("Web worker already in working state."));
      }

      if (isTerminated) {
        return Promise.reject(new Error("Web worker is terminated."));
      }

      setWorkerState("working");

      if (timeoutSeconds) {
        timeoutId.current = window.setTimeout(() => {
          terminate(`Operation timed out after ${timeoutSeconds} seconds.`);
        }, timeoutSeconds * 1000);
      }

      const result = new Promise<K>((resolve, reject) => {
        promise.current = {
          reject,
          resolve,
        };
      }).finally(() => {
        clearTimeoutIfSet();
        promise.current = undefined;
      });

      worker.current.postMessage(input);

      return result;
    },
    [isTerminated, terminate, timeoutSeconds]
  );

  return [
    invokeWorker,
    {
      state: workerState,
      terminate,
    },
  ];
};
