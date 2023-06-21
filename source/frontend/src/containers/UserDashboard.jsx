/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect} from 'react';

import {
  Grid,
  SpaceBetween
} from '@awsui/components-react';

import { useMFApps } from "../actions/ApplicationsHook";
import { useGetServers } from "../actions/ServersHook.js";
import { useMFWaves } from "../actions/WavesHook.js";
import { useGetDatabases } from "../actions/DatabasesHook.js";
import WaveStatus from '../components/dashboard/WaveStatus.jsx'
import ChartOSTypes from '../components/dashboard/ChartOSTypes.jsx'
import ChartServerEnvTypes from '../components/dashboard/ChartServerEnvTypes.jsx'
import WaveServersByMonth from '../components/dashboard/ServersByMonth.jsx'
import MFOverview from '../components/dashboard/MFOverview.jsx'
import ServerRepStatus from "../components/dashboard/ServerRepStatus";

/**
 * React CMF user dashboard container REACT component.
 * @param props
 * @returns {JSX.Element}
 * @constructor
 */
const UserDashboard = (props) => {
  //Data items for viewer and table.
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }, ] = useMFWaves();
  const [{ isLoading: isLoadingApps, data: dataApps, error: errorApps }, ] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers, error: errorServers }, ] = useGetServers();
  const [{ isLoading: isLoadingDatabases, data: dataDatabases, error: errorDatabases }, ] = useGetDatabases();

  /**
   * Returns the migrated items based on the Wave that they are linked to being in a Completed status.
   * @returns {} - Returns object containing keys per migrated schema, each containing an array of record IDs.
   */
  function getMigratedItems(){

    let completedItems = {}

    for (const wave of dataWaves){
      if (wave.wave_status === 'Completed'){
        if (completedItems['waves']) {
          completedItems['waves'].push(wave.wave_id);
        } else {
          completedItems['waves'] = [];
          completedItems['waves'].push(wave.wave_id);
        }
      }
    }

    if (completedItems['waves']) {
      //Waves completed.
      for (const application of dataApps) {
        if (completedItems['waves'].includes(application.wave_id)) {
          if (completedItems['applications']) {
            completedItems['applications'].push(application.app_id);
          } else {
            completedItems['applications'] = [];
            completedItems['applications'].push(application.app_id);
          }
        }
      }

      if(completedItems['applications']) {
        //At least one application completed, check if related servers or databases.
        for (const server of dataServers) {
          if (completedItems['applications'].includes(server.app_id)) {
            if (completedItems['servers']) {
              completedItems['servers'].push(server.server_id);
            } else {
              completedItems['servers'] = [];
              completedItems['servers'].push(server.server_id);
            }
          }
        }

        for (const database of dataDatabases) {
          if (completedItems['applications'].includes(database.app_id)) {
            if (completedItems['databases']) {
              completedItems['databases'].push(database.database_id);
            } else {
              completedItems['databases'] = [];
              completedItems['databases'].push(database.database_id);
            }
          }
        }
      }
    }

    return completedItems;

  }

  /**
   * Update help tools panel with generic fixed content describing the dashboard.
   */
  useEffect(() => {
    props.setHelpPanelContent({header: 'Dashboard' , content: 'Dashboards provide a high-level overview of the current state of your migration program.'})

  }, []);

  return (
    <div>
          {<SpaceBetween size="l">
            <Grid
              gridDefinition={[
                {colspan: {l: '12', m: '12', default: '12'}},
                {colspan: {l: '6', m: '6', default: '12'}},
                {colspan: {l: '6', m: '6', default: '12'}},
                {colspan: {l: '6', m: '6', default: '12'}},
                {colspan: {l: '6', m: '6', default: '12'}},
                {colspan: {l: '6', m: '6', default: '12'}},
                {colspan: {l: '6', m: '6', default: '12'}},
                {colspan: {l: '6', m: '6', default: '12'}},
                {colspan: {l: '6', m: '6', default: '12'}},
                {colspan: {l: '6', m: '6', default: '12'}}
              ]}
            >
              <MFOverview
                dataWaves={{data: dataWaves, isLoading: isLoadingWaves, error: errorWaves}}
                dataServers={{data: dataServers, isLoading: isLoadingServers, error: errorServers}}
                dataApps={{data: dataApps, isLoading: isLoadingApps, error: errorApps}}
                dataDatabases={{data: dataDatabases, isLoading: isLoadingDatabases, error: errorDatabases}}
                completion={getMigratedItems()}
              />
              <WaveStatus
                data={{data: dataWaves, isLoading: isLoadingWaves, error: errorWaves}}
              />
              <WaveServersByMonth
                Waves={{data: dataWaves, isLoading: isLoadingWaves, error: errorWaves}}
                Servers={{data: dataServers, isLoading: isLoadingServers, error: errorServers}}
                Apps={{data: dataApps, isLoading: isLoadingApps, error: errorApps}}
              />
              <ChartOSTypes
                data={{data: dataServers, isLoading: isLoadingServers, error: errorServers}}
              />
              <ChartServerEnvTypes
                data={{data: dataServers, isLoading: isLoadingServers, error: errorServers}}
              />
              <ServerRepStatus
                data={{data: dataServers, isLoading: isLoadingServers, error: errorServers}}
              />

            </Grid>
          </SpaceBetween>
          }
    </div>
  );
};

export default UserDashboard;
