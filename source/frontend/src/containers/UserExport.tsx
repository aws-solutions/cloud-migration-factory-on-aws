// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect} from 'react';
import { exportAll } from '../resources/main';

import {

  Button,
} from '@awsui/components-react';

import { useMFApps } from "../actions/ApplicationsHook";
import { useGetServers } from "../actions/ServersHook";
import { useMFWaves } from "../actions/WavesHook";
import { useGetDatabases} from "../actions/DatabasesHook";

const UserExport = (props) => {

  //Data items for viewer and table.
  const [{ isLoading: isLoadingApps, data: dataApps}, ] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers}, ] = useGetServers();
  const [{ isLoading: isLoadingWaves, data: dataWaves}, ] = useMFWaves();
  const [{ isLoading: isLoadingDBs, data: dataDBs}, ] = useGetDatabases();


  function exportClick() {

    let data = {};
    data.servers = dataServers;
    data.applications = dataApps;
    data.waves = dataWaves;
    data.databases = dataDBs;

    exportAll(data, "all-data");

  }

  //Check if any data is still loading and disable download button.
  let dataLoading = isLoadingApps || isLoadingServers || isLoadingWaves || isLoadingDBs;

  //Update help tools panel.
  useEffect(() => {
    props.setHelpPanelContent({
      header: 'Export',
      content_text: 'From here you can export all the data from the Migration Factory into a single multi tabbed Excel spreadsheet.'
    })
  }, []);

  return (
    <div>
      {<Button variant="primary" iconName="download" disabled={dataLoading} onClick={() => {
          exportClick();
        }}>Download All Data</Button>}
      </div>
  );
};

// Component TableView is a skeleton of a Table using AWS-UI React components.
export default UserExport;
