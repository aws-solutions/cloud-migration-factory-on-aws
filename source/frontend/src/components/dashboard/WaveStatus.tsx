// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import {Box, Container, Header, PieChart} from '@awsui/components-react';


// Attribute Display message content
const WaveStatus = ({data}) => {
  let statusType = 'loading';

  let waveStatus = data.data.map(function (value, index) {
    return value['wave_status']
  });

  let wave_count = [];
  waveStatus.forEach(function (value, index) {
    let lvalue = value;

    if (lvalue === undefined) {
      lvalue = 'No Status'
    }

    let item = wave_count.filter(function (entry) {
      return entry.title === lvalue;
    });

    if (item.length === 1) {
      item[0].value += 1;
    } else {
      wave_count.push({title: lvalue, value: 1});
    }
  });


  if (!data.isLoading && !data.error) {
    statusType = 'finished';
  } else if (!data.isLoading && data.error) {
    statusType = 'error';
  }

  return <Container
    header={
      <Header
        variant="h2"
        description="Status of all waves"
      >
        Wave status
      </Header>
    }
  >
    <PieChart
      data={wave_count}
      statusType={statusType}
      loadingText='Loading'
      size="medium"
      segmentDescription={(datum, sum) =>
        `${datum.value} waves, ${(
          (datum.value / sum) *
          100
        ).toFixed(0)}%`
      }
      i18nStrings={{
        detailsValue: "Value",
        detailsPercentage: "Percentage",
        filterLabel: "Filter displayed data",
        filterPlaceholder: "Filter data",
        filterSelectedAriaLabel: "selected",
        detailPopoverDismissAriaLabel: "Dismiss",
        legendAriaLabel: "Legend",
        chartAriaRoleDescription: "pie chart",
        segmentAriaRoleDescription: "segment"
      }}
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

export default WaveStatus;
