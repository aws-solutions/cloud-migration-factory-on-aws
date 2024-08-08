/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useContext, useEffect } from "react";

import { Grid, SpaceBetween } from "@awsui/components-react";

import { useMFApps } from "../actions/ApplicationsHook";
import { useGetServers } from "../actions/ServersHook";
import { useMFWaves } from "../actions/WavesHook";
import { useGetDatabases } from "../actions/DatabasesHook";
import WaveStatus from "../components/dashboard/WaveStatus";
import ChartOSTypes from "../components/dashboard/ChartOSTypes";
import ChartServerEnvTypes from "../components/dashboard/ChartServerEnvTypes";
import WaveServersByMonth from "../components/dashboard/ServersByMonth";
import MFOverview, { CompletedItemIds } from "../components/dashboard/MFOverview";
import ServerRepStatus from "../components/dashboard/ServerRepStatus";
import { ToolsContext } from "../contexts/ToolsContext";
import { Wave } from "../models/Wave";
import { Application } from "../models/Application";
import { Database } from "../models/Database";
import { Server } from "../models/Server";

const UserDashboard = () => {
  //Data items for viewer and table.
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }] = useMFWaves();
  const [{ isLoading: isLoadingApps, data: dataApps, error: errorApps }] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers, error: errorServers }] = useGetServers();
  const [{ isLoading: isLoadingDatabases, data: dataDatabases }] = useGetDatabases();

  const { setHelpPanelContent } = useContext(ToolsContext);

  function getMigratedItems(): CompletedItemIds {
    const completedWaveIds = dataWaves
      .filter((wave: Wave) => wave.wave_status === "Completed")
      .map((wave: Wave) => wave.wave_id);

    const migratedAppIds = dataApps
      .filter((app: Application) => completedWaveIds.includes(app.wave_id))
      .map((app: Application) => app.app_id);

    const migratedServerIds = dataServers
      .filter((server: Server) => migratedAppIds.includes(server.app_id))
      .map((server: Server) => server.server_id);

    const migratedDatabaseIds = dataDatabases
      .filter((database: Database) => migratedServerIds.includes(database.app_id))
      .map((database: Database) => database.database_id);

    return {
      waveIds: completedWaveIds,
      applicationIds: migratedAppIds,
      serverIds: migratedServerIds,
      databaseIds: migratedDatabaseIds,
    };
  }

  /**
   * Update help tools panel with generic fixed content describing the dashboard.
   * Must be wrapped in useEffect, because React can't update a different component while this component is rendered.
   */
  useEffect(() => {
    setHelpPanelContent({
      header: "Dashboard",
      content: "Dashboards provide a high-level overview of the current state of your migration program.",
    });
  }, []);

  return (
    <div>
      {
        <SpaceBetween size="l">
          <Grid
            gridDefinition={[
              { colspan: { l: 12, m: 12, default: 12 } },
              { colspan: { l: 6, m: 6, default: 12 } },
              { colspan: { l: 6, m: 6, default: 12 } },
              { colspan: { l: 6, m: 6, default: 12 } },
              { colspan: { l: 6, m: 6, default: 12 } },
              { colspan: { l: 6, m: 6, default: 12 } },
            ]}
          >
            <MFOverview
              dataWaves={{ data: dataWaves, isLoading: isLoadingWaves }}
              dataServers={{ data: dataServers, isLoading: isLoadingServers }}
              dataApps={{ data: dataApps, isLoading: isLoadingApps }}
              dataDatabases={{ data: dataDatabases, isLoading: isLoadingDatabases }}
              completed={getMigratedItems()}
            />
            <WaveStatus data={{ data: dataWaves, isLoading: isLoadingWaves, error: errorWaves }} />
            <WaveServersByMonth
              Waves={{ data: dataWaves, isLoading: isLoadingWaves, error: errorWaves }}
              Servers={{ data: dataServers, isLoading: isLoadingServers, error: errorServers }}
              Apps={{ data: dataApps, isLoading: isLoadingApps, error: errorApps }}
            />
            <ChartOSTypes data={{ data: dataServers, isLoading: isLoadingServers, error: errorServers }} />
            <ChartServerEnvTypes data={{ data: dataServers, isLoading: isLoadingServers, error: errorServers }} />
            <ServerRepStatus data={{ data: dataServers, isLoading: isLoadingServers, error: errorServers }} />
          </Grid>
        </SpaceBetween>
      }
    </div>
  );
};
export default UserDashboard;
