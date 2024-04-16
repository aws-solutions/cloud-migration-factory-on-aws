// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import React, {createContext, ReactNode, useMemo, useState} from 'react';
import {HelpContent} from "../models/HelpContent";
import {EntitySchema} from "../models/EntitySchema";
import {capitalize} from "../resources/main";

export type ToolsContextType = {
  toolsState: ToolsState,
  setHelpPanelContent: (content?: HelpContent, silent?: boolean) => void;

  /**
   * Check if the schema with the given name has help content. If yes, update the context state with that content.
   */
  setHelpPanelContentFromSchema: (schemas: Record<string, EntitySchema>, schemaName: string) => void;
  setToolsOpen: (open: boolean) => void;
};
export type ToolsState = {
  toolsOpen: boolean;
  toolsHelpContent?: HelpContent;
};

// default context, used if no context is provided. automatically applied to tests
const NULL_CONTEXT: ToolsContextType = {
  setHelpPanelContent: (content, silent) => {
  },
  setHelpPanelContentFromSchema: (schemas: Record<string, EntitySchema>, schemaName: string) => {
  },
  setToolsOpen: (open: boolean) => {
  },
  toolsState: {toolsOpen: false}
};

export const ToolsContext = createContext<ToolsContextType>(NULL_CONTEXT);
export const ToolsContextProvider = ({children}: { children: ReactNode }) => {

  const [toolsState, setToolsState] = useState<ToolsState>({
    toolsOpen: false,
    toolsHelpContent: undefined
  });

  const setHelpPanelContent = async (content?: HelpContent, silent = true) => {
    setToolsState((previousState: ToolsState) => {
      if (content == previousState.toolsHelpContent){
        // toggle help panel from Info link, as content is the same.
        return {
          toolsHelpContent: content,
          toolsOpen: silent ? previousState.toolsOpen : !previousState.toolsOpen
        };
      } else {
        return {
          toolsHelpContent: content,
          toolsOpen: silent ? previousState.toolsOpen : true
        };
      }
    });
  };

  const setHelpPanelContentFromSchema = async (schemas: Record<string, EntitySchema>, schemaName: string) => {
    const schema = schemas[schemaName];

    if (schemas && schema?.help_content) {
      schema.help_content.header = schema.friendly_name ? schema.friendly_name : capitalize(schemaName);
      await setHelpPanelContent(schema.help_content)
    }
  }

  const setToolsOpen = (open: boolean) => {
    setToolsState(previousState => ({
      ...previousState,
      toolsOpen: open,
    }));
  }

  const context: ToolsContextType = useMemo<ToolsContextType>(() => {
    return {toolsState, setHelpPanelContent, setHelpPanelContentFromSchema, setToolsOpen};
  }, [toolsState]);

  return (
    <>
      <ToolsContext.Provider value={context}>
        {children}
      </ToolsContext.Provider>
    </>
  )
}
