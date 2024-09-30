/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { BarChart, Box, Container, Header } from "@cloudscape-design/components";

type WaveServersByMonthParams = {
  Waves: { data: any[]; isLoading: any; error: any };
  Apps: { data: any; isLoading: any; error: any };
  Servers: { data: any; isLoading: any; error: any };
};

// Attribute Display message content
const WaveServersByMonth = (props: WaveServersByMonthParams) => {
  function getWaveApplications(dataApps: any[], wave_id: any) {
    return (
      dataApps?.filter(function (entry) {
        return entry.wave_id === wave_id;
      }) || []
    );
  }

  function getWaveServers(wave_id: any, dataApps: any[], dataServers: any[]) {
    const apps = getWaveApplications(dataApps, wave_id);
    let servers: any[] = [];

    for (let item in apps) {
      let lservers = dataServers.filter(function (entry: { app_id: any }) {
        return entry.app_id === apps[item].app_id;
      });

      servers = servers.concat(lservers);
    }

    return servers;
  }

  function dateRange(startDate: Date, endDate: Date) {
    let startYear = startDate.getFullYear();
    let endYear = endDate.getFullYear();
    let dates = [];

    for (let i = startYear; i <= endYear; i++) {
      let endMonth = i != endYear ? 11 : endDate.getMonth();
      let startMon = i === startYear ? startDate.getMonth() : 0;
      for (let j = startMon; j <= endMonth; j = j > 12 ? j % 12 || 11 : j + 1) {
        let month = j + 1;
        dates.push({ x: [i, month].join("-"), y: 0 });
      }
    }
    return dates;
  }

  let statusType: any = "loading";
  let chart_data: { x: string; y: number }[] = [];

  //Get Wave end time into data array for chart.
  let waveStatus = props.Waves.data.map(function (value) {
    let servers = getWaveServers(value["wave_id"], props.Apps.data, props.Servers.data);

    if (value["wave_end_time"]) {
      let startDate = new Date(value["wave_end_time"]);

      return { x: startDate, y: servers.length };
    } else {
      return { x: undefined, y: servers.length };
    }
  });

  //Remove waves that do not have an end date set.
  waveStatus = waveStatus.filter(function (value) {
    return value.x !== undefined;
  });

  waveStatus = waveStatus.sort(function (a, b) {
    if (a.x && b.x) {
      return a.x > b.x ? 1 : -1;
    } else if (!a.x && b.x) {
      return -1;
    } else {
      return 1;
    }
  });

  //Pre-populate chart_data with all months between the earliest and latest dates for the waves.
  if (waveStatus !== undefined && waveStatus.length > 0) {
    chart_data = dateRange(waveStatus[0].x!, waveStatus[waveStatus.length - 1].x!);

    //Map each wave into the chart_data array and combine waves server totals where occurring the same month.
    waveStatus.forEach(function (value) {
      if (value.x) {
        let startDate = new Date(value.x);
        let month = startDate.getMonth() + 1;
        let year = startDate.getFullYear();

        let item = chart_data.filter(function (entry) {
          return entry.x === year + "-" + month;
        });

        if (item.length === 1) {
          item[0].y += value.y;
        } else {
          chart_data.push({ x: year + "-" + month, y: value.y });
        }
      }
    });
  }

  if (
    !props.Waves.isLoading &&
    !props.Waves.error &&
    !props.Servers.isLoading &&
    !props.Servers.error &&
    !props.Apps.isLoading &&
    !props.Apps.error
  ) {
    statusType = "finished";
  } else if (
    (!props.Waves.isLoading && props.Waves.error) ||
    (!props.Servers.isLoading && props.Servers.error) ||
    (!props.Apps.isLoading && props.Apps.error)
  ) {
    statusType = "error";
  }

  const series: any =
    chart_data.length == 0
      ? []
      : [
          {
            type: "bar",
            data: chart_data,
          },
        ];
  return (
    <Container
      header={
        <Header variant="h2" description="Server migrations by month">
          Server migrations by month
        </Header>
      }
    >
      <BarChart
        series={series}
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
  );
};

export default WaveServersByMonth;
