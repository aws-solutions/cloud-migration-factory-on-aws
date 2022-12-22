/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from 'react';
import { exportAll } from '../resources/main.js';

import {

  Button,
} from '@awsui/components-react';

import { useMFApps } from "../actions/ApplicationsHook";
import { useGetServers } from "../actions/ServersHook.js";
import { useMFWaves } from "../actions/WavesHook.js";
import { useGetDatabases} from "../actions/DatabasesHook";
import { useProgressModal } from "../actions/ProgressModalHook.js";

const UserExport = (props) => {

  //Data items for viewer and table.
  const [{ isLoading: isLoadingApps, data: dataApps, error: errorApps }, { update: updateApps }] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers, error: errorServers }, { update: updateServers }] = useGetServers();
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }, { update: updateWaves }] = useMFWaves();
  const [{ isLoading: isLoadingDBs, data: dataDBs, error: errorDbs }, { update: updateDBs }] = useGetDatabases();
  const { show: showCommitProgress, hide: hideCommitProgress, setProgress: setImportProgress, RenderModal: CommitProgressModel } = useProgressModal()

  function exportClick() {

    let data = {};
    data.servers = dataServers;
    data.applications = dataApps;
    data.waves = dataWaves;
    data.databases = dataDBs;

    exportAll(data, "all-data");

  }

  //Check if any data is still loading and disable download button.
  let dataLoading = isLoadingApps || isLoadingServers || isLoadingWaves

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
