// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { BarChart,
Container,
Header,
Box} from '@awsui/components-react';


// Attribute Display message content
const WaveServersByMonth = (props) => {


  function getWaveApplications(dataApps, wave_id) {

      let apps = dataApps.filter(function (entry) {
        return entry.wave_id === wave_id;
      });

      if ( apps.length > 0){
        return apps;
      } else {
        return [];
      }
  }

  function getWaveServers(wave_id, dataApps, dataServers) {

      let apps = getWaveApplications(dataApps, wave_id);
      let servers = [];

      for(let item in apps) {
        let lservers = dataServers.filter(function (entry) {
          return entry.app_id === apps[item].app_id;
        });

        servers = servers.concat(lservers);
      }

      if ( servers.length > 0){
        return servers;
      } else {
        return [];
      }
  }

  function dateRange(startDate, endDate) {
      let startYear  = startDate.getFullYear();
      let endYear    = endDate.getFullYear();
      let dates      = [];

      for(let i = startYear; i <= endYear; i++) {
        let endMonth = i != endYear ? 11 : parseInt(endDate.getMonth());
        let startMon = i === startYear ? parseInt(startDate.getMonth()) : 0;
        for(let j = startMon; j <= endMonth; j = j > 12 ? j % 12 || 11 : j+1) {
          let month = j+1;
          dates.push({x: [i, month].join('-'), y: 0});
        }
      }
      return dates;
    }

  let statusType = 'loading';
  let chart_data = []

  //Get Wave end time into data array for chart.
  let waveStatus = props.Waves.data.map(function(value, index) {
    let servers = getWaveServers(value['wave_id'], props.Apps.data, props.Servers.data)

    if (value['wave_end_time']){
      let startDate = new Date(value['wave_end_time']);

      return {x: startDate, y: servers.length};
    } else {
      return {x: undefined, y: servers.length};
    }
  });


  //Remove waves that do not have an end date set.
  waveStatus = waveStatus.filter(function(value, index) {
      return value.x !== undefined;
  });

  waveStatus = waveStatus.sort(function (a, b) {
    if (a.x && b.x){
      return a.x > b.x ? 1 : -1;
    }
    else if (!a.x && b.x){
      return -1;
    }
    else if (a.x && !b.x) {
      return 1;
    }
  });

  //Pre-populate chart_data with all months between the earliest and latest dates for the waves.
  if (waveStatus !== undefined && waveStatus.length > 0){
    chart_data = dateRange(waveStatus[0].x, waveStatus[waveStatus.length-1].x);

    //Map each wave into the chart_data array and combine waves server totals where occurring the same month.
    waveStatus.forEach(function(value, index) {
      if (value.x){
        let startDate = new Date(value.x);
        let month = startDate.getMonth()+1;
        let year = startDate.getFullYear();

        let item = chart_data.filter(function (entry) {
          return entry.x === year + '-' + month;
        });

        if (item.length === 1) {
          item[0].y += value.y;
        } else {
          chart_data.push({x: year + '-' + month , y: value.y});
        }
      }
    });
  }

  if (!props.Waves.isLoading && !props.Waves.error && !props.Servers.isLoading && !props.Servers.error && !props.Apps.isLoading && !props.Apps.error) {
    statusType = 'finished';
  } else if ((!props.Waves.isLoading && props.Waves.error) || (!props.Servers.isLoading && props.Servers.error)|| (!props.Apps.isLoading && props.Apps.error)) {
    statusType = 'error';
  }

  return <Container
          header={
            <Header
              variant="h2"
              description="Server migrations by month"
            >
              Server migrations by month
            </Header>
          }
        >
    <BarChart
      series={chart_data.length == 0 ? [] : [
        {
          type: "bar",
          data: chart_data,
        }
      ]}
      i18nStrings={{
        filterLabel: "Filter displayed data",
        filterPlaceholder: "Filter data",
        filterSelectedAriaLabel: "selected",
        legendAriaLabel: "Legend",
        chartAriaRoleDescription: "line chart",
      }}
      ariaLabel="Single data series line chart"
      errorText="Error loading data."
      height={300}
      hideFilter
      hideLegend
      loadingText="Loading chart"
      recoveryText="Retry"
      statusType={statusType}
      xScaleType="categorical"
      xTitle="Month"
      yTitle="Number of servers"
      empty={
        <Box textAlign="center" color="inherit">
          <b>No data available</b>
          <Box variant="p" color="inherit">
            There is no data available
          </Box>
        </Box>
      }
      noMatch={
        <Box textAlign="center" color="inherit">
          <b>No matching data</b>
          <Box variant="p" color="inherit">
            There is no matching data to display
          </Box>
        </Box>
      }
    />
        </Container>
};

export default WaveServersByMonth;
