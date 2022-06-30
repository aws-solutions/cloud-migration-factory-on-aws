import React from 'react';
import {
  Container,
  Header,
  Box,
  Link,
  Spinner,
  ColumnLayout
} from '@awsui/components-react';

// import { withRouter } from "react-router";

// Attribute Display message content
const MFOverview = (props) => {

  let history = props.history

  function handleClick(LinkProps) {

    history.push(LinkProps.href);
  }

  return <Container
      className="custom-dashboard-container"
      header={
        <Header variant="h2" description="Overview of the status within the Migration Factory">
          Migration Factory overview
        </Header>
      }
    >
      <ColumnLayout columns="4" variant="text-grid">
        <div>
          <Box margin={{ bottom: 'xxxs' }} color="text-label">
            Waves
          </Box>
          {props.dataWaves.isLoading
            ?
            <Spinner size="big"/>
            :
            <Link fontSize="display-l" href='/waves' onFollow={handleClick}>
              {props.dataWaves.isLoading ? <Spinner/> :
                <span className="custom-link-font-weight-light">{props.dataWaves.data.length}</span>}
            </Link>
          }
        </div>
        <div>
          <Box margin={{ bottom: 'xxxs' }} color="text-label">
            Applications
          </Box>
          {props.dataApps.isLoading
            ?
            <Spinner size="big"/>
            :
            <Link fontSize="display-l" href="/apps">
              <span className="custom-link-font-weight-light">{props.dataApps.data.length}</span>
            </Link>
          }
        </div>
        <div>
          <Box margin={{ bottom: 'xxxs' }} color="text-label">
            Servers
          </Box>
          {props.dataServers.isLoading
            ?
            <Spinner size="big"/>
            :
            <Link fontSize="display-l" href="/servers">
              <span className="custom-link-font-weight-light">{props.dataServers.data.length}</span>
            </Link>
          }
        </div>
        <div>
          <Box margin={{ bottom: 'xxxs' }} color="text-label">
            Databases
          </Box>
          {props.dataDatabases.isLoading
            ?
            <Spinner size="big"/>
            :
            <Link fontSize="display-l" href="/databases">
              <span className="custom-link-font-weight-light">{props.dataDatabases.data.length}</span>
            </Link>
          }
        </div>
        <div>
          <Box margin={{ bottom: 'xxxs' }} color="text-label">
            Completed Waves
          </Box>
          {props.dataWaves.isLoading
            ?
            <Spinner size="big"/>
            :
            <Link fontSize="display-l" href="#">
              <span
                className="custom-link-font-weight-light">{props.completion.waves ? props.completion.waves.length : 0}</span>
            </Link>
          }
        </div>
        <div>
          <Box margin={{ bottom: 'xxxs' }} color="text-label">
            Migrated Applications
          </Box>
          {props.dataApps.isLoading
            ?
            <Spinner size="big"/>
            :
            <Link fontSize="display-l" href="#">
              <span
                className="custom-link-font-weight-light">{props.completion.applications ? props.completion.applications.length : 0}</span>
            </Link>
          }
        </div>
        <div>
          <Box margin={{ bottom: 'xxxs' }} color="text-label">
            Migrated Servers
          </Box>
          {props.dataServers.isLoading
            ?
            <Spinner size="big"/>
            :
            <Link fontSize="display-l" href="#">
              <span
                className="custom-link-font-weight-light">{props.completion.servers ? props.completion.servers.length : 0}</span>
            </Link>
          }
        </div>
        <div>
          <Box margin={{ bottom: 'xxxs' }} color="text-label">
            Migrated Databases
          </Box>
          {props.dataDatabases.isLoading
            ?
            <Spinner size="big"/>
            :
            <Link fontSize="display-l" href="#">
              <span
                className="custom-link-font-weight-light">{props.completion.databases ? props.completion.databases.length : 0}</span>
            </Link>
          }
        </div>
      </ColumnLayout>
    </Container>
};

export default MFOverview;
