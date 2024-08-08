/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { Box, ColumnLayout, Container, Header, Link, Spinner } from "@awsui/components-react";

export type CompletedItemIds = {
  waveIds: string[];
  applicationIds: string[];
  serverIds: string[];
  databaseIds: string[];
};
type MFOverviewParams = {
  dataWaves: { isLoading: any; data: any[] };
  dataApps: { isLoading: any; data: any[] };
  dataServers: { isLoading: any; data: any[] };
  dataDatabases: { isLoading: any; data: any[] };
  completed: CompletedItemIds;
};

// Attribute Display message content
const MFOverview = (props: MFOverviewParams) => {
  return (
    <Container
      className="custom-dashboard-container"
      header={
        <Header variant="h2" description="Overview of the status within the Migration Factory">
          Migration Factory overview
        </Header>
      }
    >
      <ColumnLayout columns={4} variant="text-grid">
        <div>
          <Box margin={{ bottom: "xxxs" }} color="text-label">
            Waves
          </Box>
          {props.dataWaves.isLoading ? (
            <Spinner size="big" />
          ) : (
            <Link fontSize="display-l" href="/waves">
              {props.dataWaves.isLoading ? (
                <Spinner />
              ) : (
                <span className="custom-link-font-weight-light">{props.dataWaves.data.length}</span>
              )}
            </Link>
          )}
        </div>
        <div>
          <Box margin={{ bottom: "xxxs" }} color="text-label">
            Applications
          </Box>
          {props.dataApps.isLoading ? (
            <Spinner size="big" />
          ) : (
            <Link fontSize="display-l" href="/applications">
              <span className="custom-link-font-weight-light">{props.dataApps.data.length}</span>
            </Link>
          )}
        </div>
        <div>
          <Box margin={{ bottom: "xxxs" }} color="text-label">
            Servers
          </Box>
          {props.dataServers.isLoading ? (
            <Spinner size="big" />
          ) : (
            <Link fontSize="display-l" href="/servers">
              <span className="custom-link-font-weight-light">{props.dataServers.data.length}</span>
            </Link>
          )}
        </div>
        <div>
          <Box margin={{ bottom: "xxxs" }} color="text-label">
            Databases
          </Box>
          {props.dataDatabases.isLoading ? (
            <Spinner size="big" />
          ) : (
            <Link fontSize="display-l" href="/databases">
              <span className="custom-link-font-weight-light">{props.dataDatabases.data.length}</span>
            </Link>
          )}
        </div>
        <div>
          <Box margin={{ bottom: "xxxs" }} color="text-label">
            Completed Waves
          </Box>
          {props.dataWaves.isLoading ? (
            <Spinner size="big" />
          ) : (
            <Link fontSize="display-l" href="#" data-testid={"completed-waves"}>
              <span className="custom-link-font-weight-light">{props.completed.waveIds.length}</span>
            </Link>
          )}
        </div>
        <div>
          <Box margin={{ bottom: "xxxs" }} color="text-label">
            Migrated Applications
          </Box>
          {props.dataApps.isLoading ? (
            <Spinner size="big" />
          ) : (
            <Link fontSize="display-l" href="#">
              <span className="custom-link-font-weight-light">{props.completed.applicationIds.length}</span>
            </Link>
          )}
        </div>
        <div>
          <Box margin={{ bottom: "xxxs" }} color="text-label">
            Migrated Servers
          </Box>
          {props.dataServers.isLoading ? (
            <Spinner size="big" />
          ) : (
            <Link fontSize="display-l" href="#">
              <span className="custom-link-font-weight-light">{props.completed.serverIds.length}</span>
            </Link>
          )}
        </div>
        <div>
          <Box margin={{ bottom: "xxxs" }} color="text-label">
            Migrated Databases
          </Box>
          {props.dataDatabases.isLoading ? (
            <Spinner size="big" />
          ) : (
            <Link fontSize="display-l" href="#">
              <span className="custom-link-font-weight-light">{props.completed.databaseIds.length}</span>
            </Link>
          )}
        </div>
      </ColumnLayout>
    </Container>
  );
};

export default MFOverview;
