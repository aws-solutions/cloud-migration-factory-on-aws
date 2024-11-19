// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import React, { createContext, ReactNode, useState } from "react";

import { EntitySchema } from "../models/EntitySchema";
import { capitalize } from "../resources/main";

export type SplitPanelContextType = {
  splitPanelState: SplitPanelState;
  setContent: (content?: any, silent?: boolean) => void;

  /**
   * Check if the schema with the given name has help content. If yes, update the context state with that content.
   */
  setContentFromSchema: (schemas: Record<string, EntitySchema>, schemaName: string) => void;
  setSplitPanelOpen: (open: boolean) => void;
};
export type SplitPanelState = {
  splitPanelOpen: boolean;
  splitPanelContent?: any;
};

// default context, used if no context is provided. automatically applied to tests
const NULL_CONTEXT: SplitPanelContextType = {
  setContent: (content, silent) => {},
  setContentFromSchema: (schemas: Record<string, EntitySchema>, schemaName: string) => {},
  setSplitPanelOpen: (open: boolean) => {},
  splitPanelState: { splitPanelOpen: false },
};

export const SplitPanelContext = createContext<SplitPanelContextType>(NULL_CONTEXT);
export const SplitPanelContextProvider = ({ children }: { children: ReactNode }) => {
  const [splitPanelState, setSplitPanelState] = useState<SplitPanelState>({
    splitPanelOpen: false,
    splitPanelContent: undefined,
  });

  const setContent = async (content?: any, silent = true) => {
    setSplitPanelState((previousState: SplitPanelState) => {
      if (content == previousState.splitPanelContent) {
        // toggle help panel from Info link, as content is the same.
        return {
          splitPanelContent: content,
          splitPanelOpen: silent ? previousState.splitPanelOpen : !previousState.splitPanelOpen,
        };
      } else {
        return {
          splitPanelContent: content,
          splitPanelOpen: silent ? previousState.splitPanelOpen : true,
        };
      }
    });
  };

  const setContentFromSchema = async (schemas: Record<string, EntitySchema>, schemaName: string) => {
    const schema = schemas[schemaName];

    if (schemas && schema?.help_content) {
      schema.help_content.header = schema.friendly_name ? schema.friendly_name : capitalize(schemaName);
      await setContent(schema.help_content);
    }
  };

  const setSplitPanelOpen = (open: boolean) => {
    setSplitPanelState((previousState) => ({
      ...previousState,
      splitPanelOpen: open,
    }));
  };

  const context = { splitPanelState, setContent, setContentFromSchema, setSplitPanelOpen };
  return (
    <>
      <SplitPanelContext.Provider value={context}>{children}</SplitPanelContext.Provider>
    </>
  );
};
