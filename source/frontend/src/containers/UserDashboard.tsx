/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";

import { Grid, SpaceBetween } from "@cloudscape-design/components";

import { useMFApps } from "../actions/ApplicationsHook";
import { useGetServers } from "../actions/ServersHook";
import { useMFWaves } from "../actions/WavesHook";
import { useGetDatabases } from "../actions/DatabasesHook";
import WaveStatus from "../components/dashboard/WaveStatus";
import ChartOSTypes from "../components/dashboard/ChartOSTypes";
import ChartServerEnvTypes from "../components/dashboard/ChartServerEnvTypes";
import WaveServersByMonth from "../components/dashboard/ServersByMonth";
import MFOverview from "../components/dashboard/MFOverview";
import ServerRepStatus from "../components/dashboard/ServerRepStatus";
import { ToolsContext } from "../contexts/ToolsContext";
import { Wave } from "../models/Wave";
import { Application } from "../models/Application";
import { Database } from "../models/Database";
import { Server } from "../models/Server";

const UserDashboard = () => {
  //Data items for viewer and table.
  const [waveLoadingState] = useMFWaves();
  const [appLoadingState] = useMFApps();
  const [serverLoadingState] = useGetServers();
  const [databaseLoadingState] = useGetDatabases();

  const { setHelpPanelContent } = React.useContext(ToolsContext);

  const migratedItems = React.useMemo(() => {
    const completedWaveIds = waveLoadingState.data
      .filter((wave: Wave) => wave.wave_status === "Completed")
      .map((wave: Wave) => wave.wave_id);

    const completedWaveIdSet = new Set(completedWaveIds);

    const migratedAppIds = appLoadingState.data
      // An app is considered as migrated only if all the waves involved complete
      .filter((app: Application) => app.wave_ids?.every((appId) => completedWaveIdSet.has(appId)))
      .map((app: Application) => app.app_id);

    const migratedServerIds = serverLoadingState.data
      .filter((server: Server) => completedWaveIdSet.has(server.wave_id ?? ""))
      .map((server: Server) => server.server_id);

    const migratedDatabaseIds = databaseLoadingState.data
      .filter((database: Database) => completedWaveIdSet.has(database.wave_id ?? ""))
      .map((database: Database) => database.database_id);

    return {
      waveIds: completedWaveIds,
      applicationIds: migratedAppIds,
      serverIds: migratedServerIds,
      databaseIds: migratedDatabaseIds,
    };
  }, [appLoadingState.data, databaseLoadingState.data, serverLoadingState.data, waveLoadingState.data]);

  /**
   * Update help tools panel with generic fixed content describing the dashboard.
   * Must be wrapped in useEffect, because React can't update a different component while this component is rendered.
   */
  React.useEffect(() => {
    setHelpPanelContent({
      header: "Dashboard",
      content: "Dashboards provide a high-level overview of the current state of your migration program.",
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
              dataWaves={waveLoadingState}
              dataServers={serverLoadingState}
              dataApps={appLoadingState}
              dataDatabases={databaseLoadingState}
              completed={migratedItems}
            />
            <WaveStatus data={waveLoadingState} />
            <WaveServersByMonth waves={waveLoadingState} servers={serverLoadingState} apps={appLoadingState} />
            <ChartOSTypes data={serverLoadingState} />
            <ChartServerEnvTypes data={serverLoadingState} />
            <ServerRepStatus data={serverLoadingState} />
          </Grid>
        </SpaceBetween>
      }
    </div>
  );
};
export default UserDashboard;
