/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useContext, useEffect } from "react";
import { exportAll } from "../utils/xlsx-export";

import { Button } from "@awsui/components-react";

import { useMFApps } from "../actions/ApplicationsHook";
import { useGetServers } from "../actions/ServersHook";
import { useMFWaves } from "../actions/WavesHook";
import { useGetDatabases } from "../actions/DatabasesHook";
import { ToolsContext } from "../contexts/ToolsContext";

const UserExport = () => {
  //Data items for viewer and table.
  const [{ isLoading: isLoadingApps, data: dataApps }] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers }] = useGetServers();
  const [{ isLoading: isLoadingWaves, data: dataWaves }] = useMFWaves();
  const [{ isLoading: isLoadingDBs, data: dataDBs }] = useGetDatabases();

  const { setHelpPanelContent } = useContext(ToolsContext);

  function exportClick() {
    const data: any = {};
    data.servers = dataServers;
    data.applications = dataApps;
    data.waves = dataWaves;
    data.databases = dataDBs;

    exportAll(data, "all-data");
  }

  //Check if any data is still loading and disable download button.
  let dataLoading = isLoadingApps || isLoadingServers || isLoadingWaves || isLoadingDBs;

  //Update help tools panel. Must be wrapped in useEffect, because React can't update a different component while this component is rendered.
  useEffect(() => {
    setHelpPanelContent({
      header: "Export",
      content_text:
        "From here you can export all the data from the Migration Factory into a single multi tabbed Excel spreadsheet.",
    });
  }, []);

  return (
    <div>
      {
        <Button
          variant="primary"
          iconName="download"
          disabled={dataLoading}
          onClick={() => {
            exportClick();
          }}
        >
          Download All Data
        </Button>
      }
    </div>
  );
};

export default UserExport;
