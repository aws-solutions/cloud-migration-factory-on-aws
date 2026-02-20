/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { BarChart, BarChartProps, Box, Container, Header } from "@cloudscape-design/components";
import { Application, DataLoadingState, Server, Wave } from "../../models";

type WaveServersByMonthParams = {
  waves: DataLoadingState<Wave>;
  apps: DataLoadingState<Application>;
  servers: DataLoadingState<Server>;
};

// Attribute Display message content
const WaveServersByMonth = (props: WaveServersByMonthParams) => {
  function dateRange(startDate: Date, endDate: Date) {
    const startYear = startDate.getFullYear();
    const endYear = endDate.getFullYear();
    const dates = [];

    for (let i = startYear; i <= endYear; i++) {
      const endMonth = i != endYear ? 11 : endDate.getMonth();
      const startMon = i === startYear ? startDate.getMonth() : 0;
      for (let j = startMon; j <= endMonth; j = j > 12 ? j % 12 || 11 : j + 1) {
        const month = j + 1;
        dates.push({ x: [i, month].join("-"), y: 0 });
      }
    }
    return dates;
  }

  let statusType: BarChartProps<string>["statusType"] = "loading";
  let chart_data: { x: string; y: number }[] = [];

  //Get Wave end time into data array for chart.
  const waveStatus = props.waves.data
    .map((value) => {
      const servers = props.servers.data.filter((server) => server.wave_id === value.wave_id);

      return { x: value.wave_end_time ? new Date(value.wave_end_time) : undefined, y: servers.length };
    })
    .filter((d): d is { x: Date; y: number } => d.x !== undefined)
    .sort((a, b) => (a.x > b.x ? 1 : -1));

  //Pre-populate chart_data with all months between the earliest and latest dates for the waves.
  if (waveStatus !== undefined && waveStatus.length > 0) {
    chart_data = dateRange(waveStatus[0].x, waveStatus[waveStatus.length - 1].x);

    //Map each wave into the chart_data array and combine waves server totals where occurring the same month.
    waveStatus.forEach((value) => {
      if (value.x) {
        const startDate = new Date(value.x);
        const month = startDate.getMonth() + 1;
        const year = startDate.getFullYear();

        const item = chart_data.filter((entry) => entry.x === year + "-" + month);

        if (item.length === 1) {
          item[0].y += value.y;
        } else {
          chart_data.push({ x: year + "-" + month, y: value.y });
        }
      }
    });
  }

  if (
    !props.waves.isLoading &&
    !props.waves.error &&
    !props.servers.isLoading &&
    !props.servers.error &&
    !props.apps.isLoading &&
    !props.apps.error
  ) {
    statusType = "finished";
  } else if (
    (!props.waves.isLoading && props.waves.error) ||
    (!props.servers.isLoading && props.servers.error) ||
    (!props.apps.isLoading && props.apps.error)
  ) {
    statusType = "error";
  }

  const series: BarChartProps<string>["series"] =
    chart_data.length == 0
      ? []
      : [
          {
            type: "bar",
            title: "",
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
